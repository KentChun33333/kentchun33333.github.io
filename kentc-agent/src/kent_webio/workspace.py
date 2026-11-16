"""Workspace paths shared by the file browser and the agent."""

from __future__ import annotations

import os
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from kentc_agent.adapters.session import Session
from kentc_agent.adapters.tools import CORE_TOOLS, Tool, ToolContext, ToolError, page, params, rel, resolve
from kentc_agent.agent import Agent
from kentc_agent.config import STATE_DIR
from kentc_agent.context.bigcontext import limits, note_source, real_tokens, route_text

READABLE_STATE = {"memory", "operations", "cache", "attachments", "tmp"}
HTML_SUFFIXES = {".html", ".htm"}


def atomic_text(path: Path, text: str) -> None:
    """Publish a complete file, including when another writer replaces it concurrently."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def workspace_path(root: Path, name: str) -> Path:
    """Resolve a browser-visible path, excluding internal and symlinked paths."""
    relative = Path(name)
    if relative.is_absolute() or any(part == ".." or part.startswith(".") for part in relative.parts):
        raise ValueError("Choose a visible path inside the workspace.")
    path = root
    for part in relative.parts:
        if "\\" in part or any(ord(char) < 32 for char in part):
            raise ValueError("The path contains an unsupported character.")
        path /= part
        if path.is_symlink():
            raise ValueError("Symbolic links are excluded from the workspace browser.")
    return path


def children(root: Path, folder: Path) -> list[dict[str, Any]]:
    rows = []
    for path in folder.iterdir():
        if path.name.startswith(".") or path.is_symlink():
            continue
        if path.is_dir():
            rows.append({"name": path.name, "path": path.relative_to(root).as_posix(), "directory": True})
        elif path.is_file():
            try:
                size = path.stat().st_size
            except FileNotFoundError:
                continue
            rows.append({"name": path.name, "path": path.relative_to(root).as_posix(),
                         "directory": False, "bytes": size})
    return sorted(rows, key=lambda row: (not row["directory"], row["name"].casefold()))


def html_outputs(root: Path) -> list[dict[str, str]]:
    """List visible HTML deliverables, newest first, without opening their contents."""
    results = []
    for folder, directories, names in os.walk(root):
        directories[:] = [name for name in directories if not name.startswith(".")]
        for name in names:
            if Path(name).suffix.lower() not in HTML_SUFFIXES:
                continue
            relative = (Path(folder) / name).relative_to(root).as_posix()
            try:
                file = workspace_path(root, relative)
                if file.is_file():
                    results.append((file.stat().st_mtime_ns, relative))
            except (OSError, ValueError):
                continue
    results.sort(key=lambda entry: (-entry[0], entry[1].casefold(), entry[1]))
    return [{"path": path, "version": str(modified)} for modified, path in results]


def list_files(ctx: ToolContext, args: dict[str, Any]) -> str:
    try:
        folder = workspace_path(ctx.workspace, args.get("path", ""))
        return "\n".join(("directory" if row["directory"] else "file") + "  " + row["path"]
                         for row in children(ctx.workspace, folder)) or "(empty folder)"
    except (ValueError, OSError) as error:
        raise ToolError(str(error)) from None


def read_pdf_text(ctx: ToolContext, args: dict[str, Any]) -> str:
    from kentc_agent.adapters.documents.loaders import load_pdf

    try:
        path = workspace_path(ctx.workspace, args["path"])
    except ValueError as error:
        raise ToolError(str(error)) from None
    if path.suffix.lower() != ".pdf" or not path.is_file():
        raise ToolError("Choose an existing PDF in the workspace.")
    local = replace(ctx, settings=ctx.settings.with_overrides(doc_render="never"))
    source = load_pdf(local, path, args.get("pages"))
    text = source.markdown() + "\n\n[Embedded text only. Use read with a focused question for scans, figures, or layout.]"
    if args.get("offset") or args.get("limit"):
        return page(text, args.get("offset"), args.get("limit"), ctx, "the embedded PDF text")
    if real_tokens(ctx, text) > limits(ctx).result:
        return route_text(ctx, text, "read_pdf_text", args, source=rel(ctx, path))
    note_source(ctx, rel(ctx, path))
    return text


TOOLS = [CORE_TOOLS[name] for name in ("read", "write", "edit")] + [
    Tool("list_files", "List one visible workspace folder. Omit path to list the workspace root.",
         params([], path={"type": "string"}), list_files),
    Tool("read_pdf_text", "Read the embedded text of a workspace PDF locally with page labels. "
         "Use read with a question for scans, charts, and visual layout.",
         params(["path"], path={"type": "string"}, pages={"type": "string", "description": "PDF pages, e.g. 1-5,9"},
                offset={"type": "integer", "description": "1-based line offset in the selected text"},
                limit={"type": "integer", "description": "Maximum lines to return"}), read_pdf_text),
]


class WorkspaceAgent(Agent):
    """Keep agent file access within the selected workspace and protect runtime state."""

    def __init__(self, ctx: ToolContext, *, tools: list[Tool], session: Session, instructions: str,
                 name: str = "main", include_workspace_instructions: bool = False) -> None:
        self.include_workspace_instructions = include_workspace_instructions
        super().__init__(ctx, tools=tools, session=session, instructions=instructions, name=name)
        self.saved_outputs: dict[str, None] = {}

    def _tool(self, name: str, args: Any) -> tuple[str, bool]:
        path = args.get("path") if isinstance(args, dict) else None
        relative = None
        if name in ("read", "write", "edit") and isinstance(path, str):
            try:
                relative = resolve(self.ctx, path).relative_to(self.ctx.workspace)
                archive_read = (name == "read" and len(relative.parts) >= 3
                                and relative.parts[0] == STATE_DIR and relative.parts[1] in READABLE_STATE)
                if not archive_read and any(part.startswith(".") for part in relative.parts):
                    return "Error: this path is reserved for workspace runtime data.", True
            except (OSError, ValueError):
                return "Error: choose a path inside the workspace.", True
        result, error = super()._tool(name, args)
        if not error and name in ("write", "edit") and relative is not None and relative.suffix.lower() in HTML_SUFFIXES:
            output = relative.as_posix()
            try:
                workspace_path(self.ctx.workspace, output)
            except (OSError, ValueError):
                return result, error
            self.saved_outputs[output] = None
        return result, error
