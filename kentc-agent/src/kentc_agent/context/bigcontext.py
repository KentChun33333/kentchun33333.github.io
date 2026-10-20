"""Big-context route: large tool results go to the operation folder, and the context gets a digest instead.

Three rules, nothing else (settings, scaled down for a small window: see `limits`):
1. a single big file or image: `read` of a file over `big_result_tokens` (3000), or of any PDF/image, stores it
   when it is read (the tool decides, it knows the file);
2. any other single tool result over `big_result_tokens` (a long bash output, many grep matches), even when the
   turn as a whole would fit;
3. a turn's tool results together over `big_turn_tokens` (12000): after the tool calls, the largest results are
   stored first until the turn fits.
Sizes are chars/4 × the density learned from the server's own token counts (`ToolContext.density`), so the
checks follow the real tokenizer of the model behind the server.

A routed result keeps its full text in .kentc-agent/operations/<session id>/<operation id>/<tool call id>/:
    full.md       the full text (not written when it is already a workspace file, e.g. a text file that was read)
    digest.json   {summary, key_insights, key_values: [{field, value, location}], metadata, preview?}
and the context gets the rendered digest (at most `big_digest_tokens`), with where the full text is and how to
read more of it: `read` with offset/limit (pages that always fit), bash (rg / grep), or for a document `read` with a
question.

Who digests: documents (PDF, images, Office, e-mail, CSV, HTML) -> the parsing sub-agent (documents.py);
everything else (code, logs, command output, listings, matches) -> the rules below, without a model call.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..config import STATE_DIR
from ..adapters.session import CHARS_PER_TOKEN, new_session_id

if TYPE_CHECKING:
    from ..adapters.tools import ToolContext
    from ..adapters.trace import OpRef

ERROR_RE = re.compile(r"(?i)\b(error|exception|traceback|fatal|failed|failure|panic|denied|warning)\b")
OUTLINE_RE = re.compile(r"^\s*(#{1,6} |(async\s+)?def |class |function |export |func |fn |pub fn |interface |struct "
                        r"|impl |type |module |package |CREATE |SELECT |@app\.|@router\.)")
GREP_RE = re.compile(r"^(.+?):(\d+):")                                  # rg -n / grep -rn
PATH_RE = re.compile(r"^(\./)?[\w.@+=~-]+(/[\w.@+=~-]*)*/?$")           # one path per line: ls / find
PREVIEW_HEAD, PREVIEW_TAIL = 15, 5


def tokens(text: str) -> int:
    """chars/4: the raw estimate."""
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def real_tokens(ctx: ToolContext, text: str) -> int:
    """The estimate × the density learned from the server's counts: what this text costs in the model's tokens."""
    return math.ceil(tokens(text) * ctx.density)


@dataclass
class CallResult:
    """One executed tool call of a turn, before it enters the context."""
    call_id: str
    name: str
    args: Any
    text: str
    error: bool
    ms: int
    ref: OpRef | None
    safety: list[str] = field(default_factory=list)   # safety.py findings on what entered the context

    @property
    def routed(self) -> dict[str, Any] | None:
        return self.ref.routed if self.ref else None


@dataclass(frozen=True)
class Limits:
    result: int    # one result above this is routed; also the size of a page read with offset/limit
    turn: int      # one turn's results above this: the largest are routed first
    digest: int    # the most a digest takes in the context


def limits(ctx: ToolContext) -> Limits:
    """The big_* settings, scaled down for a small context window, where a 12k turn budget could not fit: at most
    1/20 (result), 1/5 (turn) and 1/40 (digest) of the window. At 65,536 tokens the settings apply unchanged."""
    s, w = ctx.settings, ctx.llm.info().context_window
    return Limits(min(s.big_result_tokens, w // 20), min(s.big_turn_tokens, w // 5), min(s.big_digest_tokens, w // 40))



# ---------------------------------------------------------------------- what a tool tells the router
def note_source(ctx: ToolContext, path: str) -> None:
    """This call's result is (or comes from) the workspace file `path`: a digest reads it, and no copy is made."""
    if ctx.operation is not None:
        ctx.operation.source = path


def note_document(ctx: ToolContext, path: str) -> None:
    """This call's result is the whole converted text of the document `path`: route it to the parsing sub-agent."""
    if ctx.operation is not None:
        ctx.operation.document = path


# ---------------------------------------------------------------------- storing and rendering
def folder(ctx: ToolContext) -> Path:
    op = ctx.operation
    base = ctx.workspace / STATE_DIR / "operations"
    if op is None:                              # called outside an agent turn (e.g. a host pre-reading a document)
        return base / "direct" / new_session_id()
    call = re.sub(r"[^A-Za-z0-9._-]+", "_", op.tool_call_id or "call")[:60]
    return base / op.session_id / str(op.operation_id) / call


def _rel(ctx: ToolContext, p: Path) -> str:
    return str(p.relative_to(ctx.workspace)) if p.is_relative_to(ctx.workspace) else str(p)


def store(ctx: ToolContext, d: Path, *, what: str, full: str | None, source: str | None, digest: dict[str, Any],
          by: str, size: int, also: str = "") -> str:
    """Write the folder `d`, mark the call as routed, and return what goes to the context.
    `what`: the call, for the header ('read(path=a.log)'); `full`: the full text to keep (None when `source`, a
    workspace file, already holds it); `size`: tokens of the full result; `also`: another way to read more."""
    d.mkdir(parents=True, exist_ok=True)
    if full is not None:
        (d / "full.md").write_text(full, encoding="utf-8")
    full_ref = _rel(ctx, d / "full.md") if full is not None else (source or "")
    digest = {**digest, "metadata": {**digest.get("metadata", {}), "full_text": full_ref, "digest_by": by}}
    (d / "digest.json").write_text(json.dumps(digest, ensure_ascii=False, indent=1), encoding="utf-8")
    if ctx.operation is not None:
        ctx.operation.routed = {"by": by, "tokens": size, "folder": _rel(ctx, d)}
    how = f"read {full_ref} with offset/limit (pages of up to {limits(ctx).result:,} tokens), or search it with " \
        "bash (rg -n / grep -n), for the parts you need." + (f" {also}" if also else "")
    return render(ctx, digest, what=what, size=size, full_ref=full_ref, folder=_rel(ctx, d), how=how)


def render(ctx: ToolContext, digest: dict[str, Any], *, what: str, size: int, full_ref: str, folder: str,
           how: str) -> str:
    """The digest as context text, within the digest limit: long lists are cut before anything else."""
    budget = limits(ctx).digest * CHARS_PER_TOKEN
    meta = {k: v for k, v in digest.get("metadata", {}).items() if k not in ("full_text", "digest_by") and v}
    insights = [str(x) for x in digest.get("key_insights") or []]
    values = [v for v in digest.get("key_values") or [] if isinstance(v, dict)]
    preview = [str(x) for x in digest.get("preview") or []]

    def build(n_ins: int, n_val: int, n_pre: int) -> str:
        header = (f"[Big result: {what} came to ~{size:,} tokens, so it was stored instead of shown. Full text: "
                  f"{full_ref}. Digest by {digest['metadata']['digest_by']}: {folder}/digest.json]")
        out = [header, f"Summary: {digest.get('summary') or '-'}"]
        if insights[:n_ins]:
            out += ["Key insights:"] + [f"- {x}" for x in insights[:n_ins]]
        if values[:n_val]:
            out += ["Key values:"] + [f"- {v.get('field', '')}: {v.get('value', '')}"
                                      + (f" ({v['location']})" if v.get("location") else "") for v in values[:n_val]]
        if meta:
            out.append("Metadata: " + "; ".join(f"{k}={json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v}"
                                                 for k, v in meta.items()))
        if preview[:n_pre]:
            out += ["Preview:"] + [f"  {x}" for x in preview[:n_pre]]
        out.append(f"More: {how}")
        return "\n".join(out)

    n_ins, n_val, n_pre = len(insights), len(values), len(preview)
    text = build(n_ins, n_val, n_pre)
    while len(text) > budget and (n_pre or n_val > 5 or n_ins > 3):
        if n_pre:
            n_pre = max(0, n_pre - 5)
        elif n_val > 5:
            n_val = max(5, n_val - 5)
        else:
            n_ins -= 1
        text = build(n_ins, n_val, n_pre)
    note = "\n[digest cut to its limit]"
    return text if len(text) <= budget else text[:budget - len(note)] + note


# ---------------------------------------------------------------------- rules digest (no model)
def call_label(name: str, args: Any) -> str:
    if not isinstance(args, dict):
        return name
    shown = {k: v for k, v in args.items() if k in ("path", "pattern", "command", "glob", "question", "pages")}
    return f"{name}(" + ", ".join(f"{k}={str(v)[:80]}" for k, v in shown.items()) + ")"


def rule_digest(text: str, name: str, args: Any) -> dict[str, Any]:
    lines = text.split("\n")
    n = len(lines)
    target = ""
    if isinstance(args, dict):
        target = str(args.get("path") or args.get("command") or args.get("pattern") or "")[:120]
    meta: dict[str, Any] = {"tool": name, "target": target, "lines": n, "chars": len(text), "tokens": tokens(text)}
    values: list[dict[str, str]] = []
    nonempty = [x.strip() for x in lines if x.strip()]
    hits = [m for m in map(GREP_RE.match, nonempty) if m]
    paths = [x for x in nonempty if PATH_RE.match(x)]
    if nonempty and len(hits) >= 0.6 * len(nonempty):          # rg -n / grep -rn output: path:line:text
        files = Counter(m.group(1) for m in hits)
        meta["matches"], meta["files"] = len(hits), len(files)
        summary = f"search output {target}: {len(hits):,} matching lines in {len(files):,} files."
        values = [{"field": f, "value": f"{c} matches"} for f, c in files.most_common(20)]
    elif nonempty and len(paths) >= 0.8 * len(nonempty):       # ls / find output: one path per line
        exts = Counter(Path(x.rstrip("/")).suffix or ("<dir>" if x.endswith("/") else "<none>") for x in paths)
        summary = f"listing {target}: {len(paths):,} entries."
        values = [{"field": e, "value": f"{c} entries"} for e, c in exts.most_common(15)]
    else:
        what = "command output" if name == "bash" else "file" if name == "read" else f"{name} output"
        summary = f"{what} {target}: {n:,} lines, ~{tokens(text):,} tokens."
        values = [{"field": f"line {i}", "value": line.strip()[:160], "location": f"L{i}"}
                  for i, line in enumerate(lines, 1) if OUTLINE_RE.match(line)][:30]
        if values:
            summary += f" Outline: {len(values)} headings/definitions listed under key values."
    flagged = [(i, line.strip()) for i, line in enumerate(lines, 1) if ERROR_RE.search(line)]
    insights = [f"L{i}: {line[:200]}" for i, line in flagged[:10]]
    if len(flagged) > 10:
        insights.append(f"{len(flagged) - 10} more lines mention error/warning/failure")
    if not flagged and name == "bash":
        insights.append("no line mentions an error or warning")
    preview = [x[:200] for x in lines[:PREVIEW_HEAD]]
    if n > PREVIEW_HEAD + PREVIEW_TAIL:
        preview += [f"... ({n - PREVIEW_HEAD - PREVIEW_TAIL:,} lines) ..."] + [x[:200] for x in lines[-PREVIEW_TAIL:]]
    else:
        preview = [x[:200] for x in lines]
    return {"summary": summary, "key_insights": insights, "key_values": values, "metadata": meta,
            "preview": preview}


def route_text(ctx: ToolContext, text: str, name: str, args: Any, source: str | None = None) -> str:
    """Rules route for a text result; `source`: the workspace file holding the full text (no copy is made)."""
    return store(ctx, folder(ctx), what=call_label(name, args), full=None if source else text, source=source,
                 digest=rule_digest(text, name, args), by="rules", size=real_tokens(ctx, text))


# ---------------------------------------------------------------------- the turn
def route_turn(ctx: ToolContext, results: list[CallResult], *, model: bool = True) -> None:
    """Rules 2 and 3, in place: a single result over the result limit is stored; then, while the turn's results
    add up to more than the turn budget, the largest are stored. Results the tool already stored (rule 1: a big
    file, a PDF or an image) count with their digest. `model=False` (an interrupted turn): rules digests only."""
    lim = limits(ctx)
    done: set[int] = set()
    for i, r in enumerate(results):
        if r.routed:
            r.routed.setdefault("rule", "file")
            done.add(i)
        elif not r.error and real_tokens(ctx, r.text) > lim.result:
            _route(ctx, r, model, "result")
            done.add(i)
    while sum(real_tokens(ctx, r.text) for r in results) > lim.turn:
        movable = [i for i, r in enumerate(results)
                   if i not in done and not r.error and real_tokens(ctx, r.text) > lim.digest]
        if not movable:                         # nothing left that a digest would make smaller
            break
        i = max(movable, key=lambda i: real_tokens(ctx, results[i].text))
        _route(ctx, results[i], model, "turn")
        done.add(i)


def _route(ctx: ToolContext, r: CallResult, model: bool, rule: str) -> None:
    """Store one result; `rule`: "result" (rule 2) or "turn" (rule 3)."""
    from ..adapters.llm import LLMError
    from ..adapters.tools import ToolError
    prev = ctx.operation
    ctx.operation = r.ref                       # the folder and any sub-agent belong to this tool call
    try:
        routed = False
        if model and r.ref is not None and r.ref.document:
            from ..adapters.documents import route_document
            try:
                r.text = route_document(ctx, ctx.workspace / r.ref.document)
                routed = True
            except (ToolError, LLMError, OSError, ValueError) as e:
                ctx.events.status("document", f"{r.ref.document}: digest failed ({e}); using the rules digest")
        if not routed:
            source = r.ref.source if r.ref is not None and r.ref.source else None
            full = (ctx.workspace / source).read_text(encoding="utf-8", errors="replace") if source else r.text
            r.text = route_text(ctx, full, r.name, r.args, source)
        if r.routed is not None:
            r.routed["rule"] = rule
    finally:
        ctx.operation = prev
