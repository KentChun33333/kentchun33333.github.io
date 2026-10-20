"""Cases and their asynchronous agent jobs.

A case folder <workspace>/cases/<case id>/ holds:
    case.json             identity, documents (name + role), jobs, corrections, report versions, trace
    docs/                 uploaded documents (role `context`: must; role `doc`: optional evidence)
    outputs/docs/<f>.json latest doc-agent extraction per document
    outputs/context.json  latest context-agent summary
    outputs/data/<p>.json latest data pull (parameters, SQL, row count, key values, preview)
    data/<p>.csv          the pulled rows
    outputs/extra/<a>.json extra agent results
    outputs/reports/v<n>.json / .md   TER report versions
    jobs/<job id>/        each job's materials, workflow state and agent session
    events.jsonl          the activity feed

The dispatcher runs local-model jobs one at a time, and data pulls and external-agent jobs in parallel.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict
import uuid
from pathlib import Path
from typing import Any

from kentc_agent.adapters.documents import load_source, read_document
from kentc_agent.adapters.llm import LLMClient
from kentc_agent.adapters.tools import ToolContext, ToolError, reject_unsupported
from kentc_agent.agent import Events
from kentc_agent.config import load_settings

from ..config import StudioConfig, load_config
from ..data import PARAMS
from ..jobs.queue import JobDispatcher
from ..models import (CASE_ID_RE, CONTEXT_MAX_CHARS, ROLES, SETTLED, Case, Job)
from ..report import to_markdown
from ..store import CaseStore


class CaseService:
    def __init__(self, workspace: Path, config_path: Path, effort: str | None = None) -> None:
        self.ws = workspace
        self.root = workspace / "cases"
        self.root.mkdir(parents=True, exist_ok=True)
        self.config: StudioConfig = load_config(config_path)
        self.settings = load_settings(workspace, {"reasoning_effort": effort})
        self.llm = LLMClient(self.settings)
        self.store = CaseStore(self.root)
        self.cases: dict[str, Case] = self.store.load_all(Case)
        self.dispatcher = JobDispatcher(self)
        self.dispatcher.start()

    def provider(self, job: Job):
        if job.role == "extra":
            return self.config.extras[job.agent]
        if job.role == "query":
            return self.config.pulls[job.agent]
        return self.config.agents[job.role]

    def label(self, job: Job) -> str:
        try:
            p = self.provider(job)
        except KeyError:                          # removed from studio.yaml since the job ran
            return job.agent
        return f"{p.label} · {job.target}" if job.role == "doc" else f"Data · {p.label}" if job.role == "query" \
            else p.label

    # -------------------------------------------------------------- creating work
    def _job(self, case: Case, role: str, agent: str, target: str = "", params: dict[str, Any] | None = None,
             after: list[str] | None = None) -> Job:
        job = Job(id=f"{time.strftime('%H%M%S')}-{role}-{uuid.uuid4().hex[:5]}", role=role, agent=agent,
                  target=target, params=params or {}, after=after or [])
        case.jobs.append(job)
        case.event("queued", self.label(job), "queued", job.id)
        return job

    def _pending(self, case: Case, roles: tuple[str, ...]) -> list[str]:
        return [j.id for j in case.jobs if j.role in roles and j.status in ("queued", "running")]

    def _extract(self, case: Case, names: list[str], feedback: dict[str, str] | None = None) -> None:
        """Doc-agent jobs, one per evidence document."""
        feedback = feedback or {}
        names = [n for n in names if n in case.docs("doc")]
        if not names:
            return
        with case.lock:
            for n in names:
                self._job(case, "doc", "doc", n, {"feedback": feedback.get(n, "")})
            case.save()
        self._wake()

    def _summarise(self, case: Case, feedback: str = "") -> None:
        """One context-agent job over the context documents. It does not depend on the doc agent; a still-queued
        earlier summary is dropped because this one covers the same documents."""
        with case.lock:
            for j in case.jobs:
                if j.role == "context" and j.status == "queued":
                    j.status, j.error = "stopped", "superseded by a newer summary request"
            self._job(case, "context", "context", "summary", {"feedback": feedback})
            case.save()
        self._wake()

    def default_pulls(self, trigger: str) -> list[str]:
        return [n for n, p in self.config.pulls.items() if p.selected_for(trigger)]

    def pull(self, case: Case, names: list[str], params: dict[str, str] | None = None, who: str = "HUM") -> list[Job]:
        """Data-pull jobs. They do not use the model, so they start at once, in parallel with the agents. A queued
        or running pull of the same template is superseded. `params` override case fields for this pull only."""
        unknown = [n for n in names if n not in self.config.pulls]
        if unknown:
            raise ValueError(f"unknown data pull(s): {', '.join(unknown)}")
        params = {k: str(v).strip() for k, v in (params or {}).items() if str(v).strip()}
        bad = sorted(set(params) - set(PARAMS))
        if bad:
            raise ValueError(f"unknown pull parameter(s): {', '.join(bad)}; use {', '.join(PARAMS)}")
        jobs = []
        with case.lock:
            for n in names:
                for j in case.jobs:
                    if j.role == "query" and j.target == n and j.status == "queued":
                        j.status, j.error = "stopped", "superseded by a newer pull"
                    elif j.role == "query" and j.target == n and j.status == "running":
                        case.stopping.add(j.id)
                jobs.append(self._job(case, "query", n, n, {"params": params}))
            if names:
                shown = ", ".join(f"{k}={v}" for k, v in params.items())
                case.audit(who, f"data pull(s) queued: {', '.join(names)}" + (f" ({shown})" if shown else ""))
            case.save()
        self._wake()
        return jobs

    def save_uploads(self, case: Case, files: list[tuple[str, str, bytes]]) -> list[str]:
        """Store (name, role, data) uploads; a re-uploaded name replaces the earlier file. -> names."""
        folder = case.dir / "docs"
        folder.mkdir(parents=True, exist_ok=True)
        names = []
        for name, role, data in files:
            name = Path(name).name
            if not name or name.startswith("."):
                continue
            if role not in ROLES:
                raise ValueError(f"{name}: role must be context or doc")
            try:
                reject_unsupported(Path(name))
            except ToolError as e:
                raise ValueError(str(e)) from None
            (folder / name).write_bytes(data)
            case.documents = [d for d in case.documents if d["name"] != name]
            case.documents.append({"name": name, "role": role, "size": len(data), "uploaded": time.time()})
            names.append(name)
        return names

    def create_case(self, meta: dict[str, str], files: list[tuple[str, str, bytes]], use_sample: Path | None,
                    pulls: list[str] | None = None) -> Case:
        """`pulls`: the data pulls to run; None = the ones pre-ticked for this trigger."""
        cid = meta["id"].strip()
        if not CASE_ID_RE.match(cid):
            raise ValueError("case ID: letters, digits, '.', '_' or '-' (max 64)")
        if cid in self.cases:
            raise FileExistsError(f"case {cid} already exists")
        pulls = self.default_pulls(meta.get("trigger", "")) if pulls is None else pulls
        unknown = [n for n in pulls if n not in self.config.pulls]
        if unknown:
            raise ValueError(f"unknown data pull(s): {', '.join(unknown)}")
        case = Case(self.root, meta)
        try:
            if use_sample is not None:
                files = [(f.name, "context" if f.suffix.lower() in (".eml", ".msg") else "doc", f.read_bytes())
                         for f in sorted(use_sample.iterdir()) if f.is_file() and not f.name.startswith(".")] + files
            self.save_uploads(case, files)
            if not case.docs("context"):
                raise ValueError("stage at least one context document (trigger e-mail, customer explanation, "
                                 "case note) - the context agent needs it")
        except ValueError:
            shutil.rmtree(case.dir, ignore_errors=True)
            raise
        case.audit("HUM", f"case submitted with {len(case.documents)} documents "
                          f"({len(case.docs('context'))} context, {len(case.docs('doc'))} evidence)")
        self.cases[cid] = case
        self.pull(case, pulls, who="SYS")         # no model: these start at once, alongside the agents
        self._summarise(case)                    # first model job: the trigger context appears on Page 2 quickly
        self._extract(case, case.docs("doc"))
        return case

    def add_documents(self, case: Case, files: list[tuple[str, str, bytes]]) -> list[str]:
        names = self.save_uploads(case, files)
        if not names:
            raise ValueError("no files")
        case.audit("HUM", f"uploaded {', '.join(names)}")
        if any(n in case.docs("context") for n in names):
            self._summarise(case)
        self._extract(case, names)
        return names

    def feedback(self, case: Case, target: str, note: str, field_name: str = "", value: str = "") -> None:
        """An analyst correction: re-extract that document (or re-summarise the context) with the note."""
        note = note.strip()
        if not note and not value:
            raise ValueError("say what is wrong")
        entry = {"time": time.time(), "target": target, "field": field_name, "analyst_value": value, "note": note}
        if target != "context":
            if target not in case.docs():
                raise ValueError(f"no document {target}")
            prev = case.read_json(case.out("docs", f"{target}.json")) or {}
            entry["agent_value"] = next((kv.get("value") for kv in prev.get("key_values", [])
                                         if kv.get("field") == field_name), "") if field_name else ""
        case.corrections.append(entry)
        what = f"{field_name} in {target}" if field_name else target
        case.audit("HUM", f"feedback on {what}: {note or value}")
        text = (f"Field '{field_name}': " if field_name else "") + \
            (f"the correct value is {value}. " if value else "") + note
        if target == "context":
            self._summarise(case, text)
        elif target in case.docs("doc"):
            self._extract(case, [target], {target: text})
        else:                                   # a context document: the context agent summarises again
            self._summarise(case, f"{target}: {text}")

    def request_report(self, case: Case, extras: list[str], instruction: str = "") -> Job:
        unknown = [e for e in extras if e not in self.config.extras]
        if unknown:
            raise ValueError(f"unknown extra agent(s): {', '.join(unknown)}")
        if instruction and not case.reports:
            instruction = ""
        with case.lock:
            before = self._pending(case, ("doc", "context", "query"))
            ex = [self._job(case, "extra", e, e, after=before) for e in extras]
            version = len(case.reports) + 1 + len(self._pending(case, ("report",)))
            job = self._job(case, "report", "report", f"v{version}",
                            {"instruction": instruction.strip(), "extras": extras},
                            after=before + [j.id for j in ex] + self._pending(case, ("report",)))
            case.audit("HUM", (f"asked for TER report revision v{version}: {instruction.strip()}" if instruction
                               else f"asked for TER report v{version}") +
                       (f" with {', '.join(extras)}" if extras else ""))
            case.save()
        self._wake()
        return job

    def approve(self, case: Case, version: int) -> None:
        if not any(r["version"] == version for r in case.reports):
            raise ValueError(f"no report v{version}")
        case.approved = {"version": version, "time": time.time()}
        case.audit("HUM", f"approved TER report v{version}")
        case.save()

    def stop(self, case: Case) -> None:
        with case.lock:
            for j in case.jobs:
                if j.status == "queued":
                    j.status, j.error = "stopped", "stopped by the analyst"
                elif j.status == "running":
                    case.stopping.add(j.id)
            case.audit("HUM", "stopped the agents")
            case.save()

    def stop_job(self, case: Case, job_id: str) -> None:
        job = next((j for j in case.jobs if j.id == job_id), None)
        if job is None:
            raise ValueError(f"no job {job_id}")
        with case.lock:
            if job.status == "queued":
                job.status, job.error = "stopped", "stopped by the analyst"
            elif job.status == "running":
                case.stopping.add(job.id)
            else:
                raise ValueError(f"{self.label(job)} already {job.status}")
            case.audit("HUM", f"stopped {self.label(job)}")
            case.save()

    def retry(self, case: Case) -> int:
        """Queue again the latest job of each target whose last attempt failed or was stopped."""
        latest: dict[tuple[str, str], Job] = {}
        for j in case.jobs:
            latest[(j.role, j.target)] = j
        again = [j for j in latest.values() if j.status in ("failed", "stopped")]
        with case.lock:
            for j in again:
                self._job(case, j.role, j.agent, j.target, dict(j.params),
                          after=self._pending(case, ("doc", "context", "query")) if j.role in ("extra", "report")
                          else [])
            case.save()
        self._wake()
        return len(again)

    # -------------------------------------------------------------- dispatching
    def _wake(self) -> None:
        self.dispatcher.wake()

    def materials(self, case: Case) -> dict[str, Any]:
        """Everything the agents know about the case, for the extra and report agents."""
        docs = []
        for d in case.documents:
            ext = case.read_json(case.out("docs", f"{d['name']}.json")) if d["role"] == "doc" else None
            docs.append({"file": f"docs/{d['name']}", "role": d["role"],
                         "extraction": {k: ext.get(k) for k in ("document_type", "reference", "summary", "key_values",
                                                                 "anomalies")} if ext else None})
        extras = {p.stem: case.read_json(p) for p in sorted(case.out("extra").glob("*.json"))} \
            if case.out("extra").is_dir() else {}
        pulls = {}
        for p in sorted(case.out("data").glob("*.json")) if case.out("data").is_dir() else []:
            r = case.read_json(p) or {}
            pulls[p.stem] = {k: r.get(k) for k in ("label", "database", "params", "rows", "truncated", "key_values",
                                                   "file")}
        return {"case": case.meta(), "context_summary": case.read_json(case.out("context.json")),
                "documents": docs, "data_pulls": pulls, "extra_agents": extras,
                "analyst_corrections": case.corrections}

    def _context_text(self, case: Case, events: Events) -> str:
        """The context documents as text for the context agent: each one converted (or digested by the parsing
        sub-agent when it is a PDF, an image or large), plus its attachments the same way. Cached digests make
        a re-summary cheap."""
        ctx = ToolContext(case.dir, self.settings, self.llm, events)
        parts = []
        for name in case.docs("context"):
            path = case.dir / "docs" / name
            try:
                parts.append(f"## {name}\n\n{read_document(ctx, path)}")
                attachments = load_source(ctx, path).attachments
            except ToolError as e:
                parts.append(f"## {name}\n\n[not readable: {e}]")
                continue
            for att in attachments:
                try:
                    parts.append(f"### Attachment of {name}: {att.name}\n\n{read_document(ctx, att)}")
                except ToolError as e:
                    parts.append(f"### Attachment of {name}: {att.name}\n\n[not readable: {e}]")
        text = "\n\n".join(parts)
        if len(text) > CONTEXT_MAX_CHARS:
            text = text[:CONTEXT_MAX_CHARS] + "\n\n[context documents truncated]"
        return text

    def _inputs(self, case: Case, job: Job, job_dir: Path, events: Events) -> dict[str, Any]:
        def rel(p: Path) -> str:
            return str(p.relative_to(case.dir))

        if job.role == "query":                  # the SQL parameters: case fields, then this pull's overrides
            binds = {k: getattr(case, k) for k in PARAMS if k != "case_id"}
            return {**binds, "case_id": case.id, **(job.params.get("params") or {})}
        if job.role == "doc":
            prev = case.read_json(case.out("docs", f"{job.target}.json"))
            return {"file": f"docs/{job.target}", "case_brief": case.brief(),
                    "feedback": job.params.get("feedback", ""),
                    "previous": json.dumps({k: prev.get(k) for k in ("key_values", "anomalies")},
                                           ensure_ascii=False) if prev and job.params.get("feedback") else ""}
        if job.role == "context":
            (job_dir / "context.md").write_text(self._context_text(case, events), encoding="utf-8")
            return {"context_file": rel(job_dir / "context.md"), "case_brief": case.brief(),
                    "feedback": job.params.get("feedback", "")}
        case.write_json(job_dir / "materials.json", self.materials(case))
        if job.role == "extra":
            return {"materials_file": rel(job_dir / "materials.json"), "case_brief": case.brief()}
        inputs = {"materials_file": rel(job_dir / "materials.json"), "case_brief": case.brief(),
                  "instruction": job.params.get("instruction", ""), "previous_report_file": ""}
        if inputs["instruction"] and case.reports:
            last = case.reports[-1]["version"]
            inputs["previous_report_file"] = rel(case.out("reports", f"v{last}.json"))
        return inputs

    def _store(self, case: Case, job: Job, result: dict[str, Any]) -> None:
        now = time.time()
        if job.role == "doc":
            case.write_json(case.out("docs", f"{job.target}.json"),
                            {**result, "file": job.target, "job": job.id, "updated": now,
                             "feedback": job.params.get("feedback", "")})
        elif job.role == "context":
            case.write_json(case.out("context.json"), {**result, "job": job.id, "updated": now})
        elif job.role == "query":
            case.write_json(case.out("data", f"{job.target}.json"), {**result, "job": job.id, "updated": now})
        elif job.role == "extra":
            case.write_json(case.out("extra", f"{job.target}.json"), {**result, "job": job.id, "updated": now})
        else:
            version = len(case.reports) + 1
            job.target = f"v{version}"
            case.write_json(case.out("reports", f"v{version}.json"), result)
            case.out("reports", f"v{version}.md").write_text(to_markdown(case.meta(), result, version),
                                                              encoding="utf-8")
            case.reports.append({"version": version, "job": job.id, "created": now,
                                 "instruction": job.params.get("instruction", ""),
                                 "extras": job.params.get("extras", [])})
            case.approved = None                 # a new version needs a new approval

    # -------------------------------------------------------------- views
    def _evidence_time(self, case: Case) -> float:
        return max([j.finished or 0 for j in case.jobs
                    if j.role in ("doc", "context", "query", "extra") and j.status == "done"]
                   + [c["time"] for c in case.corrections] + [0])

    def view(self, case: Case) -> dict[str, Any]:
        """The queue row: status text, recommendation, progress and where Detail goes."""
        jobs = case.jobs
        active = [j for j in jobs if j.status in ("queued", "running")]
        running = [j for j in jobs if j.status == "running"]
        latest: dict[tuple[str, str], Job] = {}
        for j in jobs:
            latest[(j.role, j.target)] = j
        failed = [j for j in latest.values() if j.status == "failed"]
        report = case.reports[-1] if case.reports else None
        rdata = case.read_json(case.out("reports", f"v{report['version']}.json")) if report else None
        stale = bool(report and self._evidence_time(case) > report["created"])
        extracted = any(case.out("docs", f"{n}.json").is_file() for n in case.docs("doc")) or \
            case.out("context.json").is_file() or any(case.out("data").glob("*.json"))
        stage, page = "", (3 if report else 2)      # Page 2 opens at once and fills in as jobs finish
        if active:
            since = min(a.created for a in active)

            def batch(role: str) -> tuple[int, int]:
                js = [j for j in jobs if j.role == role and (j.status in ("queued", "running") or
                                                             (j.finished or 0) >= since)]
                return sum(j.status in SETTLED for j in js), len(js)
            (ddone, dtotal), (qdone, qtotal) = batch("doc"), batch("query")
            model = [j for j in running if j.role != "query"]
            r = model[0] if model else None
            if r is None and any(j.role == "query" for j in running):
                label, stage = f"Pulling data ({qdone}/{qtotal})", "Data pull"
            elif r is None:
                label = f"Queued · {len(active)} agent job(s)"
                stage = "Queued"
            elif r.role == "doc":
                label, stage = f"Parsing documents ({ddone}/{dtotal})", "Doc agent"
            elif r.role == "context":
                label, stage = "Summarising context", "Context agent"
            elif r.role == "extra":
                label, stage = f"Running {self.provider(r).label}", "Extra agent"
            else:
                label = "Revising TER report" if r.params.get("instruction") else "Drafting TER report"
                stage = "Report agent"
            if stage != "Data pull" and qdone < qtotal:
                label += f" · data {qdone}/{qtotal}"
            rec = "IN PROGRESS"
            if any(j.role in ("report", "extra") for j in active):
                page = 3
        elif failed:
            label, rec, stage = f"{self.label(failed[0])} failed", "ERROR", "Failed"
        elif case.approved:
            label, rec, stage = f"Approved · TER v{case.approved['version']}", "APPROVED", "Approved"
        elif report:
            nxt = str(((rdata or {}).get("recommendation") or {}).get("next_step", ""))
            if stale:
                label, rec = "New evidence · report out of date", "REGENERATE"
            else:
                label = f"TER report v{report['version']} ready · review"
                rec = "REQUEST DOCUMENTS" if (rdata or {}).get("document_requests") else \
                    "FURTHER INVESTIGATION" if "further" in nxt.lower() else "AGREE"
            stage = "Report"
        elif extracted:
            label, rec, stage = "Evidence extracted · review required", "PENDING REVIEW", "Extraction"
        else:
            label, rec = "Staged", "—"
        first = min((j.started for j in jobs if j.started), default=None)
        last = max((j.finished or time.time() for j in jobs if j.started), default=None)
        return {**case.meta(), "status": "running" if running else "queued" if active else
                "failed" if failed else "approved" if case.approved else "ready" if (report or extracted) else "staged",
                "label": label, "recommendation": rec, "stage": stage, "page": page, "stale": stale,
                "created": case.created, "updated": case.updated, "documents": len(case.documents),
                "versions": len(case.reports), "elapsed": round(last - first) if first and last else 0,
                "customer": case.customer}

    def detail(self, case: Case) -> dict[str, Any]:
        jobs_by_target: dict[tuple[str, str], Job] = {}
        for j in case.jobs:
            jobs_by_target[(j.role, j.target)] = j
        docs = []
        for d in case.documents:
            j = jobs_by_target.get(("doc", d["name"])) if d["role"] == "doc" else None
            docs.append({**d, "status": (j.status if j else "done" if d["role"] == "context" else "staged"),
                         "error": j.error if j else None,
                         "extraction": case.read_json(case.out("docs", f"{d['name']}.json"))
                         if d["role"] == "doc" else None,
                         "corrections": [c for c in case.corrections if c["target"] == d["name"]]})
        cj = jobs_by_target.get(("context", "summary"))
        data = []
        for name, p in self.config.pulls.items():
            j = jobs_by_target.get(("query", name))
            data.append({"name": name, "label": p.label, "description": p.description, "database": p.database.label,
                         "binds": p.binds, "preselected": p.selected_for(case.trigger),
                         "status": j.status if j else None, "error": j.error if j else None,
                         "job": j.id if j else None, "started": j.started if j else None,
                         "params": (j.params.get("params") or {}) if j else {},
                         "progress": case.progress.get(j.id, "") if j else "",
                         "result": case.read_json(case.out("data", f"{name}.json"))})
        reports = [{**r, "data": case.read_json(case.out("reports", f"v{r['version']}.json"))} for r in case.reports]
        extras = {name: {"label": p.label, "default": p.default, "remote": not p.local, "describe": p.describe(),
                         "result": case.read_json(case.out("extra", f"{name}.json")),
                         "status": (jobs_by_target.get(("extra", name)).status
                                    if jobs_by_target.get(("extra", name)) else None)}
                  for name, p in self.config.extras.items()}
        return {**self.view(case), "trigger": case.trigger, "review_scope": case.review_scope, "docs": docs,
                "context": case.read_json(case.out("context.json")),
                "context_status": cj.status if cj else None, "context_error": cj.error if cj else None,
                "corrections": case.corrections, "reports": reports, "approved": case.approved, "extras": extras,
                "data": data,
                "jobs": [{**asdict(j), "label": self.label(j)} for j in case.jobs[-40:]],
                "trace": case.trace[-60:], "live": case.live, "tokens": case.tokens}

    def get(self, case_id: str) -> Case:
        case = self.cases.get(case_id)
        if case is None:
            raise KeyError(case_id)
        return case
