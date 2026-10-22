"""Persistence helpers for the studio: atomic JSON writes and case discovery."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections.abc import Callable, Collection
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, text: str) -> None:
    """Write text and replace the target atomically, so a crash never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def atomic_write_json(path: Path, data: Any, *, indent: int = 1) -> None:
    atomic_write_text(path, json.dumps(data, indent=indent, ensure_ascii=False))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


class CaseStore:
    """The case folder layout on disk: discovery and (atomic) access to the case index."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def case_files(self) -> list[Path]:
        return sorted(self.root.glob("*/case.json"))

    def load_all(self, factory: Callable[..., Any], apps: Collection[str]) -> dict[str, Any]:
        """factory: Case(root, data). -> by case id; interrupted jobs are marked stopped. A case without one of
        `apps` (created before studio apps, or its app was removed from studio.yaml) is skipped, never deleted."""
        cases: dict[str, Any] = {}
        for f in self.case_files():
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("app") not in apps:
                why = f"its app {data['app']!r} is not in studio.yaml" if data.get("app") else \
                    "created before studio apps; delete the folder or recreate the case"
                print(f"skipped {f.parent}: {why}", file=sys.stderr)
                continue
            case = factory(self.root, data)
            for job in case.jobs:
                if job.status in ("queued", "running"):
                    job.status, job.error = "stopped", "interrupted by a server restart"
            case.save()
            cases[case.id] = case
        return cases
