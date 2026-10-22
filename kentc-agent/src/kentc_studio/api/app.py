"""FastAPI routes of the Agentic Studio: one async loop, several apps (config/studio.yaml -> apps/<name>/app.yaml).

Page 1: pick an app, fill its fields, stage files in its lanes, tick data pulls -> the insight agents read the
files and the pulls run, asynchronously, while the case table updates. Page 2: verify the insights, flag wrong
values (re-run asynchronously), add files. Page 3: the report agent writes the report in the report framework;
every prompt becomes a new version the analyst finds back in the case table; approve and export.
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

from ..providers import AgentError
from ..report import to_html
from ..service.cases import Case, CaseService

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "web"


class Feedback(BaseModel):
    target: str                 # a document name, or "lane:<lane>"
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


async def read_uploads(files: list[UploadFile], lanes: list[str]) -> list[tuple[str, str, bytes]]:
    if len(lanes) != len(files):
        raise HTTPException(400, "give one lane per file")
    return [(f.filename or "", lanes[i], await f.read()) for i, f in enumerate(files)]


def create_app(studio: CaseService, token: str = "") -> FastAPI:
    app = FastAPI(title="Agentic Studio", docs_url="/api/docs")
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

    @app.middleware("http")
    async def revalidate_front_end(request: Request, call_next):
        """The page and its assets change with the studio: make the browser revalidate them (ETag → 304) instead
        of running a heuristically cached app.js against a newer page or API."""
        response = await call_next(request)
        if not request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-cache"
        return response

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
        return {"model": model, "workspace": str(studio.ws)}

    @app.get("/api/apps")
    def apps() -> list[dict[str, Any]]:
        return [a.describe(studio.config.pulls) for a in studio.config.apps.values()]

    @app.get("/api/cases")
    def list_cases() -> list[dict[str, Any]]:
        return [studio.view(c) for c in sorted(studio.cases.values(), key=lambda c: c.created, reverse=True)]

    @app.post("/api/cases", status_code=201)
    async def create_case(app_name: str = Form(..., alias="app"), case_id: str = Form(...),
                          fields: str = Form("{}"), use_sample: bool = Form(False),
                          files: list[UploadFile] = File(default=[]), lanes: list[str] = Form(default=[]),
                          pulls: list[str] = Form(default=[]), pulls_selected: bool = Form(False)) -> dict[str, Any]:
        """`fields`: a JSON object of the app's fields. `pulls` + `pulls_selected=true`: run exactly these data
        pulls (none if empty); without `pulls_selected`, the pulls pre-ticked for the fields run."""
        try:
            values = json.loads(fields)
        except ValueError:
            raise HTTPException(400, "fields must be a JSON object") from None
        if not isinstance(values, dict):
            raise HTTPException(400, "fields must be a JSON object")
        uploads = await read_uploads(files, lanes)
        case = guard(studio.create_case, app_name, case_id, values, uploads, use_sample,
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
                            lanes: list[str] = Form(default=[])) -> dict[str, Any]:
        case = case_of(case_id)
        names = guard(studio.add_documents, case, await read_uploads(files, lanes))
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
        data = case.read_json(case.out("reports", f"v{version}.json"))
        if data is None:
            raise HTTPException(404, f"no report v{version}")
        text = studio.report_markdown(case, version)
        return {"version": version, "markdown": text, "html": to_html(text), "data": data}

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
    app = studio.app(case)
    name = app.report.name
    version = (case.approved or {}).get("version") or (case.reports[-1]["version"] if case.reports else None)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("case-detail.json", json.dumps(
            {"version": 3, **case.meta(), "appTitle": app.title, "approved": case.approved,
             "lanes": {ln["name"]: (ln["insight"] or {}).get("result") for ln in detail["lanes"]},
             "documents": [{"name": d["name"], "lane": d["lane"], "status": d["status"],
                            "insight": (d["insight"] or {}).get("result")} for d in detail["docs"]],
             "corrections": case.corrections,
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
        w.writerow(["File", "Lane", "Agent", "Status", "Analyst corrections"])
        for d in detail["docs"]:
            w.writerow([d["name"], d["lane"], d["agent"], d["status"], len(d["corrections"])])
        z.writestr("evidence-manifest.csv", out.getvalue())
        for r in case.reports:
            text = studio.report_markdown(case, r["version"])
            if text is not None:
                z.writestr(f"reports/v{r['version']}.md", text)
        if version:
            text = studio.report_markdown(case, version) or ""
            z.writestr("report.html", f"<!doctype html><meta charset='utf-8'><title>{case.id} {name} v{version}</title>"
                                      f"<body style='font-family:sans-serif;max-width:860px;margin:auto'>"
                                      f"{to_html(text)}")
        z.writestr("README.txt", f"{app.title} case {case.id} exported {time.strftime('%Y-%m-%d %H:%M')}.\n"
                                 f"report.html: {name} v{version}{' (approved)' if case.approved else ''}; "
                                 "reports/: every version.\n"
                                 "case-detail.json: case fields, insight agent results per lane and file, data pulls, "
                                 "corrections, extra agents and report versions (with each version's prompt).\n"
                                 "data/: the rows of each data pull (CSV).\n"
                                 "decision-trace.csv: HUM analyst / AGT agent / SYS events.\n"
                                 "evidence-manifest.csv: documents with lanes, agents and statuses.\n")
    return buf.getvalue()
