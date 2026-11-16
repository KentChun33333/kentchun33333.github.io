"""Chats of kentc-breezeman: each chat is one kentc_agent main agent with its own session journal.

A run executes on a worker thread (the agent is synchronous). Agent events go through `WebEvents` to every
WebSocket subscriber of the chat, on the server's event loop. Stop is cooperative: the next streamed token or tool
start of the run raises `Aborted`, which the agent loop already settles consistently (as for Ctrl-C in the CLI).
A bash command that is already running finishes or times out first.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import re
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

from kentc_agent.adapters.documents import attach_document
from kentc_agent.adapters.llm import LLMError
from kentc_agent.adapters.session import Session
from kentc_agent.adapters.tools import CORE_TOOLS, ToolContext, ToolError
from kentc_agent.adapters.web_research import web_search_tool
from kentc_agent.agent import Aborted, Agent, Events, build_tools
from kentc_agent.config import STATE_DIR, Settings
from kentc_agent.context.compaction import CompactionError
from kentc_agent.ports import LLM

from .workspace import inside

CHAT_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
ATTACHMENT = re.compile(r'<attachment path="([^"\n]*)">\n.*?\n</attachment>(?:\n\n)?', re.DOTALL)   # attach_document
ACTIVITY_LIMIT = 4000           # buffered live events per chat (consecutive deltas are merged into one)
TOOL_RESULT_PREVIEW = 4000      # characters of a tool result sent to the live panel
TITLE_CHARS = 80


class ChatBusy(RuntimeError):
    """A chat runs one prompt (or compaction) at a time."""


def text_of(content: Any) -> str:
    """Message content as text; image parts as a marker."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(p.get("text", "") if p.get("type") == "text" else f"[{p.get('type', 'part')}]"
                         for p in content if isinstance(p, dict))
    return ""


def split_attachments(text: str) -> tuple[str, list[str]]:
    """A journaled user prompt -> (what the user typed, attached paths); the attached text stays in the context view."""
    paths = ATTACHMENT.findall(text)
    return (ATTACHMENT.sub("", text).strip(), paths) if paths else (text, [])


def display_message(msg: dict[str, Any], mid: int | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"role": msg.get("role", ""), "content": text_of(msg.get("content"))}
    if mid is not None:
        out["id"] = mid
    if msg.get("reasoning_content"):
        out["reasoning"] = msg["reasoning_content"]
    if msg.get("tool_calls"):
        out["tool_calls"] = [{"id": c.get("id", ""), "name": c.get("function", {}).get("name", ""),
                              "arguments": c.get("function", {}).get("arguments", "")} for c in msg["tool_calls"]]
    if msg.get("tool_call_id"):
        out["tool_call_id"] = msg["tool_call_id"]
    return out


def read_journal(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


class WebEvents(Events):
    def __init__(self, chat: Chat) -> None:
        self.chat = chat

    def _check_stop(self) -> None:
        if self.chat.stop_requested.is_set():
            raise Aborted()

    def delta(self, agent: str, kind: str, text: str) -> None:
        self._check_stop()
        self.chat.publish({"type": "delta", "agent": agent, "kind": kind, "text": text})

    def tool_start(self, agent: str, name: str, args: dict[str, Any]) -> None:
        self._check_stop()
        self.chat.publish({"type": "tool_start", "agent": agent, "name": name, "args": args})

    def tool_end(self, agent: str, name: str, result: str, error: bool) -> None:
        self.chat.publish({"type": "tool_end", "agent": agent, "name": name, "error": error,
                           "result": result[:TOOL_RESULT_PREVIEW], "chars": len(result)})

    def compaction(self, agent: str, before: int, after: int) -> None:
        self.chat.publish({"type": "compaction", "agent": agent, "before": before, "after": after})

    def big_result(self, agent: str, tool: str, args: Any, routed: dict[str, Any], shown: int) -> None:
        self.chat.publish({"type": "big_result", "agent": agent, "tool": tool, "args": args, "routed": routed,
                           "shown": shown})

    def status(self, agent: str, text: str) -> None:
        self.chat.publish({"type": "status", "agent": agent, "text": text})

    def turn_end(self, agent: str, tokens: int, window: int) -> None:
        if agent == "main":
            self.chat.tokens, self.chat.window = tokens, window
        self.chat.publish({"type": "turn_end", "agent": agent, "tokens": tokens, "window": window})


class Chat:
    def __init__(self, runtime: Runtime, key: str, session: Session) -> None:
        self.runtime = runtime
        self.key = key
        self.session = session
        self.ctx = ToolContext(runtime.workspace, runtime.settings, runtime.llm, WebEvents(self))
        self.agent = Agent(self.ctx, tools=build_tools(None, {**CORE_TOOLS, "web_search": web_search_tool()}),
                           session=session)
        self.stop_requested = threading.Event()
        self.busy: str | None = None             # "chat" | "compact" while a worker runs
        self.tokens = 0
        self.window = 0
        self._lock = threading.Lock()
        self._seq = itertools.count(1)
        self._activity: deque[dict[str, Any]] = deque(maxlen=ACTIVITY_LIMIT)
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    # ------------------------------------------------------------------ events
    def publish(self, event: dict[str, Any]) -> None:
        """Buffer an event for late subscribers and fan it out on the server loop (callable from any thread)."""
        with self._lock:
            event = {**event, "seq": next(self._seq), "t": time.time()}
            last = self._activity[-1] if self._activity else None
            if (event["type"] == "delta" and last is not None and last["type"] == "delta"
                    and last["agent"] == event["agent"] and last["kind"] == event["kind"]):
                self._activity[-1] = {**last, "text": last["text"] + event["text"], "seq": event["seq"]}
            else:
                self._activity.append(dict(event))
        loop = self.runtime.loop
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(self._fan_out, event)

    def _fan_out(self, event: dict[str, Any]) -> None:
        for queue in list(self._subscribers):
            queue.put_nowait(event)

    def subscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> dict[str, Any]:
        """Register on the loop thread; the snapshot's `seq` tells the client which queued events it already has."""
        with self._lock:
            self._subscribers.add(queue)
            activity = list(self._activity)
            seq = activity[-1]["seq"] if activity else 0
        return {"key": self.key, "session_id": self.session.id, "busy": self.busy, "tokens": self.tokens,
                "window": self.window, "activity": activity, "seq": seq}

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)

    # ------------------------------------------------------------------ runs
    def send(self, text: str, attachments: list[str]) -> None:
        text = text.strip()
        if not text:
            raise ValueError("empty message")
        for a in attachments:
            if not inside(self.runtime.workspace, a).is_file():
                raise ValueError(f"not a file: {a}")
        self._spawn("chat", lambda: self._chat(text, attachments))

    def compact(self, focus: str | None) -> None:
        self._spawn("compact", lambda: self._compact(focus))

    def stop(self) -> None:
        if self.busy:
            self.stop_requested.set()
            self.publish({"type": "stopping"})

    def _spawn(self, kind: str, work: Callable[[], dict[str, Any]]) -> None:
        with self._lock:
            if self.busy:
                raise ChatBusy(f"this chat is already running a {self.busy}")
            self.busy = kind
            self.stop_requested.clear()
        threading.Thread(target=self._worker, args=(kind, work), name=f"breezeman-{self.key}", daemon=True).start()

    def _worker(self, kind: str, work: Callable[[], dict[str, Any]]) -> None:
        try:
            outcome = work()
        except Aborted:
            outcome = {"type": "aborted"}
        except (LLMError, ToolError, CompactionError, OSError, ValueError, RuntimeError) as e:
            outcome = {"type": "error", "message": str(e)}
        except Exception as e:  # noqa: BLE001 - any run failure must reach the browser, not end the thread silently
            outcome = {"type": "error", "message": f"{type(e).__name__}: {e}"}
        with self._lock:
            self.busy = None
        self.publish({**outcome, "run": kind, "tokens": self.agent.context_tokens(), "window": self.window})

    def _chat(self, text: str, attachments: list[str]) -> dict[str, Any]:
        self.publish({"type": "run_start", "run": "chat", "text": text, "attachments": attachments})
        parts = [attach_document(self.ctx, inside(self.runtime.workspace, a), None, label=a) for a in attachments]
        answer = self.agent.run("\n\n".join([*parts, text]))
        return {"type": "done", "answer": answer, "stopped": self.agent.stopped}

    def _compact(self, focus: str | None) -> dict[str, Any]:
        self.publish({"type": "run_start", "run": "compact", "text": "/compact" + (f" {focus}" if focus else ""),
                      "attachments": []})
        compacted = self.agent.compact(focus or None, force=True)
        return {"type": "compacted", "compacted": compacted}

    # ------------------------------------------------------------------ views
    def transcript(self) -> list[dict[str, Any]]:
        """The whole conversation from the journal (compaction drops history from the context, not the journal)."""
        path = self.session.path
        if path is None or not path.is_file():
            return []
        out = []
        for row in read_journal(path):
            if row.get("type") == "message" and isinstance(row.get("message"), dict):
                item = display_message(row["message"], row.get("id"))
                if item["role"] == "user":
                    item["content"], item["attachments"] = split_attachments(item["content"])
                out.append(item)
            elif row.get("type") == "compaction":
                out.append({"role": "compaction", "content": row.get("summary", "")})
        return out

    def context(self) -> dict[str, Any]:
        """What the main agent's next model call sees, for the searchable context panel."""
        s = self.session
        topics_error = ""
        try:
            topics = s.read_topics()
        except (OSError, ValueError) as e:
            topics, topics_error = {}, str(e)
        window = self.window
        if not window:
            try:
                window = self.agent.window
            except LLMError:
                window = 0
        return {
            "key": self.key, "session_id": s.id, "busy": self.busy,
            "tokens": self.agent.context_tokens(), "window": window,
            "system": self.agent.system,
            "persona": s.core.get("persona", ""), "instructions": s.core.get("instructions", ""),
            "checkpoint": s.summary or "",
            "topics": [{"slug": k, "text": v} for k, v in sorted(topics.items())], "topics_error": topics_error,
            "messages": [display_message(m) for m in s.context()],
            "tools": [{"name": t.name, "description": t.description, "parameters": t.parameters}
                      for t in self.agent.tools.values()],
        }

    def close(self) -> None:
        self.stop_requested.set()
        self.agent.close()


class Runtime:
    def __init__(self, workspace: Path, settings: Settings, llm: LLM) -> None:
        self.workspace = workspace
        self.settings = settings
        self.llm = llm
        self.sessions_dir = workspace / STATE_DIR / "sessions"
        self.loop: asyncio.AbstractEventLoop | None = None
        self._chats: dict[str, Chat] = {}
        self._lock = threading.Lock()

    def new_chat(self) -> Chat:
        session = Session()
        session.path = self.sessions_dir / f"{session.id}.jsonl"
        chat = Chat(self, session.id, session)
        with self._lock:
            self._chats[chat.key] = chat
        return chat

    def chat(self, key: str) -> Chat:
        """An open chat, or a saved session resumed with a fresh main agent. KeyError when there is none."""
        if not CHAT_KEY.fullmatch(key):
            raise KeyError(key)
        with self._lock:
            if key in self._chats:
                return self._chats[key]
            path = self.sessions_dir / f"{key}.jsonl"
            if not path.is_file():
                raise KeyError(key)
            chat = self._chats[key] = Chat(self, key, Session.load(path))
            return chat

    def list_chats(self) -> list[dict[str, Any]]:
        """Saved sessions with at least one message, plus open chats; newest first."""
        found: dict[str, dict[str, Any]] = {}
        if self.sessions_dir.is_dir():
            for path in self.sessions_dir.glob("*.jsonl"):
                if not CHAT_KEY.fullmatch(path.stem):
                    continue
                title, count = "", 0
                for row in read_journal(path):
                    if row.get("type") == "message":
                        count += 1
                        msg = row.get("message") or {}
                        if not title and msg.get("role") == "user":
                            title = " ".join(split_attachments(text_of(msg.get("content")))[0].split())[:TITLE_CHARS]
                if count:
                    found[path.stem] = {"key": path.stem, "title": title, "messages": count,
                                        "updated": path.stat().st_mtime}
        with self._lock:
            open_chats = list(self._chats.values())
        for chat in open_chats:
            entry = found.setdefault(chat.key, {"key": chat.key, "title": "", "messages": 0, "updated": time.time()})
            entry["open"] = True
            entry["busy"] = chat.busy
        return sorted(found.values(), key=lambda e: e["updated"], reverse=True)

    def close(self) -> None:
        with self._lock:
            chats = list(self._chats.values())
            self._chats.clear()
        for chat in chats:
            chat.close()
