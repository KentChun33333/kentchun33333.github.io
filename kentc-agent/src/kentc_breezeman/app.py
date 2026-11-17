"""HTTP + WebSocket API of kentc-breezeman.

REST: /api/health, /api/tree, /api/file, /api/upload, /api/skills, /api/chats, /api/chats/{key}/transcript|context,
PUT /api/chats/{key}/skill {"name": <skill> | null} (one skill per chat)
WebSocket /ws/{key}: client → {"type": "chat", "text", "attachments"} | {"type": "stop"} | {"type": "compact", "focus"};
server → "hello" (snapshot) then the chat's live events (runtime.py).
"""

from __future__ import annotations

import asyncio
import json
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from kentc_agent.adapters.llm import LLMError
from kentc_agent.skills import SkillError

from . import workspace as wsfiles
from .runtime import Chat, ChatBusy, Runtime, list_skills

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web" / "breezeman"


def create_app(runtime: Runtime, token: str = "") -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        runtime.loop = asyncio.get_running_loop()
        try:
            yield
        finally:
            runtime.close()

    app = FastAPI(title="kentc-breezeman", docs_url="/api/docs", lifespan=lifespan)
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")
    ws_root = runtime.workspace

    def authorized(supplied: str) -> bool:
        return not token or secrets.compare_digest(supplied, token)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.url.path.startswith("/api"):
            supplied = request.headers.get("x-api-token") or ""
            header = request.headers.get("authorization", "")
            if header.lower().startswith("bearer "):
                supplied = supplied or header[7:].strip()
            if not authorized(supplied):
                return JSONResponse({"detail": "unauthorized"}, status_code=401)
        response = await call_next(request)
        if not request.url.path.startswith("/api"):
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

    @app.get("/api/tree")
    def tree(path: str = "") -> list[dict[str, Any]]:
        return bad_request(wsfiles.list_dir, ws_root, path)

    @app.get("/api/file")
    def file(path: str) -> dict[str, Any]:
        return bad_request(wsfiles.preview, ws_root, path)

    @app.post("/api/upload")
    async def upload(folder: str = Form(""), files: list[UploadFile] = File(...)) -> dict[str, Any]:
        saved = []
        for f in files:
            data = await f.read(wsfiles.MAX_UPLOAD_BYTES + 1)
            saved.append(await run_in_threadpool(bad_request, wsfiles.save_upload, ws_root, folder,
                                                  f.filename or "", data))
        return {"saved": saved}

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
