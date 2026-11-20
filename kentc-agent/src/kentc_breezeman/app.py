"""HTTP + WebSocket API of kentc-breezeman.

REST: /api/health, /api/tree, /api/file, /api/upload, /api/skills, /api/chats, /api/chats/{key}/transcript|context,
PUT /api/chats/{key}/skill {"name": <skill> | null} (one skill per chat)
WebSocket /ws/{key}: client → {"type": "chat", "text", "attachments"} | {"type": "stop"} | {"type": "compact", "focus"};
server → "hello" (snapshot) then the chat's live events (runtime.py).
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from kentc_agent.adapters.llm import LLMError
from kentc_agent.skills import SkillError

from . import workspace as wsfiles
from .runtime import Chat, ChatBusy, Runtime, list_skills
from .studio import StudioRegistry

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web" / "breezeman"
logger = logging.getLogger(__name__)


def create_app(runtime: Runtime, token: str = "") -> FastAPI:
    studios = StudioRegistry(runtime.workspace, runtime.skills, effort=runtime.settings.reasoning_effort)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        runtime.loop = asyncio.get_running_loop()

        async def task_scheduler_loop() -> None:
            while True:
                await asyncio.sleep(5)
                try:
                    await run_in_threadpool(runtime.tick_schedules)
                except Exception:  # noqa: BLE001 - keep scheduler alive across transient errors
                    logger.exception("task scheduler tick failed")

        async def dream_scheduler_loop() -> None:
            while True:
                await asyncio.sleep(5)
                try:
                    await run_in_threadpool(runtime.tick_dream)
                except Exception:  # noqa: BLE001 - keep dreaming loop alive across transient errors
                    logger.exception("dream scheduler tick failed")

        task_sched = asyncio.create_task(task_scheduler_loop())
        dream_sched = asyncio.create_task(dream_scheduler_loop())
        try:
            yield
        finally:
            task_sched.cancel()
            dream_sched.cancel()
            studios.close()
            runtime.close()

    app = FastAPI(title="kentc-breezeman", docs_url="/api/docs", lifespan=lifespan)
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")
    ws_root = runtime.workspace

    def authorized(supplied: str) -> bool:
        return not token or secrets.compare_digest(supplied, token)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        is_studio_api = request.url.path.startswith("/studios/") and "/api/" in request.url.path
        if request.url.path.startswith("/api") or is_studio_api:
            supplied = request.headers.get("x-api-token") or ""
            header = request.headers.get("authorization", "")
            if header.lower().startswith("bearer "):
                supplied = supplied or header[7:].strip()
            if not authorized(supplied):
                return JSONResponse({"detail": "unauthorized"}, status_code=401)
        response = await call_next(request)
        if not request.url.path.startswith("/api") and not is_studio_api:
            response.headers["Cache-Control"] = "no-cache"
        return response

    def bad_request(fn, *args):
        try:
            return fn(*args)
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
        except OSError as e:
            raise HTTPException(500, str(e)) from None

    def chat_of(key: str) -> Chat:
        try:
            return runtime.chat(key)
        except KeyError:
            raise HTTPException(404, f"no chat {key}") from None
        except ValueError as e:                      # a journal that cannot be replayed
            raise HTTPException(409, str(e)) from None

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse((WEB / "index.html").read_text(encoding="utf-8"))

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        try:
            info = runtime.llm.info(refresh=True)
            model = {"online": True, "id": info.id, "context": info.context_window}
        except LLMError as e:
            model = {"online": False, "error": str(e)}
        return {"model": model, "workspace": str(ws_root), "name": ws_root.name}

    def workspace_of(task: str = "") -> Path:
        if not task:
            return ws_root
        try:
            if task.startswith("studio:"):
                return studios.folder_of(task[7:])
            return runtime.task_workspace(task)
        except KeyError:
            raise HTTPException(404, f"no task {task}") from None
        except ValueError as e:
            raise HTTPException(400, str(e)) from None

    @app.get("/api/tree")
    def tree(path: str = "", task: str = "") -> list[dict[str, Any]]:
        return bad_request(wsfiles.list_dir, workspace_of(task), path)

    @app.get("/api/file")
    def file(path: str, task: str = "") -> dict[str, Any]:
        return bad_request(wsfiles.preview, workspace_of(task), path)

    @app.get("/api/file/raw")
    def file_raw(path: str, task: str = "") -> Response:
        resolved = bad_request(wsfiles.inside, workspace_of(task), path)
        if not resolved.is_file():
            raise HTTPException(400, f"not a file: {path}")
        media = "text/html; charset=utf-8" if resolved.suffix.lower() in {".html", ".htm"} else "text/plain; charset=utf-8"
        return Response(
            content=resolved.read_bytes(),
            media_type=media,
            headers={"Content-Security-Policy": "sandbox allow-scripts"},
        )

    @app.post("/api/upload")
    async def upload(folder: str = Form(""), task: str = Form(""), files: list[UploadFile] = File(...)) -> dict[str, Any]:
        root = workspace_of(task)
        saved = []
        for f in files:
            data = await f.read(wsfiles.MAX_UPLOAD_BYTES + 1)
            saved.append(await run_in_threadpool(bad_request, wsfiles.save_upload, root, folder,
                                                  f.filename or "", data))
        return {"saved": saved}

    @app.get("/api/tasks")
    def tasks() -> list[dict[str, Any]]:
        return runtime.list_tasks()

    @app.post("/api/tasks")
    def create_task(body: dict[str, Any]) -> dict[str, Any]:
        name = body.get("name")
        folder = body.get("folder") or ""
        if not isinstance(name, str) or not isinstance(folder, str):
            raise HTTPException(400, "name and folder must be strings")
        return bad_request(runtime.create_task, name, folder)

    @app.patch("/api/tasks/{task_id}")
    def update_task(task_id: str, body: dict[str, Any]) -> dict[str, Any]:
        name = body.get("name")
        status = body.get("status")
        schedule = body["schedule"] if "schedule" in body else ...
        requirements = body["requirements"] if "requirements" in body else ...
        if name is not None and not isinstance(name, str):
            raise HTTPException(400, "name must be a string")
        if status is not None and not isinstance(status, str):
            raise HTTPException(400, "status must be a string")
        try:
            return runtime.update_task(task_id, name=name, status=status, schedule=schedule, requirements=requirements)
        except KeyError:
            raise HTTPException(404, f"no task {task_id}") from None
        except ValueError as e:
            raise HTTPException(400, str(e)) from None

    @app.delete("/api/tasks/{task_id}")
    def delete_task(task_id: str) -> dict[str, bool]:
        try:
            runtime.delete_task(task_id)
        except KeyError:
            raise HTTPException(404, f"no task {task_id}") from None
        return {"ok": True}

    @app.get("/api/dream")
    def dream_status() -> dict[str, Any]:
        return runtime.dream_status()

    @app.get("/api/dream/nodes")
    def dream_nodes(q: str = "", track: str = "", archived: bool = False) -> list[dict[str, Any]]:
        return runtime.dream_nodes(q=q, track=track, include_archived=archived)

    @app.patch("/api/dream")
    def update_dream(body: dict[str, Any]) -> dict[str, Any]:
        enabled = body.get("enabled")
        interval_min = body.get("interval_min")
        if enabled is not None and not isinstance(enabled, bool):
            raise HTTPException(400, "enabled must be a boolean")
        if interval_min is not None:
            if not isinstance(interval_min, (int, float)) or isinstance(interval_min, bool):
                raise HTTPException(400, "interval_min must be a number")
            interval_min = float(interval_min)
        return bad_request(lambda: runtime.update_dream_schedule(enabled=enabled, interval_min=interval_min))

    @app.post("/api/dream/run")
    async def trigger_dream() -> dict[str, Any]:
        try:
            return await run_in_threadpool(runtime.run_dream_now)
        except ChatBusy as e:
            raise HTTPException(409, str(e)) from None

    @app.get("/api/chats")
    def chats() -> list[dict[str, Any]]:
        return runtime.list_chats()

    @app.post("/api/chats")
    def new_chat() -> dict[str, Any]:
        return {"key": runtime.new_chat().key}

    @app.get("/api/chats/{key}/transcript")
    def transcript(key: str) -> list[dict[str, Any]]:
        return chat_of(key).transcript()

    @app.get("/api/chats/{key}/context")
    def context(key: str) -> dict[str, Any]:
        return chat_of(key).context()

    @app.post("/api/chats/{key}/context/clear")
    def clear_context(key: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        scope = str((body or {}).get("scope") or "all").strip().lower()
        chat = chat_of(key)
        try:
            return chat.clear_context(scope)
        except ChatBusy as e:
            raise HTTPException(409, str(e)) from None
        except ValueError as e:
            raise HTTPException(400, str(e)) from None

    @app.get("/api/skills")
    def skills() -> list[dict[str, str]]:
        return list_skills(runtime.skills)

    @app.put("/api/chats/{key}/skill")
    def set_skill(key: str, body: dict[str, Any]) -> dict[str, Any]:
        chat, name = chat_of(key), body.get("name")
        if name is not None and not isinstance(name, str):
            raise HTTPException(400, "name must be a skill name or null")
        try:
            chat.set_skill(name or None)
        except ChatBusy as e:
            raise HTTPException(409, str(e)) from None
        except SkillError as e:
            raise HTTPException(400, str(e)) from None
        return {"skill": chat.skill}

    @app.get("/api/chats/{key}/requirements")
    def get_requirements(key: str) -> dict[str, Any]:
        return {"requirements": list(chat_of(key).session.requirements)}

    @app.post("/api/chats/{key}/requirements")
    def toggle_requirement(key: str, body: dict[str, Any]) -> dict[str, Any]:
        chat = chat_of(key)
        text = body.get("text")
        active = body.get("active", True)
        if not isinstance(text, str) or not isinstance(active, bool):
            raise HTTPException(400, "text must be a string and active must be a boolean")
        try:
            reqs = chat.set_requirement(text, active=active)
        except ChatBusy as e:
            raise HTTPException(409, str(e)) from None
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
        return {"requirements": reqs}

    @app.put("/api/chats/{key}/requirements")
    def put_requirements(key: str, body: dict[str, Any]) -> dict[str, Any]:
        chat = chat_of(key)
        items = body.get("requirements")
        try:
            reqs = chat.sync_requirements(items)
        except ChatBusy as e:
            raise HTTPException(409, str(e)) from None
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
        return {"requirements": reqs}

    @app.get("/api/studios")
    def list_studios() -> list[dict[str, Any]]:
        return studios.list_studios()

    @app.get("/api/studios/templates")
    def studio_templates() -> list[dict[str, str]]:
        return studios.templates()

    @app.post("/api/studios")
    def create_studio(body: dict[str, Any]) -> dict[str, Any]:
        name = body.get("name")
        folder = body.get("folder") or ""
        template = body.get("template") or "ter"
        if not isinstance(name, str) or not isinstance(folder, str) or not isinstance(template, str):
            raise HTTPException(400, "name, folder and template must be strings")
        return bad_request(studios.create_studio, name, folder, template)

    @app.get("/studios/{studio_id}")
    def studio_slash(studio_id: str) -> RedirectResponse:
        return RedirectResponse(url=f"/studios/{studio_id}/", status_code=307)

    @app.api_route("/studios/{studio_id}/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def studio_dispatch(studio_id: str, rest: str, request: Request) -> Response:
        try:
            mounted = await run_in_threadpool(studios.mount, studio_id)
        except KeyError:
            raise HTTPException(404, f"no studio {studio_id}") from None
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
        if rest == "api/cases" and request.method == "GET":
            await run_in_threadpool(studios.sync_cases, mounted)
        sub_scope = dict(request.scope)
        sub_scope["path"] = "/" + rest
        sub_scope["raw_path"] = ("/" + rest).encode("utf-8")
        sub_scope["root_path"] = ""
        sent: list[dict[str, Any]] = []

        async def send(msg: dict[str, Any]) -> None:
            sent.append(msg)

        await mounted.asgi(sub_scope, request.receive, send)
        status = 200
        headers: dict[str, str] = {}
        chunks: list[bytes] = []
        for msg in sent:
            if msg["type"] == "http.response.start":
                status = msg["status"]
                headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in msg.get("headers", [])}
            elif msg["type"] == "http.response.body":
                chunks.append(msg.get("body", b""))
        return Response(content=b"".join(chunks), status_code=status, headers=headers)

    @app.websocket("/ws/{key}")
    async def socket(ws: WebSocket, key: str) -> None:
        if not authorized(ws.query_params.get("token", "")):
            await ws.close(code=4401)
            return
        await ws.accept()
        try:
            chat = await run_in_threadpool(runtime.chat, key)
        except (KeyError, ValueError) as e:
            await ws.send_json({"type": "error", "message": f"cannot open chat {key}: {e}", "fatal": True})
            await ws.close(code=4404)
            return
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        await ws.send_json({"type": "hello", **chat.subscribe(queue)})

        async def forward() -> None:
            while True:
                event = await queue.get()
                await ws.send_text(json.dumps(event, ensure_ascii=False, default=str))

        sender = asyncio.create_task(forward())
        try:
            while True:
                msg = await ws.receive_json()
                kind = msg.get("type") if isinstance(msg, dict) else None
                try:
                    if kind == "chat":
                        attachments = msg.get("attachments") or []
                        if not isinstance(attachments, list) or not all(isinstance(a, str) for a in attachments):
                            raise ValueError("attachments must be workspace paths")
                        await run_in_threadpool(chat.send, str(msg.get("text", "")), attachments)
                    elif kind == "stop":
                        chat.stop()
                    elif kind == "compact":
                        chat.compact(str(msg.get("focus") or "").strip() or None)
                    else:
                        raise ValueError(f"unknown message type {kind!r}")
                except (ChatBusy, ValueError) as e:
                    await ws.send_json({"type": "error", "message": str(e)})
        except (WebSocketDisconnect, json.JSONDecodeError):
            pass
        finally:
            chat.unsubscribe(queue)
            sender.cancel()

    return app
