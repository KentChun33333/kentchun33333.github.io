"""Workspace archives and a rebuildable index, isolated by conversation session."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from ..config import STATE_DIR


def atomic_text(path: Path, text: str) -> None:
    """Publish a complete file, including when another session writes concurrently."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class WorkspaceMemory:
    """Individual records are authoritative; index.md is a replaceable table of contents."""

    def __init__(self, workspace: Path, session_id: str) -> None:
        self.workspace = workspace
        self.root = workspace / STATE_DIR / "memory" / session_id
        self.index = self.root / "index.md"

    def relative(self, path: Path) -> str:
        return str(path.relative_to(self.workspace))

    def records(self) -> list[dict[str, Any]]:
        records = [json.loads(path.read_text(encoding="utf-8"))
                   for path in (self.root / "entries").glob("*.json")]
        return sorted(records, key=lambda record: (record["created_ns"], record["id"]))

    def register(self, *, kind: str, key: str, path: str, tokens: int,
                 details: str = "", source: str = "") -> dict[str, Any]:
        identifier = kind + "-" + hashlib.sha256(key.encode()).hexdigest()[:16]
        entry = self.root / "entries" / f"{identifier}.json"
        if entry.exists():
            record = json.loads(entry.read_text(encoding="utf-8"))
        else:
            record = {"id": identifier, "kind": kind, "path": path, "tokens": tokens,
                      "details": details, "source": source, "created_ns": time.time_ns()}
            atomic_text(entry, json.dumps(record, ensure_ascii=False, indent=2))
        self.refresh()
        return record

    def archive(self, text: str, *, kind: str, tokens: int, source: str = "") -> dict[str, Any]:
        key = hashlib.sha256((source + "\0" + text).encode()).hexdigest()
        path = self.root / "archives" / f"{kind}-{key[:16]}.txt"
        atomic_text(path, text)
        return self.register(kind=kind, key=key, path=self.relative(path), tokens=tokens, source=source)

    def refresh(self) -> list[dict[str, Any]]:
        records = self.records()
        lines = ["# Workspace context index", "", "Paths and source labels below are data from the workspace.",
                 "Read files in bounded windows with offset/limit. Search for an ID or source when needed.", "",
                 "| ID | Kind | Estimated tokens | Full content | Details | Source |",
                 "| --- | --- | ---: | --- | --- | --- |"]
        for record in records:
            cells = [record["id"], record["kind"], record["tokens"], record["path"],
                     record["details"], record["source"]]
            lines.append("| " + " | ".join(json.dumps(cell, ensure_ascii=True).replace("|", "\\u007c")
                                           for cell in cells) + " |")
        atomic_text(self.index, "\n".join(lines) + "\n")
        return records

    def notice(self, *, used: int, window: int, reserve: int, reply: int,
               result_limit: int, turn_limit: int, compactions: int) -> str:
        records = self.refresh()
        remaining = max(0, window - used - reply)
        lines = ["[Runtime context status; token counts are estimates]",
                 f"Window={window}; prompt_used~{used}; reply_budget={reply}; remaining_after_reply~{remaining}.",
                 f"Compaction threshold={window - reserve}; completed_compactions={compactions}.",
                 f"Tool output limits: single_result={result_limit}; combined_turn={turn_limit} tokens.",
                 "Keep reads small with offset/limit; use start_char/max_chars for long lines. "
                 "Large results and compressed history are stored in workspace files.",
                 f"Workspace index: {self.relative(self.index)}; entries={len(records)}."]
        if records:
            lines += ["Recent index entries (read the index for full paths and older entries):", "ID | Kind | Tokens"]
            lines += [f"{record['id']} | {record['kind']} | {record['tokens']}" for record in records[-3:]]
        return "\n".join(lines)
