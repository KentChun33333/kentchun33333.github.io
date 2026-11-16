"""Loopback HTTP server for Kent WebIO."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from kentc_agent.adapters.llm import LLMClient, LLMError
from kentc_agent.config import load_settings
from kentc_agent.workflow import WorkflowError

from .profiles import PROJECT_ROOT, ProfileCatalog
from .runtime import WebIO
from .tasks import Tasks
from .workspace import HTML_SUFFIXES, children, html_outputs, workspace_path

ASSETS = Path(__file__).parent / "static"
MAX_UPLOAD = 128 * 1024 * 1024
PREVIEW_ASSETS = {
    ".css": "text/css", ".js": "text/javascript",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
    ".webp": "image/webp", ".avif": "image/avif", ".svg": "image/svg+xml", ".ico": "image/x-icon",
    ".mp4": "video/mp4", ".webm": "video/webm", ".mp3": "audio/mpeg", ".ogg": "audio/ogg",
}


class Chat(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)
    files: list[str] = Field(default_factory=list, max_length=32)


class Folder(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


class RenamePath(BaseModel):
    source: str = Field(min_length=1, max_length=4096)
    destination: str = Field(min_length=1, max_length=4096)


class ClearChat(BaseModel):
    session_id: str


class NewTask(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    persona: str = ""
    skills: list[str] = Field(default_factory=list, max_length=32)
    workflow: str = ""


class WorkflowRun(BaseModel):
    inputs: dict[str, str] = Field(default_factory=dict)
    step: str | None = None
    answer: str | None = Field(default=None, max_length=20_000)


class TaskStatus(BaseModel):
    closed: bool


def create_app(web: WebIO, *, profile_root: Path = PROJECT_ROOT) -> FastAPI:
    app = FastAPI(title="Kent WebIO", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    tasks = Tasks(web, ProfileCatalog(profile_root))

    @app.middleware("http")
    async def local_requests(request: Request, call_next):
        if request.method in ("POST", "PUT", "DELETE"):
            origin = request.headers.get("origin")
            if origin and origin != f"{request.url.scheme}://{request.headers.get('host')}":
                return Response(status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    def active_task(task: str = Query("", max_length=32)) -> WebIO:
        try:
            return tasks.get(task)
        except FileNotFoundError as error:
            raise HTTPException(404, str(error) if error.filename is None else "Task not found.") from None
        except (OSError, KeyError, ValueError, WorkflowError):
            raise HTTPException(409, "Could not open this task.") from None

    def path_for(web: WebIO, name: str) -> Path:
        try:
            return workspace_path(web.workspace, name)
        except ValueError as error:
            raise HTTPException(400, str(error)) from None

    def claim_workspace(web: WebIO) -> None:
        if not web.lock.acquire(blocking=False):
            raise HTTPException(409, "The workspace is busy. Try again when the current operation finishes.")

    def ensure_open(web: WebIO) -> None:
        if web.task.get("closed"):
            raise HTTPException(409, "Reopen this task before making changes.")

    @app.get("/")
    def index():
        return FileResponse(ASSETS / "index.html")

    @app.get("/api/tasks")
    def list_tasks():
        return {"entries": tasks.list()}

    @app.get("/api/profiles")
    def profiles():
        return tasks.profiles.describe()

    @app.post("/api/tasks", status_code=201)
    def create_task(body: NewTask):
        try:
            return tasks.create(body.title, body.persona, body.skills, body.workflow)
        except ValueError as error:
            raise HTTPException(400, str(error)) from None
        except OSError:
            raise HTTPException(409, "Could not create the task workspace.") from None

    @app.post("/api/tasks/status")
    def task_status(body: TaskStatus, web: WebIO = Depends(active_task)):
        if not web.task["id"]:
            raise HTTPException(400, "Open a named task first.")
        claim_workspace(web)
        try:
            return tasks.set_closed(web, body.closed)
        except OSError:
            raise HTTPException(409, "Could not update the task status.") from None
        finally:
            web.lock.release()

    @app.get("/api/state")
    def state(web: WebIO = Depends(active_task)):
        return web.snapshot()

    @app.get("/api/events")
    async def events(request: Request, web: WebIO = Depends(active_task)):
        async def stream():
            header = request.headers.get("last-event-id", "")
            cursor = int(header) if header.isdecimal() else None
            if cursor is None:
                snapshot = web.snapshot()
                cursor = snapshot["cursor"]
                yield f"id: {cursor}\ndata: {json.dumps({'snapshot': snapshot})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                batch = await asyncio.to_thread(web.events_after, cursor)
                if await request.is_disconnected():
                    break
                if not batch:
                    yield ": keepalive\n\n"
                for cursor, event in batch:
                    yield f"id: {cursor}\ndata: {json.dumps(event)}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"X-Accel-Buffering": "no"})

    @app.get("/api/files")
    def files(path: str = Query("", max_length=4096), web: WebIO = Depends(active_task)):
        folder = path_for(web, path)
        if not folder.is_dir():
            raise HTTPException(404, "Folder not found.")
        try:
            return {"path": path, "entries": children(web.workspace, folder)}
        except OSError as error:
            raise HTTPException(403, "Could not list this folder.") from error

    @app.get("/api/download")
    def download(path: str = Query(..., max_length=4096), web: WebIO = Depends(active_task)):
        file = path_for(web, path)
        if not file.is_file():
            raise HTTPException(404, "File not found.")
        return FileResponse(file, filename=file.name, media_type="application/octet-stream")

    @app.get("/api/outputs")
    def outputs(web: WebIO = Depends(active_task)):
        return {"entries": html_outputs(web.workspace)}

    def preview_file(web: WebIO, path: str, request: Request, prefix: str):
        file = path_for(web, path)
        suffix = file.suffix.lower()
        media_type = "text/html" if suffix in HTML_SUFFIXES else PREVIEW_ASSETS.get(suffix)
        if not media_type or not file.is_file():
            raise HTTPException(404, "Preview file not found or unsupported.")

        # Scope resource loads to preview paths even though the frame has an opaque origin.
        try:
            port = request.url.port
        except ValueError:
            raise HTTPException(400, "Invalid preview host port.") from None
        host = request.url.hostname or "localhost"
        origin = f"{request.url.scheme}://{host}" + (f":{port}" if port else "")
        assets = origin + prefix
        policy = (
            "sandbox allow-scripts; frame-ancestors 'self'; default-src 'none'; base-uri 'none'; form-action 'none'; "
            f"script-src 'unsafe-inline' {assets}; style-src 'unsafe-inline' {assets}; "
            f"img-src data: blob: {assets}; font-src data:; media-src data: blob: {assets}"
        )
        return FileResponse(file, media_type=media_type, headers={
            "Content-Security-Policy": policy,
            "Referrer-Policy": "no-referrer",
        })

    @app.get("/preview/{path:path}")
    def preview(path: str, request: Request):
        return preview_file(web, path, request, "/preview/")

    @app.get("/tasks/{task}/preview/{path:path}")
    def task_preview(task: str, path: str, request: Request):
        if not task:
            raise HTTPException(404, "Task not found.")
        return preview_file(active_task(task), path, request, f"/tasks/{task}/preview/")

    @app.post("/api/folders", status_code=201)
    def add_folder(body: Folder, web: WebIO = Depends(active_task)):
        ensure_open(web)
        claim_workspace(web)
        try:
            path_for(web, body.path).mkdir()
        except FileExistsError:
            raise HTTPException(409, "A file or folder already has that name.") from None
        except OSError:
            raise HTTPException(400, "Could not create the folder.") from None
        finally:
            web.lock.release()
        return {"path": body.path}

    @app.put("/api/files", status_code=201)
    async def upload(request: Request, path: str = Query(..., min_length=1, max_length=4096),
                     web: WebIO = Depends(active_task)):
        ensure_open(web)
        destination = path_for(web, path)
        if not destination.parent.is_dir():
            raise HTTPException(404, "Choose an existing upload folder.")
        length = request.headers.get("content-length", "")
        if length.isdecimal() and int(length) > MAX_UPLOAD:
            raise HTTPException(413, "Upload exceeds the 128 MiB limit.")
        claim_workspace(web)
        temporary = None
        try:
            if destination.exists():
                raise HTTPException(409, "A file or folder already has that name.")
            size = 0
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".upload-", delete=False) as stream:
                temporary = Path(stream.name)
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > MAX_UPLOAD:
                        raise HTTPException(413, "Upload exceeds the 128 MiB limit.")
                    stream.write(chunk)
            os.link(temporary, destination)
        except FileExistsError:
            raise HTTPException(409, "A file or folder already has that name.") from None
        except OSError:
            raise HTTPException(400, "Could not save the uploaded file.") from None
        finally:
            try:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            finally:
                web.lock.release()
        return {"path": path, "bytes": size}

    @app.delete("/api/files")
    def delete_file(path: str = Query(..., min_length=1, max_length=4096), recursive: bool = Query(False),
                    web: WebIO = Depends(active_task)):
        ensure_open(web)
        target = path_for(web, path)
        if target == web.workspace:
            raise HTTPException(400, "Cannot delete the workspace root.")
        claim_workspace(web)
        try:
            if not target.exists():
                raise HTTPException(404, "File or folder not found.")
            if target.is_dir():
                if recursive:
                    for folder_path, dirs, names in os.walk(target):
                        base = Path(folder_path)
                        if any((base / entry).is_symlink() for entry in [*dirs, *names]):
                            raise HTTPException(400, "Symbolic links are excluded from the workspace browser.")
                    shutil.rmtree(target)
                else:
                    target.rmdir()
            else:
                target.unlink()
        except HTTPException:
            raise
        except OSError:
            raise HTTPException(409, "Could not delete this item. Ensure the folder is empty.") from None
        finally:
            web.lock.release()
        return {"deleted": path}

    @app.post("/api/files/rename")
    def rename_file(body: RenamePath, web: WebIO = Depends(active_task)):
        ensure_open(web)
        src = path_for(web, body.source)
        dst = path_for(web, body.destination)
        if src == web.workspace or dst == web.workspace:
            raise HTTPException(400, "Cannot rename the workspace root.")
        if dst.is_relative_to(src):
            raise HTTPException(400, "Cannot move a folder into itself.")
        claim_workspace(web)
        try:
            if not src.exists():
                raise HTTPException(404, "Source file or folder not found.")
            if not dst.parent.is_dir():
                raise HTTPException(404, "Destination folder not found.")
            if dst.exists():
                raise HTTPException(409, "A file or folder already has that name.")
            src.rename(dst)
        except HTTPException:
            raise
        except OSError:
            raise HTTPException(400, "Could not rename this item.") from None
        finally:
            web.lock.release()
        return {"source": body.source, "destination": body.destination}

    @app.post("/api/chat", status_code=202)
    def chat(body: Chat, web: WebIO = Depends(active_task)):
        ensure_open(web)
        text = body.text.strip()
        if not text:
            raise HTTPException(400, "Enter a message first.")
        paths = list(dict.fromkeys(body.files))
        for path in paths:
            if len(path) > 4096 or not path_for(web, path).is_file():
                raise HTTPException(404, "An attached file is no longer available.")
        if not web.start(lambda: web.chat(text, paths), "Preparing your message"):
            raise HTTPException(409, "A workspace operation is already running.")
        return {"accepted": True}

    @app.post("/api/compact", status_code=202)
    def compact(web: WebIO = Depends(active_task)):
        ensure_open(web)
        if not web.start(web.compact, "Preparing context compression", kind="compression"):
            raise HTTPException(409, "A workspace operation is already running.")
        return {"accepted": True}

    @app.post("/api/chat/clear")
    def clear_chat(body: ClearChat, web: WebIO = Depends(active_task)):
        ensure_open(web)
        claim_workspace(web)
        try:
            if body.session_id != web.agent.session.id:
                raise HTTPException(409, "The active chat has already changed.")
            web.clear_chat()
        except (OSError, ValueError):
            raise HTTPException(500, "Could not create a new chat in this workspace.") from None
        finally:
            web.lock.release()
        return {"cleared": True}

    @app.post("/api/workflow", status_code=202)
    def run_workflow(body: WorkflowRun, web: WebIO = Depends(active_task)):
        ensure_open(web)
        try:
            started = web.start_workflow(body.inputs, body.step, body.answer)
        except (ValueError, WorkflowError) as error:
            raise HTTPException(400, str(error)) from None
        if not started:
            raise HTTPException(409, "A workspace operation is already running.")
        return {"accepted": True}

    @app.post("/api/cancel")
    def cancel_operation(web: WebIO = Depends(active_task)):
        if not web.cancel():
            raise HTTPException(409, "No operation is currently running.")
        return {"cancelling": True}

    app.mount("/assets", StaticFiles(directory=ASSETS), name="assets")
    return app


def main() -> None:
    parser = argparse.ArgumentParser(prog="kent-webio", description="Local workspace chat for KentC Agent")
    parser.add_argument("-w", "--workspace", default="webio-workspace")
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--provider", choices=["openai", "qwen38", "openrouter"])
    parser.add_argument("--model")
    parser.add_argument("--base-url")
    parser.add_argument("--profile-root", type=Path, default=PROJECT_ROOT,
                        help="Trusted local folder containing personas/, skills/, and workflows/.")
    args = parser.parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    try:
        workspace.mkdir(parents=True, exist_ok=True)
        settings = load_settings(workspace, {key: getattr(args, key) for key in ("provider", "model", "base_url")})
        web = WebIO(workspace, settings, LLMClient(settings))
    except (OSError, ValueError, LLMError) as error:
        sys.exit(str(error))
    print(f"Kent WebIO · {workspace} · http://127.0.0.1:{args.port}", flush=True)
    uvicorn.run(create_app(web, profile_root=args.profile_root.expanduser().resolve()), host="127.0.0.1",
                port=args.port, log_level="warning",
                timeout_graceful_shutdown=3)


if __name__ == "__main__":
    main()
