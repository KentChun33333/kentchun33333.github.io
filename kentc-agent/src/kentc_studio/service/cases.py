"""Cases and their asynchronous agent jobs.

A case belongs to one app (apps.py). Its folder <workspace>/cases/<case id>/ holds:
    case.json                   app, fields, documents (name + lane), jobs, corrections, report versions, trace
    docs/                       uploaded documents
    outputs/files/<f>.json      latest result of a per-file insight agent ({result, job, updated, feedback})
    outputs/lanes/<lane>.json   latest result of a per-lane insight agent (same wrapper)
    outputs/data/<p>.json       latest data pull (parameters, SQL, row count, key values, preview)
    data/<p>.csv                the pulled rows
    outputs/extra/<a>.json      extra agent results (same wrapper)
    outputs/reports/v<n>.json / .md   report versions
    jobs/<job id>/              each job's materials, workflow state and agent session
    events.jsonl                the activity feed

Page 3 prompts are report jobs: each analyst prompt is a report job carrying the prompt as its instruction; the
version it produces answers in `reply`, and the version records the prompt. Every request is asynchronous.

The dispatcher runs local-model jobs one at a time, and data pulls and external-agent jobs in parallel.
"""

from __future__ import annotations

import json
import shutil
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from kentc_agent.adapters.documents import load_source, read_document
from kentc_agent.adapters.llm import LLMClient
from kentc_agent.adapters.tools import ToolContext, ToolError, reject_unsupported
from kentc_agent.agent import Events
from kentc_agent.config import load_settings

from ..apps import Agent, App, block_kind
from ..config import StudioConfig, load_config
from ..jobs.queue import JobDispatcher
from ..models import CASE_ID_RE, LANE_MAX_CHARS, SETTLED, Case, Job
from ..providers import Provider
from ..report import get, text, to_markdown
from ..store import CaseStore

BUSY = ("queued", "running")


def lane_target(lane: str) -> str:
    return f"lane:{lane}"


class CaseService:
    def __init__(self, workspace: Path, config_path: Path, effort: str | None = None) -> None:
        self.ws = workspace
        self.root = workspace / "cases"
        self.root.mkdir(parents=True, exist_ok=True)
        self.config: StudioConfig = load_config(config_path)
        self.settings = load_settings(workspace, {"reasoning_effort": effort})
        self.llm = LLMClient(self.settings)
        self.store = CaseStore(self.root)
        self.cases: dict[str, Case] = self.store.load_all(Case, self.config.apps)
        self.dispatcher = JobDispatcher(self)
        self.dispatcher.start()

    def app(self, case: Case) -> App:
        return self.config.apps[case.app]

    def provider(self, case: Case, job: Job) -> Provider:
        app = self.app(case)
        if job.role == "insight":
            return app.agents[job.agent].provider
        if job.role == "extra":
            return app.extras[job.agent]
        if job.role == "query":
            return self.config.pulls[job.agent]
        return app.report.provider

    def label(self, case: Case, job: Job) -> str:
        try:
            p = self.provider(case, job)
        except KeyError:                          # removed from the app since the job ran
            return job.agent
        if job.role == "insight" and not job.target.startswith("lane:"):
            return f"{p.label} · {job.target}"
        return f"Data · {p.label}" if job.role == "query" else p.label

    # -------------------------------------------------------------- results on disk
    def _out(self, case: Case, target: str) -> Path:
        """Where the latest insight result of a target (a file, or lane:<lane>) is kept."""
        if target.startswith("lane:"):
            return case.out("lanes", f"{target[5:]}.json")
        return case.out("files", f"{target}.json")

    def _result(self, case: Case, target: str) -> dict[str, Any] | None:
        return (case.read_json(self._out(case, target)) or {}).get("result")

    @staticmethod
    def facts(agent: Agent, result: dict[str, Any] | None) -> list[dict[str, Any]]:
        """The flaggable rows (`facts` blocks) of an insight agent's result."""
        rows = []
        for block in agent.view:
            if block_kind(block) == "facts":
                rows += [r for r in get(result or {}, block["facts"]) or [] if isinstance(r, dict)]
        return rows

    # -------------------------------------------------------------- creating work
    def _job(self, case: Case, role: str, agent: str, target: str = "", params: dict[str, Any] | None = None,
             after: list[str] | None = None) -> Job:
        job = Job(id=f"{time.strftime('%H%M%S')}-{role}-{uuid.uuid4().hex[:5]}", role=role, agent=agent,
                  target=target, params=params or {}, after=after or [])
        case.jobs.append(job)
        case.event("queued", self.label(case, job), "queued", job.id)
        return job

    def _pending(self, case: Case, roles: tuple[str, ...]) -> list[str]:
        return [j.id for j in case.jobs if j.role in roles and j.status in BUSY]

    def _targets(self, case: Case, names: list[str]) -> list[str]:
        """The insight jobs covering these files: per-lane jobs first (one call, shown first), then per-file."""
        app = self.app(case)
        lanes, files = [], []
        for n in names:
            lane = case.lane_of(n)
            agent = app.agent_of(lane) if lane else None
            if agent is None:
                continue
            if agent.per == "lane":
                if lane_target(lane) not in lanes:
                    lanes.append(lane_target(lane))
            else:
                files.append(n)
        return lanes + files

    def _insight(self, case: Case, targets: list[str], feedback: dict[str, str] | None = None) -> None:
        """Insight-agent jobs. A still-queued job of the same target is replaced by this one (its feedback kept),
        since the new job covers the same files."""
        feedback = feedback or {}
        if not targets:
            return
        app = self.app(case)
        with case.lock:
            for t in targets:
                lane = t[5:] if t.startswith("lane:") else case.lane_of(t)
                notes = []
                for j in case.jobs:
                    if j.role == "insight" and j.target == t and j.status == "queued":
                        j.status, j.error = "stopped", "superseded by a newer request"
                        notes.append(j.params.get("feedback", ""))
                notes.append(feedback.get(t, ""))
                self._job(case, "insight", app.lane(lane).agent, t, {"feedback": "\n".join(n for n in notes if n)})
            case.save()
        self._wake()

    def default_pulls(self, app: App, fields: dict[str, str]) -> list[str]:
        words = " ".join(fields.values())
        return [n for n in app.pulls if self.config.pulls[n].selected_for(words)]

    def pull(self, case: Case, names: list[str], params: dict[str, str] | None = None, who: str = "HUM") -> list[Job]:
        """Data-pull jobs. They do not use the model, so they start at once, in parallel with the agents. A queued
        or running pull of the same template is superseded. `params` override case fields for this pull only."""
        app = self.app(case)
        unknown = [n for n in names if n not in app.pulls]
        if unknown:
            raise ValueError(f"unknown data pull(s) for {app.title}: {', '.join(unknown)}")
        params = {k: str(v).strip() for k, v in (params or {}).items() if str(v).strip()}
        for n in names:
            allowed = [b for b in self.config.pulls[n].binds if b != "case_id"]
            bad = sorted(set(params) - set(allowed))
            if bad:
                raise ValueError(f"{n}: unknown parameter(s) {', '.join(bad)}; use {', '.join(allowed) or 'none'}")
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
        """Store (name, lane, data) uploads; a re-uploaded name replaces the earlier file. -> names."""
        app = self.app(case)
        folder = case.dir / "docs"
        folder.mkdir(parents=True, exist_ok=True)
        names = []
        for name, lane, data in files:
            name = Path(name).name
            if not name or name.startswith("."):
                continue
            if app.lane(lane) is None:
                raise ValueError(f"{name}: lane must be one of {', '.join(ln.name for ln in app.lanes)}")
            try:
                reject_unsupported(Path(name))
            except ToolError as e:
                raise ValueError(str(e)) from None
            (folder / name).write_bytes(data)
            case.documents = [d for d in case.documents if d["name"] != name]
            case.documents.append({"name": name, "lane": lane, "size": len(data), "uploaded": time.time()})
            names.append(name)
        return names

    def create_case(self, app_name: str, case_id: str, fields: dict[str, Any], files: list[tuple[str, str, bytes]],
                    use_sample: bool = False, pulls: list[str] | None = None) -> Case:
        """`pulls`: the data pulls to run; None = the ones pre-ticked for these fields."""
        app = self.config.apps.get(app_name)
        if app is None:
            raise ValueError(f"unknown app {app_name!r}; use {', '.join(self.config.apps)}")
        cid = case_id.strip()
        if not CASE_ID_RE.match(cid):
            raise ValueError("case ID: letters, digits, '.', '_' or '-' (max 64)")
        if cid in self.cases:
            raise FileExistsError(f"case {cid} already exists")
        fields = app.clean_fields(fields)
        pulls = self.default_pulls(app, fields) if pulls is None else pulls
        unknown = [n for n in pulls if n not in app.pulls]
        if unknown:
            raise ValueError(f"unknown data pull(s) for {app.title}: {', '.join(unknown)}")
        case = Case(self.root, {"id": cid, "app": app.name, "fields": fields})
        try:
            if use_sample:
                if app.sample is None:
                    raise ValueError(f"{app.title} has no sample bundle")
                files = app.sample_files() + files
            self.save_uploads(case, files)
            missing = [ln.label or ln.name for ln in app.lanes if ln.required and not case.docs(ln.name)]
            if missing:
                raise ValueError(f"stage at least one file in {', '.join(missing)}")
        except ValueError:
            shutil.rmtree(case.dir, ignore_errors=True)
            raise
        counts = ", ".join(f"{len(case.docs(ln.name))} {ln.label or ln.name}" for ln in app.lanes)
        case.audit("HUM", f"{app.title} case submitted with {len(case.documents)} documents ({counts})")
        self.cases[cid] = case
        self.pull(case, pulls, who="SYS")          # no model: these start at once, alongside the agents
        self._insight(case, self._targets(case, case.docs()))
        return case

    def add_documents(self, case: Case, files: list[tuple[str, str, bytes]]) -> list[str]:
        names = self.save_uploads(case, files)
        if not names:
            raise ValueError("no files")
        case.audit("HUM", f"uploaded {', '.join(names)}")
        case.save()
        self._insight(case, self._targets(case, names))
        return names

    def feedback(self, case: Case, target: str, note: str, field_name: str = "", value: str = "") -> None:
        """An analyst correction on a file or a lane (`lane:<name>`): its insight agent runs again with the note."""
        note, value = note.strip(), value.strip()
        if not note and not value:
            raise ValueError("say what is wrong")
        app = self.app(case)
        lane = target[5:] if target.startswith("lane:") else case.lane_of(target)
        if lane is None or app.lane(lane) is None:
            raise ValueError(f"no document or lane {target}")
        agent = app.agent_of(lane)
        if agent is None:
            raise ValueError(f"no agent reads the {app.lane(lane).label or lane} lane")
        if target.startswith("lane:") and agent.per != "lane":
            raise ValueError(f"{lane} is read file by file: send the note on one of its files")
        job_target = lane_target(lane) if agent.per == "lane" else target
        entry = {"time": time.time(), "target": target, "field": field_name, "analyst_value": value, "note": note}
        if field_name:
            entry["agent_value"] = next((r.get("value") for r in self.facts(agent, self._result(case, job_target))
                                         if r.get("field") == field_name), "")
        case.corrections.append(entry)
        what = f"{field_name} in {target}" if field_name else target
        case.audit("HUM", f"feedback on {what}: {note or value}")
        msg = (f"Field '{field_name}': " if field_name else "") + (f"the correct value is {value}. " if value else "") \
            + note
        self._insight(case, [job_target], {job_target: msg if job_target == target else f"{target}: {msg}"})

    def request_report(self, case: Case, extras: list[str], instruction: str = "") -> Job:
        """A report version. With an instruction it is the analyst's prompt: the agent revises the latest version (at
        the time it runs) and answers in `reply`. It waits for running insight / data / extra / report jobs."""
        app = self.app(case)
        unknown = [e for e in extras if e not in app.extras]
        if unknown:
            raise ValueError(f"unknown extra agent(s): {', '.join(unknown)}")
        instruction = instruction.strip()
        with case.lock:
            reports = self._pending(case, ("report",))
            if instruction and not case.reports and not reports:
                raise ValueError(f"generate the first {app.report.name} before sending a prompt")
            before = self._pending(case, ("insight", "query"))
            ex = [self._job(case, "extra", e, e, after=before) for e in extras]
            version = len(case.reports) + 1 + len(reports)
            job = self._job(case, "report", "report", f"v{version}", {"instruction": instruction, "extras": extras},
                            after=before + [j.id for j in ex] + reports)
            case.audit("HUM", (f"prompt for {app.report.name} v{version}: {instruction}" if instruction
                               else f"asked for {app.report.name} v{version}") +
                       (f" with {', '.join(extras)}" if extras else ""))
            case.save()
        self._wake()
        return job

    def approve(self, case: Case, version: int) -> None:
        if not any(r["version"] == version for r in case.reports):
            raise ValueError(f"no report v{version}")
        case.approved = {"version": version, "time": time.time()}
        case.audit("HUM", f"approved {self.app(case).report.name} v{version}")
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
                raise ValueError(f"{self.label(case, job)} already {job.status}")
            case.audit("HUM", f"stopped {self.label(case, job)}")
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
                          after=self._pending(case, ("insight", "query")) if j.role in ("extra", "report") else [])
            case.save()
        self._wake()
        return len(again)

    # -------------------------------------------------------------- dispatching
    def _wake(self) -> None:
        self.dispatcher.wake()

    def materials(self, case: Case) -> dict[str, Any]:
        """Everything the agents know about the case, for the extra and report agents."""
        app = self.app(case)
        docs = []
        for d in case.documents:
            agent = app.agent_of(d["lane"])
            docs.append({"file": f"docs/{d['name']}", "lane": d["lane"],
                         "insight": self._result(case, d["name"]) if agent and agent.per == "file" else None})
        lanes = {ln.name: r for ln in app.lanes
                 if (a := app.agent_of(ln.name)) and a.per == "lane"
                 and (r := self._result(case, lane_target(ln.name))) is not None}
        extras = {p.stem: (case.read_json(p) or {}).get("result") for p in sorted(case.out("extra").glob("*.json"))} \
            if case.out("extra").is_dir() else {}
        pulls = {}
        for p in sorted(case.out("data").glob("*.json")) if case.out("data").is_dir() else []:
            r = case.read_json(p) or {}
            pulls[p.stem] = {k: r.get(k) for k in ("label", "database", "params", "rows", "truncated", "key_values",
                                                   "file")}
        return {"case": {"id": case.id, "app": app.title, **case.fields}, "documents": docs, "lane_insights": lanes,
                "data_pulls": pulls, "extra_agents": extras, "analyst_corrections": case.corrections}

    def _lane_text(self, case: Case, lane: str, events: Events) -> str:
        """A lane's documents as text for its per-lane agent: each one converted (or digested by the parsing
        sub-agent when it is a PDF, an image or large), plus its attachments the same way. Cached digests make a
        re-run cheap."""
        ctx = ToolContext(case.dir, self.settings, self.llm, events)
        parts = []
        for name in case.docs(lane):
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
        out = "\n\n".join(parts)
        if len(out) > LANE_MAX_CHARS:
            out = out[:LANE_MAX_CHARS] + "\n\n[lane documents truncated]"
        return out

    def inputs(self, case: Case, job: Job, job_dir: Path, events: Events) -> dict[str, Any]:
        """The job's workflow inputs (apps.py AGENT_INPUTS / REPORT_INPUTS / EXTRA_INPUTS)."""
        def rel(p: Path) -> str:
            return str(p.relative_to(case.dir))

        if job.role == "query":                  # the SQL parameters: case fields, then this pull's overrides
            return {**case.fields, "case_id": case.id, **(job.params.get("params") or {})}
        brief = self.app(case).brief(case.id, case.fields)
        feedback = job.params.get("feedback", "")
        if job.role == "insight" and job.target.startswith("lane:"):
            (job_dir / "lane.md").write_text(self._lane_text(case, job.target[5:], events), encoding="utf-8")
            return {"lane_file": rel(job_dir / "lane.md"), "case_brief": brief, "feedback": feedback}
        if job.role == "insight":
            prev = self._result(case, job.target)
            return {"file": f"docs/{job.target}", "case_brief": brief, "feedback": feedback,
                    "previous": json.dumps(prev, ensure_ascii=False) if prev and feedback else ""}
        case.write_json(job_dir / "materials.json", self.materials(case))
        if job.role == "extra":
            return {"materials_file": rel(job_dir / "materials.json"), "case_brief": brief}
        inputs = {"materials_file": rel(job_dir / "materials.json"), "case_brief": brief,
                  "instruction": job.params.get("instruction", ""), "previous_report_file": ""}
        if inputs["instruction"] and case.reports:
            inputs["previous_report_file"] = rel(case.out("reports", f"v{case.reports[-1]['version']}.json"))
        return inputs

    def request(self, case: Case, job: Job, job_dir: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        """The body an external (HTTP) agent receives; pulls get none."""
        if job.role == "query":
            return {}
        lane_md = job_dir / "lane.md"
        materials = {"case": case.meta(), "lane_documents": lane_md.read_text(encoding="utf-8")} \
            if job.role == "insight" and job.target.startswith("lane:") else self.materials(case)
        return {"role": job.role, "app": case.app, "case_id": case.id, "job_id": job.id, "inputs": inputs,
                "documents": [{**d, "url": f"{self.config.public_url}/api/cases/{case.id}/docs/{d['name']}"}
                              for d in case.documents],
                "materials": materials}

    def store_result(self, case: Case, job: Job, result: dict[str, Any]) -> None:
        now = time.time()
        if job.role == "insight":
            case.write_json(self._out(case, job.target), {"result": result, "job": job.id, "updated": now,
                                                          "feedback": job.params.get("feedback", "")})
        elif job.role == "query":
            case.write_json(case.out("data", f"{job.target}.json"), {**result, "job": job.id, "updated": now})
        elif job.role == "extra":
            case.write_json(case.out("extra", f"{job.target}.json"), {"result": result, "job": job.id, "updated": now})
        else:
            version = len(case.reports) + 1
            job.target = f"v{version}"
            case.write_json(case.out("reports", f"v{version}.json"), result)
            case.out("reports", f"v{version}.md").write_text(
                to_markdown(self.app(case), case.id, case.fields, result, version), encoding="utf-8")
            case.reports.append({"version": version, "job": job.id, "created": now,
                                 "instruction": job.params.get("instruction", ""),
                                 "extras": job.params.get("extras", [])})
            case.approved = None                 # a new version needs a new approval

    # -------------------------------------------------------------- views
    def _evidence_time(self, case: Case) -> float:
        return max([j.finished or 0 for j in case.jobs
                    if j.role in ("insight", "query", "extra") and j.status == "done"]
                   + [c["time"] for c in case.corrections] + [0])

    def view(self, case: Case) -> dict[str, Any]:
        """The queue row: status text, verdict, progress and where Detail goes."""
        app, jobs = self.app(case), case.jobs
        name = app.report.name
        active = [j for j in jobs if j.status in BUSY]
        running = [j for j in jobs if j.status == "running"]
        latest: dict[tuple[str, str], Job] = {}
        for j in jobs:
            latest[(j.role, j.target)] = j
        failed = [j for j in latest.values() if j.status == "failed"]
        report = case.reports[-1] if case.reports else None
        rdata = case.read_json(case.out("reports", f"v{report['version']}.json")) if report else None
        stale = bool(report and self._evidence_time(case) > report["created"])
        insights = any(self._out(case, j.target).is_file() for j in jobs if j.role == "insight") or \
            any(case.out("data").glob("*.json"))
        stage, page, tone = "", (3 if report else 2), ""    # Page 2 opens at once and fills in as jobs finish
        if active:
            since = min(a.created for a in active)

            def batch(pred) -> tuple[int, int]:
                js = [j for j in jobs if pred(j) and (j.status in BUSY or (j.finished or 0) >= since)]
                return sum(j.status in SETTLED for j in js), len(js)
            qdone, qtotal = batch(lambda j: j.role == "query")
            model = [j for j in running if j.role != "query"]
            r = model[0] if model else None
            if r is None and any(j.role == "query" for j in running):
                label, stage = f"Pulling data ({qdone}/{qtotal})", "Data pull"
            elif r is None:
                label, stage = f"Queued · {len(active)} agent job(s)", "Queued"
            elif r.role == "insight" and r.target.startswith("lane:"):
                label = stage = self.provider(case, r).label
            elif r.role == "insight":
                done, total = batch(lambda j: j.role == "insight" and not j.target.startswith("lane:"))
                stage = self.provider(case, r).label
                label = f"{stage} ({done}/{total} files)"
            elif r.role == "extra":
                label, stage = f"Running {self.provider(case, r).label}", "Extra agent"
            else:
                label = f"Revising {name} → {r.target}" if r.params.get("instruction") else f"Drafting {name}"
                stage = app.report.provider.label
            if stage != "Data pull" and qdone < qtotal:
                label += f" · data {qdone}/{qtotal}"
            rec = "IN PROGRESS"
            if any(j.role in ("report", "extra") for j in active):
                page = 3
        elif failed:
            label, rec, stage = f"{self.label(case, failed[0])} failed", "ERROR", "Failed"
        elif case.approved:
            label, rec, stage = f"Approved · {name} v{case.approved['version']}", "APPROVED", "Approved"
        elif report:
            if stale:
                label, rec = "New evidence · report out of date", "REGENERATE"
            else:
                verdict = text((rdata or {}).get("verdict"))
                label, rec, tone = f"{name} v{report['version']} ready · review", verdict.upper() or "READY", \
                    app.report.tone(verdict)
            stage = "Report"
        elif insights:
            label, rec, stage = "Insights ready · review required", "PENDING REVIEW", "Insights"
        else:
            label, rec = "Staged", "—"
        first = min((j.started for j in jobs if j.started), default=None)
        last = max((j.finished or time.time() for j in jobs if j.started), default=None)
        return {**case.meta(), "app_title": app.title,
                "status": "running" if running else "queued" if active else "failed" if failed else
                "approved" if case.approved else "ready" if (report or insights) else "staged",
                "label": label, "recommendation": rec, "tone": tone, "stage": stage, "page": page, "stale": stale,
                "created": case.created, "updated": case.updated, "documents": len(case.documents),
                "versions": len(case.reports), "elapsed": round(last - first) if first and last else 0}

    def detail(self, case: Case) -> dict[str, Any]:
        app = self.app(case)
        latest: dict[tuple[str, str], Job] = {}
        for j in case.jobs:
            latest[(j.role, j.target)] = j
        docs = []
        for d in case.documents:
            agent = app.agent_of(d["lane"])
            per_file = bool(agent and agent.per == "file")
            j = latest.get(("insight", d["name"] if per_file else lane_target(d["lane"]))) if agent else None
            docs.append({**d, "agent": app.lane(d["lane"]).agent, "per": agent.per if agent else "",
                         "status": j.status if j else "staged" if agent else "stored",
                         "error": j.error if j else None,
                         "insight": case.read_json(self._out(case, d["name"])) if per_file else None,
                         "corrections": [c for c in case.corrections if c["target"] == d["name"]]})
        lanes = []
        for ln in app.lanes:
            agent = app.agent_of(ln.name)
            if not agent or agent.per != "lane":
                continue
            t = lane_target(ln.name)
            j = latest.get(("insight", t))
            files = case.docs(ln.name)
            lanes.append({"name": ln.name, "label": ln.label, "agent": ln.agent, "agent_label": agent.label,
                          "files": files, "status": j.status if j else None, "error": j.error if j else None,
                          "insight": case.read_json(self._out(case, t)),
                          "corrections": [c for c in case.corrections if c["target"] == t or c["target"] in files]})
        data = []
        for name in app.pulls:
            p = self.config.pulls[name]
            j = latest.get(("query", name))
            data.append({"name": name, "label": p.label, "description": p.description, "database": p.database.label,
                         "binds": [b for b in p.binds if b != "case_id"],
                         "status": j.status if j else None, "error": j.error if j else None,
                         "job": j.id if j else None, "started": j.started if j else None,
                         "params": (j.params.get("params") or {}) if j else {},
                         "progress": case.progress.get(j.id, "") if j else "",
                         "result": case.read_json(case.out("data", f"{name}.json"))})
        reports = [{**r, "data": case.read_json(case.out("reports", f"v{r['version']}.json"))} for r in case.reports]
        extras = {}
        for name, p in app.extras.items():
            j = latest.get(("extra", name))
            extras[name] = {"label": p.label, "default": p.default, "remote": not p.local, "describe": p.describe(),
                            "result": (case.read_json(case.out("extra", f"{name}.json")) or {}).get("result"),
                            "status": j.status if j else None}
        return {**self.view(case), "docs": docs, "lanes": lanes, "data": data, "corrections": case.corrections,
                "reports": reports, "approved": case.approved, "extras": extras,
                "jobs": [{**asdict(j), "label": self.label(case, j)} for j in case.jobs[-40:]],
                "trace": case.trace[-60:], "live": case.live, "tokens": case.tokens}

    def get(self, case_id: str) -> Case:
        case = self.cases.get(case_id)
        if case is None:
            raise KeyError(case_id)
        return case
