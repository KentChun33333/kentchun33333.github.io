"""Studio domain model: a case (of one app), its jobs, and the event feed adapter."""

from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from kentc_agent.ports import Events

from .store import atomic_write_json, read_json

CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MAX_EVENTS = 2000
SETTLED = ("done", "failed", "stopped")
LANE_MAX_CHARS = 48_000        # a lane's documents handed to a per-lane agent as text (~12k tokens)


@dataclass
class Job:
    id: str
    role: str                      # insight | query | extra | report
    agent: str                     # the app's agent / pull / extra name
    target: str = ""               # insight: a file name or "lane:<lane>"; extra name; report version "v<n>"
    params: dict[str, Any] = field(default_factory=dict)
    after: list[str] = field(default_factory=list)
    status: str = "queued"         # queued | running | done | failed | stopped
    created: float = field(default_factory=time.time)
    started: float | None = None
    finished: float | None = None
    error: str | None = None


class Case:
    def __init__(self, root: Path, data: dict[str, Any]) -> None:
        self.root = root
        self.id: str = data["id"]
        self.app: str = data["app"]
        self.fields: dict[str, str] = {k: str(v or "") for k, v in (data.get("fields") or {}).items()}
        self.created: float = data.get("created", time.time())
        self.updated: float = data.get("updated", self.created)
        self.documents: list[dict[str, Any]] = data.get("documents", [])     # name, lane, size, uploaded
        self.jobs: list[Job] = [Job(**j) for j in data.get("jobs", [])]
        self.corrections: list[dict[str, Any]] = data.get("corrections", [])
        self.reports: list[dict[str, Any]] = data.get("reports", [])
        self.approved: dict[str, Any] | None = data.get("approved")
        self.trace: list[dict[str, Any]] = data.get("trace", [])
        self.events: list[dict[str, Any]] = []
        self.seq = 0
        self.live = {"agent": "", "kind": "", "text": ""}
        self.tokens = {"used": 0, "window": 0}
        self.stopping: set[str] = set()          # running jobs asked to stop
        self.progress: dict[str, str] = {}       # running data pull -> latest progress line
        self.lock = threading.RLock()
        f = self.dir / "events.jsonl"
        if f.is_file():
            self.events = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines()[-MAX_EVENTS:] if x.strip()]
            self.seq = self.events[-1]["seq"] if self.events else 0

    # -------------------------------------------------------------- paths and files
    @property
    def dir(self) -> Path:
        return self.root / self.id

    def out(self, *parts: str) -> Path:
        return self.dir.joinpath("outputs", *parts)

    def read_json(self, path: Path) -> Any:
        return read_json(path)

    def write_json(self, path: Path, data: Any) -> None:
        atomic_write_json(path, data)

    def save(self) -> None:
        with self.lock:
            self.updated = time.time()
            self.write_json(self.dir / "case.json", {
                "id": self.id, "app": self.app, "fields": self.fields, "created": self.created,
                "updated": self.updated, "documents": self.documents, "jobs": [asdict(j) for j in self.jobs],
                "corrections": self.corrections, "reports": self.reports, "approved": self.approved,
                "trace": self.trace})

    def meta(self) -> dict[str, Any]:
        return {"id": self.id, "app": self.app, "fields": self.fields}

    def docs(self, lane: str | None = None) -> list[str]:
        return [d["name"] for d in self.documents if lane is None or d["lane"] == lane]

    def lane_of(self, name: str) -> str | None:
        return next((d["lane"] for d in self.documents if d["name"] == name), None)

    # -------------------------------------------------------------- activity
    def event(self, kind: str, agent: str, text: str, job: str = "") -> None:
        with self.lock:
            self.seq += 1
            ev = {"seq": self.seq, "time": time.time(), "kind": kind, "agent": agent, "job": job, "text": text[:600]}
            self.events.append(ev)
            del self.events[:-MAX_EVENTS]
            self.dir.mkdir(parents=True, exist_ok=True)
            with (self.dir / "events.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    def audit(self, actor: str, event: str) -> None:
        """Decision trace: HUM (analyst), AGT (agent job), SYS."""
        self.trace.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "actor": actor, "event": event})

    def last_job(self, role: str, target: str | None = None) -> Job | None:
        js = [j for j in self.jobs if j.role == role and (target is None or j.target == target)]
        return js[-1] if js else None


class JobEvents(Events):
    """Agent events -> the case feed, tagged with the job. A Stop request surfaces as Aborted at the next event."""

    def __init__(self, case: Case, job: Job, label: str) -> None:
        self.case, self.job, self.label = case, job, label

    def cancelled(self) -> bool:
        return self.job.id in self.case.stopping

    def _check(self) -> None:
        if self.cancelled():
            from kentc_agent.errors import Aborted
            raise Aborted()

    def delta(self, agent: str, kind: str, text: str) -> None:
        self._check()
        if kind == "tool":
            return
        who = "parsing sub-agent" if agent == "document" else self.label
        live = self.case.live
        if live.get("job") != self.job.id or live.get("kind") != kind or live.get("agent") != who:
            self.case.live = live = {"agent": who, "kind": kind, "job": self.job.id, "text": ""}
        live["text"] = (live["text"] + text)[-1500:]

    def tool_start(self, agent: str, name: str, args: dict[str, Any]) -> None:
        self._check()
        shown = ", ".join(f"{k}={json.dumps(v, ensure_ascii=False)[:70]}" for k, v in args.items()
                          if k not in ("content", "new_text", "old_text"))
        self.case.event("tool", self.label, f"{name}({shown})", self.job.id)

    def tool_end(self, agent: str, name: str, result: str, error: bool) -> None:
        lines = result.strip().splitlines() or [""]
        more = f"  (+{len(lines) - 1} lines)" if len(lines) > 1 else ""
        self.case.event("error" if error else "result", self.label, lines[0][:200] + more, self.job.id)

    def compaction(self, agent: str, before: int, after: int) -> None:
        self.case.event("compaction", self.label, f"context compacted: {before:,} → {after:,} tokens", self.job.id)

    def status(self, agent: str, text: str) -> None:
        self._check()
        who = "parsing sub-agent" if agent == "document" else self.label
        if self.job.role == "query":
            self.case.progress[self.job.id] = text
        self.case.event("status", who, text, self.job.id)

    def turn_end(self, agent: str, tokens: int, window: int) -> None:
        if agent != "document":
            self.case.tokens = {"used": tokens, "window": window}
