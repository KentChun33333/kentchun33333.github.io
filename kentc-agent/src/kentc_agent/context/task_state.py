"""Persist chat milestones and source excerpts separately from the model checkpoint."""

from __future__ import annotations

import json
import re
from itertools import islice
from pathlib import Path
from typing import Any

from ..adapters.session import estimate_tokens
from ..adapters.tools import Tool, ToolContext, ToolError, inside, params, rel
from .memory import WorkspaceMemory, atomic_text

STATUSES = ("pending", "in_progress", "blocked", "complete")


def _text(args: dict[str, Any], key: str, max_chars: int) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > max_chars:
        raise ToolError(f"{key} must contain 1–{max_chars} characters")
    return value


def _evidence(ctx: ToolContext, memory: WorkspaceMemory, args: dict[str, Any]) -> dict[str, Any]:
    path = inside(ctx, _text(args, "path", 4096), "evidence sources")
    line = args.get("line")
    if type(line) is not int or not 1 <= line <= 2**31 - 1:
        raise ToolError("line must be a positive 1-based line number")
    quote = _text(args, "quote", 2000)
    if not path.is_file():
        raise ToolError("evidence source must be a workspace text file")
    lines = quote.split("\n")
    with path.open(encoding="utf-8") as stream:
        source = [text.removesuffix("\n") for text in islice(stream, line - 1, line + len(lines) - 1)]
    if quote not in "\n".join(source):
        raise ToolError("quote does not match the source at the supplied line")
    end = line + len(lines) - 1
    location = f"{rel(ctx, path)}:{line}" + (f"-{end}" if end > line else "")
    entry = memory.archive(quote, kind="evidence", tokens=estimate_tokens({"content": quote}), source=location)
    return {"id": entry["id"], "source": location, "snapshot": entry["path"], "verification": "source_match"}


def milestone_dir(memory: WorkspaceMemory) -> Path:
    return memory.root / "milestones"


def task_state_tool(memory: WorkspaceMemory) -> Tool:
    directory = milestone_dir(memory)

    def run(ctx: ToolContext, args: dict[str, Any]) -> str:
        action = args.get("action")
        if action == "evidence":
            return json.dumps(_evidence(ctx, memory, args), ensure_ascii=False)
        if action == "show" and "id" not in args:
            return json.dumps([json.loads(path.read_text(encoding="utf-8"))
                               for path in sorted(directory.glob("*.json"))], ensure_ascii=False)
        if action not in ("show", "milestone"):
            raise ToolError("action must be show, milestone or evidence")
        identifier = _text(args, "id", 64)
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", identifier):
            raise ToolError("id must contain lowercase letters, digits, hyphens or underscores")
        path = directory / f"{identifier}.json"
        if action == "show":
            if not path.is_file():
                raise ToolError(f"unknown milestone: {identifier}")
            return path.read_text(encoding="utf-8")

        criterion = _text(args, "criterion", 800)
        status = args.get("status")
        if status not in STATUSES:
            raise ToolError("status must be pending, in_progress, blocked or complete")
        evidence_ids = args.get("evidence_ids", [])
        if (not isinstance(evidence_ids, list) or len(evidence_ids) > 10 or
                any(not isinstance(item, str) or not re.fullmatch(r"evidence-[a-f0-9]{16}", item)
                    for item in evidence_ids)):
            raise ToolError("evidence_ids must contain up to 10 IDs returned by the evidence action")
        if status == "complete" and not evidence_ids:
            raise ToolError("completion requires at least one recorded evidence ID")
        for evidence_id in evidence_ids:
            entry = memory.root / "entries" / f"{evidence_id}.json"
            if not entry.is_file():
                raise ToolError(f"unknown evidence in this session: {evidence_id}")
        record = {"id": identifier, "criterion": criterion, "status": status, "evidence_ids": evidence_ids}
        result = json.dumps(record, ensure_ascii=False, indent=2)
        atomic_text(path, result + "\n")
        return result

    return Tool(
        "task_state",
        "Use for meaningful milestones in multi-step tasks. Record a checkable criterion and update progress "
        "as the work changes. Capture a quote with evidence before marking a milestone complete. A source match "
        "confirms the quote and location; judge whether it supports the criterion yourself. Use show to recover "
        "progress after context compaction. Evidence snapshots are available in the workspace index.",
        params(["action"],
               action={"type": "string", "enum": ["show", "milestone", "evidence"]},
               id={"type": "string", "description": "Stable milestone ID. Omit for show to list all milestones."},
               criterion={"type": "string", "description": "Observable condition required for completion."},
               status={"type": "string", "enum": list(STATUSES)},
               evidence_ids={"type": "array", "items": {"type": "string"}},
               path={"type": "string", "description": "Workspace text file or indexed artifact path to cite."},
               line={"type": "integer", "description": "1-based line where the quote starts."},
               quote={"type": "string", "description": "Exact excerpt to match and snapshot."}),
        run,
    )
