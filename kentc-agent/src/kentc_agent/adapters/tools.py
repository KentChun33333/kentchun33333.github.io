"""The built-in tools: read, write, edit, bash (pi-agent's core set). Listing, searching and exact arithmetic go
through bash (ls, find, rg/grep, python3 -c). There is
no web tool: web research is a workflow `web:` step run by the web agent (web_research.py), saved as a file.

Paths are relative to the workspace. Reads may go anywhere unless `confine_reads` is set (an agent reading
untrusted documents); write and edit always stay inside the workspace."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..context.bigcontext import limits, note_source, real_tokens, route_text
from ..config import STATE_DIR, Settings
from ..errors import ToolError
from ..ports import Events, LLM
from .filetypes import DOC_SUFFIXES, reject_unsupported
from .session import CHARS_PER_TOKEN

if TYPE_CHECKING:
    from .trace import OpRef


@dataclass
class ToolContext:
    workspace: Path
    settings: Settings
    llm: LLM
    events: Events
    operation: OpRef | None = None   # the tool call running now (trace.py): a sub-agent's parent
    density: float = 1.0             # server tokens per chars/4 token, from the agent whose tools run (agent.py)
    confine_reads: bool = False      # read refuses paths outside the workspace (studio agents on uploaded documents)

    @property
    def state_dir(self) -> Path:
        return self.workspace / STATE_DIR


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    run: Callable[[ToolContext, dict[str, Any]], str]

    def schema(self) -> dict[str, Any]:
        return {"type": "function",
                "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}


def params(required: list[str], **props: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": required}


# ---------------------------------------------------------------------- paths and truncation
def resolve(ctx: ToolContext, path: str) -> Path:
    p = Path(os.path.expanduser(path or "."))
    return (p if p.is_absolute() else ctx.workspace / p).resolve()


def inside(ctx: ToolContext, path: str, what: str = "writes") -> Path:
    p = resolve(ctx, path)
    if not p.is_relative_to(ctx.workspace.resolve()):
        raise ToolError(f"{path}: outside the workspace {ctx.workspace}; {what} are limited to the workspace")
    return p


def rel(ctx: ToolContext, p: Path) -> str:
    ws = ctx.workspace.resolve()
    return str(p.relative_to(ws)) if p.is_relative_to(ws) else \
        str(p.relative_to(ctx.workspace)) if p.is_relative_to(ctx.workspace) else str(p)


def truncate_head(text: str, max_lines: int, max_bytes: int) -> tuple[str, int, bool]:
    """Keep the start. -> (text, lines kept, truncated)."""
    lines = text.split("\n")
    out, size = [], 0
    for line in lines[:max_lines]:
        size += len(line.encode()) + 1
        if size > max_bytes:
            break
        out.append(line)
    if not out and lines:                                   # a single giant line
        return lines[0].encode()[:max_bytes].decode("utf-8", "ignore"), 1, True
    return "\n".join(out), len(out), len(out) < len(lines)


def truncate_tail(text: str, max_lines: int, max_bytes: int) -> tuple[str, bool]:
    """Keep the end (command output: errors and results come last)."""
    lines = text.split("\n")
    out, size = [], 0
    for line in reversed(lines[-max_lines:]):
        size += len(line.encode()) + 1
        if size > max_bytes:
            break
        out.append(line)
    if not out and lines:
        return lines[-1].encode()[-max_bytes:].decode("utf-8", "ignore"), True
    return "\n".join(reversed(out)), len(out) < len(lines)


# ---------------------------------------------------------------------- read / write / edit
PAGE_NOTE_CHARS = 160      # room kept for the "[Showing lines ...]" note at the end of a page


def page(text: str, offset: int | None, limit: int | None, ctx: ToolContext, what: str) -> str:
    """Lines offset.. of `text`, cut to fit the big-result limit (the note included): a page never needs the
    big-context route."""
    lines = text.split("\n")
    total = len(lines)
    start = max(1, int(offset or 1))
    if start > total:
        raise ToolError(f"offset {start} is past the end of {what} ({total} lines)")
    s = ctx.settings
    room = limits(ctx).result * CHARS_PER_TOKEN - PAGE_NOTE_CHARS
    body, kept, cut = truncate_head("\n".join(lines[start - 1:start - 1 + int(limit or s.tool_output_max_lines)]),
                                    s.tool_output_max_lines, min(s.tool_output_max_bytes, room))
    end = start + kept - 1
    if end < total:
        body += f"\n\n[Showing lines {start}-{end} of {total} of {what}. Use offset={end + 1} to continue.]"
    elif cut:
        body += "\n\n[Line truncated to the output limit.]"
    return body


def _read(ctx: ToolContext, a: dict[str, Any]) -> str:
    p = inside(ctx, a["path"], "reads") if ctx.confine_reads else resolve(ctx, a["path"])
    if not p.exists():
        raise ToolError(f"{a['path']}: no such file")
    if p.is_dir():
        raise ToolError(f"{a['path']}: is a directory; list it with bash (ls)")
    if p.suffix.lower() in DOC_SUFFIXES:
        from .documents import read_document
        offset, limit = a.get("offset"), a.get("limit")
        return read_document(ctx, p, a.get("question") or None, a.get("pages") or None,
                             int(offset) if offset else None, int(limit) if limit else None)
    reject_unsupported(p)
    raw = p.read_bytes()
    if b"\0" in raw[:8192]:
        raise ToolError(f"{a['path']}: binary file ({len(raw)} bytes)")
    text = raw.decode("utf-8", "replace")
    if a.get("offset") or a.get("limit"):
        return page(text, a.get("offset"), a.get("limit"), ctx, "the file")
    if real_tokens(ctx, text) > limits(ctx).result:        # condition 1, a single big file: digest + pointer
        return route_text(ctx, text, "read", a, source=rel(ctx, p))
    note_source(ctx, rel(ctx, p))
    return text


def _write(ctx: ToolContext, a: dict[str, Any]) -> str:
    p = inside(ctx, a["path"])
    p.parent.mkdir(parents=True, exist_ok=True)
    data = a.get("content", "")
    p.write_text(data, encoding="utf-8")
    return f"Wrote {len(data.encode())} bytes to {rel(ctx, p)}"


def _edit(ctx: ToolContext, a: dict[str, Any]) -> str:
    p = inside(ctx, a["path"])
    if not p.is_file():
        raise ToolError(f"{a['path']}: no such file")
    old, new = a.get("old_text", ""), a.get("new_text", "")
    if not old:
        raise ToolError("old_text is empty; use write to create a file")
    text = p.read_text(encoding="utf-8")
    n = text.count(old)
    if n == 0:
        hint = " (it matches if whitespace is ignored: copy the exact indentation)" \
            if re.sub(r"\s+", "", old) in re.sub(r"\s+", "", text) else ""
        raise ToolError(f"old_text not found in {rel(ctx, p)}{hint}. Read the file and copy the text exactly.")
    if n > 1 and not a.get("replace_all"):
        raise ToolError(f"old_text occurs {n} times in {rel(ctx, p)}; add surrounding lines to make it unique "
                        "or set replace_all")
    text = text.replace(old, new) if a.get("replace_all") else text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    line = text[: text.find(new)].count("\n") + 1 if new else None
    return f"Edited {rel(ctx, p)}: {n if a.get('replace_all') else 1} replacement(s)" + \
        (f", starting at line {line}" if line else "")


# ---------------------------------------------------------------------- bash
@dataclass(frozen=True)
class ShellResult:
    output: str            # tail-truncated, with a pointer to the full log when cut
    code: int | None       # None: timed out
    timeout: float
    log: str = ""          # the full output's file (workspace-relative) when the output was cut

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def status(self) -> str:
        return f"timed out after {self.timeout:.0f}s" if self.code is None else f"exit code {self.code}"

    def format(self) -> str:
        return f"{self.output}\n\n[{self.status}]" if self.output else f"[{self.status}, no output]"


def run_shell(ctx: ToolContext, command: str, timeout: float | None = None) -> ShellResult:
    s = ctx.settings
    timeout = float(timeout or s.bash_timeout)
    proc = subprocess.Popen(["/bin/bash", "-c", command], cwd=ctx.workspace, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    timed_out = False
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGKILL)
        out, _ = proc.communicate()
    except BaseException:                       # Ctrl-C: take the whole process group down with us
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        raise
    text = out.decode("utf-8", "replace").rstrip("\n")
    shown, cut = truncate_tail(text, s.tool_output_max_lines, s.tool_output_max_bytes)
    log = ""
    if cut:
        path = ctx.state_dir / "tmp" / f"bash-{time.strftime('%Y%m%d-%H%M%S')}-{proc.pid}.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        log = rel(ctx, path)
        shown = f"[Output truncated: showing the end. Full output: {log}]\n" + shown
    return ShellResult(shown, None if timed_out else proc.returncode, timeout, log)


def _bash(ctx: ToolContext, a: dict[str, Any]) -> str:
    r = run_shell(ctx, a["command"], a.get("timeout"))
    if r.log:
        note_source(ctx, r.log)                 # a big-result digest then covers the whole output
    return r.format()


# ---------------------------------------------------------------------- registry
CORE_TOOLS: dict[str, Tool] = {t.name: t for t in [
    Tool("read", "Read a file. Small text files and documents (Word, Excel, CSV, PowerPoint, e-mail .eml/.msg, "
         "HTML; converted to markdown) come back whole. PDFs, images and large files are stored instead, and you get "
         "a digest (summary, key insights, key values, metadata) with the path of the full text: read that path "
         "with offset/limit for exact lines (pages always fit), search it with bash, or read a document with "
         "question for "
         "specific facts with their locations, or pages for PDF ranges. E-mail attachments are saved and listed; "
         "read them the same way. Video is not supported.",
         params(["path"], path={"type": "string"},
                offset={"type": "integer", "description": "1-based start line"},
                limit={"type": "integer", "description": "max lines"},
                question={"type": "string", "description": "for PDFs/images/large documents: what to extract"},
                pages={"type": "string", "description": "PDF page ranges, e.g. '1-5,9'"}), _read),
    Tool("write", "Create or overwrite a file with the full content. Parent directories are created.",
         params(["path", "content"], path={"type": "string"}, content={"type": "string"}), _write),
    Tool("edit", "Replace exact text in a file. old_text must match exactly (including whitespace) and be unique "
         "unless replace_all is true. Prefer small, targeted edits.",
         params(["path", "old_text", "new_text"], path={"type": "string"}, old_text={"type": "string"},
                new_text={"type": "string"}, replace_all={"type": "boolean"}), _edit),
    Tool("bash", "Run a shell command in the workspace (bash -c). Output is truncated to its end. Use it to list "
         "(ls), find files (find, rg --files), search contents (rg -n or grep -rn), compute exactly "
         "(python3 -c 'print(182000 + 146000)'), and for builds, tests, git and scripts.",
         params(["command"], command={"type": "string"},
                timeout={"type": "number", "description": "seconds (default 120)"}), _bash),
]}
