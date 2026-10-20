"""FastAPI routes of the TER Agentic Studio.

Flow: stage documents (context: required, doc evidence: optional) -> the doc agent extracts each document and
the context agent summarises, asynchronously, while the case table updates -> Page 2 review: upload more,
flag wrong values (re-extracted asynchronously) -> Page 3: the report agent (plus any extra agents) writes the
TER report; request more documents from the client, refine the report into new versions, approve and export.
"""

from __future__ import annotations

import csv
import io
import json
import secrets
import time
import zipfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..config import AgentError
from ..report import to_html
from ..service.cases import CaseService, Case

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "web"
SAMPLE = ROOT / "examples" / "ter-case"


class Feedback(BaseModel):
    target: str                 # a document name, or "context"
    note: str = ""
    field: str = ""
    value: str = ""


class ReportRequest(BaseModel):
    extras: list[str] = []
    instruction: str = ""


class Approval(BaseModel):
    version: int


class PullRequest(BaseModel):
    pull: str
    params: dict[str, str] = {}     # case-field overrides for this pull, e.g. {"lookback_date": "2026-03-01"}


async def read_uploads(files: list[UploadFile], roles: list[str]) -> list[tuple[str, str, bytes]]:
    if len(roles) not in (0, len(files)):
        raise HTTPException(400, "give one role per file")
    return [(f.filename or "", roles[i] if roles else "doc", await f.read()) for i, f in enumerate(files)]


def create_app(studio: CaseService, token: str = "") -> FastAPI:
    app = FastAPI(title="TER Agentic Studio", docs_url="/api/docs")
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")

    @app.middleware("http")
    async def require_token(request: Request, call_next):
        """Protect /api when a token is configured (mandatory for a non-loopback bind)."""
        if token and request.url.path.startswith("/api"):
            supplied = request.headers.get("x-api-token") or ""
            header = request.headers.get("authorization", "")
            if header.lower().startswith("bearer "):
                supplied = supplied or header[7:].strip()
            if not secrets.compare_digest(supplied, token):
                return JSONResponse({"detail": "unauthorized"}, status_code=401)
        return await call_next(request)

    def case_of(case_id: str) -> Case:
        try:
            return studio.get(case_id)
        except KeyError:
            raise HTTPException(404, f"no case {case_id}") from None

    def guard(fn, *args, **kw):
        try:
            return fn(*args, **kw)
        except (ValueError, AgentError) as e:
            raise HTTPException(400, str(e)) from None
        except FileExistsError as e:
            raise HTTPException(409, str(e)) from None

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse((WEB / "index.html").read_text(encoding="utf-8"))

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        try:
            info = studio.llm.info(refresh=True)
            model = {"online": True, "id": info.id, "context": info.context_window}
        except Exception as e:  # noqa: BLE001 - reported to the UI as offline
            studio.llm._info = None
            model = {"online": False, "error": str(e)}
        jobs = [(c.id, j) for c in studio.cases.values() for j in c.jobs]
        running = [{"case": cid, "label": studio.label(j)} for cid, j in jobs if j.status == "running"]
        return {"model": model, "workspace": str(studio.ws), "running": running,
                "queued": sum(j.status == "queued" for _, j in jobs), "sample": SAMPLE.is_dir(),
                "agents": {k: {"label": p.label, "describe": p.describe(), "remote": not p.local}
                           for k, p in {**studio.config.agents, **studio.config.extras}.items()},
                "data_pulls": [{"name": k, "label": p.label, "description": p.description, "database": p.database.label,
                                "default": p.default, "triggers": p.triggers}
                               for k, p in studio.config.pulls.items()]}

    @app.get("/api/cases")
    def list_cases() -> list[dict[str, Any]]:
        return [studio.view(c) for c in sorted(studio.cases.values(), key=lambda c: c.created, reverse=True)]

    @app.post("/api/cases", status_code=201)
    async def create_case(case_id: str = Form(...), cif: str = Form(...), customer: str = Form(""),
                          start_date: str = Form(...), lookback_date: str = Form(...), trigger: str = Form(...),
                          related_entity: str = Form(""), review_scope: str = Form(""),
                          use_sample: bool = Form(False), files: list[UploadFile] = File(default=[]),
                          roles: list[str] = Form(default=[]), pulls: list[str] = Form(default=[]),
                          pulls_selected: bool = Form(False)) -> dict[str, Any]:
        """`pulls` + `pulls_selected=true`: run exactly these data pulls (none if empty); without
        `pulls_selected`, the pulls pre-ticked for the trigger run."""
        uploads = await read_uploads(files, roles)
        meta = {"id": case_id, "cif": cif, "customer": customer, "start_date": start_date,
                "lookback_date": lookback_date, "trigger": trigger, "related_entity": related_entity,
                "review_scope": review_scope}
        case = guard(studio.create_case, {k: v.strip() for k, v in meta.items()}, uploads,
                     SAMPLE if use_sample and SAMPLE.is_dir() else None,
                     [p for p in pulls if p] if pulls_selected else None)
        return studio.view(case)

    @app.get("/api/cases/{case_id}")
    def detail(case_id: str) -> dict[str, Any]:
        return studio.detail(case_of(case_id))

    @app.get("/api/cases/{case_id}/events")
    def events(case_id: str, after: int = 0) -> dict[str, Any]:
        case = case_of(case_id)
        return {"events": [e for e in case.events if e["seq"] > after], "live": case.live, "tokens": case.tokens,
                "view": studio.view(case)}

    @app.post("/api/cases/{case_id}/documents")
    async def add_documents(case_id: str, files: list[UploadFile] = File(...),
                            roles: list[str] = Form(default=[])) -> dict[str, Any]:
        case = case_of(case_id)
        names = guard(studio.add_documents, case, await read_uploads(files, roles))
        return {"added": names, "view": studio.view(case)}

    @app.post("/api/cases/{case_id}/feedback")
    def feedback(case_id: str, body: Feedback) -> dict[str, Any]:
        case = case_of(case_id)
        guard(studio.feedback, case, body.target, body.note, body.field, body.value)
        return studio.view(case)

    @app.post("/api/cases/{case_id}/report")
    def report(case_id: str, body: ReportRequest) -> dict[str, Any]:
        case = case_of(case_id)
        job = guard(studio.request_report, case, body.extras, body.instruction)
        return {"job": job.id, "view": studio.view(case)}

    @app.post("/api/cases/{case_id}/data")
    def run_pull(case_id: str, body: PullRequest) -> dict[str, Any]:
        case = case_of(case_id)
        jobs = guard(studio.pull, case, [body.pull], body.params)
        return {"job": jobs[0].id, "view": studio.view(case)}

    @app.get("/api/cases/{case_id}/data/{name}")
    def pull_csv(case_id: str, name: str) -> FileResponse:
        case = case_of(case_id)
        f = case.dir / "data" / f"{name}.csv"
        if name not in studio.config.pulls or not f.is_file():
            raise HTTPException(404, "no such data pull result")
        return FileResponse(f, media_type="text/csv", filename=f"{case.id}-{name}.csv")

    @app.post("/api/cases/{case_id}/jobs/{job_id}/stop")
    def stop_job(case_id: str, job_id: str) -> dict[str, Any]:
        case = case_of(case_id)
        guard(studio.stop_job, case, job_id)
        return studio.view(case)

    @app.get("/api/cases/{case_id}/reports/{version}")
    def report_version(case_id: str, version: int) -> dict[str, Any]:
        case = case_of(case_id)
        md = case.out("reports", f"v{version}.md")
        if not md.is_file():
            raise HTTPException(404, f"no report v{version}")
        text = md.read_text(encoding="utf-8")
        return {"version": version, "markdown": text, "html": to_html(text),
                "data": case.read_json(case.out("reports", f"v{version}.json"))}

    @app.post("/api/cases/{case_id}/approve")
    def approve(case_id: str, body: Approval) -> dict[str, Any]:
        case = case_of(case_id)
        guard(studio.approve, case, body.version)
        return studio.view(case)

    @app.post("/api/cases/{case_id}/stop")
    def stop(case_id: str) -> dict[str, Any]:
        case = case_of(case_id)
        studio.stop(case)
        return studio.view(case)

    @app.post("/api/cases/{case_id}/retry")
    def retry(case_id: str) -> dict[str, Any]:
        case = case_of(case_id)
        if not studio.retry(case):
            raise HTTPException(409, "nothing failed or stopped to retry")
        return studio.view(case)

    @app.get("/api/cases/{case_id}/docs/{name}")
    def document(case_id: str, name: str) -> FileResponse:
        case = case_of(case_id)
        folder = (case.dir / "docs").resolve()
        f = (folder / name).resolve()
        if f.parent != folder or not f.is_file():
            raise HTTPException(404, "no such document")
        return FileResponse(f)

    @app.get("/api/cases/{case_id}/export.zip")
    def export(case_id: str) -> Response:
        case = case_of(case_id)
        return Response(export_zip(studio, case), media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{case.id}-case-detail.zip"'})

    return app


def export_zip(studio: CaseService, case: Case) -> bytes:
    detail = studio.detail(case)
    version = (case.approved or {}).get("version") or (case.reports[-1]["version"] if case.reports else None)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("case-detail.json", json.dumps(
            {"version": 2, "caseType": "TER", **case.meta(), "approved": case.approved,
             "context": detail["context"], "corrections": case.corrections,
             "documents": [{k: d[k] for k in ("name", "role", "status", "extraction")} for d in detail["docs"]],
             "dataPulls": {p["name"]: p["result"] for p in detail["data"] if p["result"]},
             "extraAgents": {k: v["result"] for k, v in detail["extras"].items() if v["result"]},
             "reports": case.reports}, indent=2, ensure_ascii=False))
        for f in sorted((case.dir / "data").glob("*.csv")):
            z.write(f, f"data/{f.name}")
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["Time", "Actor", "Event"])
        w.writerows([t["time"], t["actor"], t["event"]] for t in case.trace)
        z.writestr("decision-trace.csv", out.getvalue())
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["File", "Role", "Status", "Document type", "Key values", "Anomalies", "Analyst corrections"])
        for d in detail["docs"]:
            e = d["extraction"] or {}
            w.writerow([d["name"], d["role"], d["status"], e.get("document_type", ""), len(e.get("key_values") or []),
                        len(e.get("anomalies") or []), len(d["corrections"])])
        z.writestr("evidence-manifest.csv", out.getvalue())
        for r in case.reports:
            md = case.out("reports", f"v{r['version']}.md")
            if md.is_file():
                z.write(md, f"reports/TER-v{r['version']}.md")
        if version:
            text = case.out("reports", f"v{version}.md").read_text(encoding="utf-8")
            z.writestr("report.html", f"<!doctype html><meta charset='utf-8'><title>{case.id} TER v{version}</title>"
                                      f"<body style='font-family:sans-serif;max-width:860px;margin:auto'>"
                                      f"{to_html(text)}")
        z.writestr("README.txt", f"Case {case.id} ({case.cif}) exported {time.strftime('%Y-%m-%d %H:%M')}.\n"
                                 f"report.html: TER v{version}{' (approved)' if case.approved else ''}; "
                                 "reports/: every version.\n"
                                 "case-detail.json: case, context summary, extractions, data pulls, corrections, "
                                 "extra agents.\n"
                                 "data/: the rows of each data pull (CSV).\n"
                                 "decision-trace.csv: HUM analyst / AGT agent / SYS events.\n"
                                 "evidence-manifest.csv: documents with roles and extraction counts.\n")
    return buf.getvalue()
