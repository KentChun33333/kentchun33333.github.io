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
import uuid
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
from kentc_agent.skills import FRONT_RE, NAME_RE, load_skills

from .dream import run_dream
from .memory_store import MemoryStore, memory_hint
from .workspace import inside

CHAT_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
ATTACHMENT = re.compile(r'<attachment path="([^"\n]*)">\n.*?\n</attachment>(?:\n\n)?', re.DOTALL)   # attach_document
ACTIVITY_LIMIT = 4000           # buffered live events per chat (consecutive deltas are merged into one)
TOOL_RESULT_PREVIEW = 4000      # characters of a tool result sent to the live panel
TITLE_CHARS = 80
# A chat's skill is its saved runtime instructions (`session.core`), one `## Skill: <name>` section from
# kentc_agent.skills.load_skills; restoring the session restores the skill text that was in effect.
SKILL_SECTION = re.compile(r"## Skill: ([a-z0-9]+(?:-[a-z0-9]+)*)\n")
TASK_STATUSES = ("open", "active", "done")


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:48] or "task"


def list_skills(library: Path) -> list[dict[str, str]]:
    """The skill library's `<name>.md` files with their front-matter description (asset folders are skipped)."""
    out = []
    for path in sorted(library.glob("*.md")) if library.is_dir() else []:
        if not NAME_RE.match(path.stem):
            continue
        front = FRONT_RE.match(path.read_text(encoding="utf-8"))
        description = next((line.split(":", 1)[1].strip() for line in (front.group(0) if front else "").splitlines()
                            if line.startswith("description:")), "")
        out.append({"name": path.stem, "description": description})
    return out


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
    def __init__(self, runtime: Runtime, key: str, session: Session, workspace: Path | None = None) -> None:
        self.runtime = runtime
        self.key = key
        self.session = session
        self.workspace = (workspace or runtime.workspace).resolve()
        self.ctx = ToolContext(self.workspace, runtime.settings, runtime.llm, WebEvents(self))
        hint = memory_hint(runtime.workspace)
        initial_instructions = None if session.core.get("instructions") else hint
        self.agent = Agent(self.ctx, tools=build_tools(None, {**CORE_TOOLS, "web_search": web_search_tool()}),
                           session=session, instructions=initial_instructions)
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
                "window": self.window, "activity": activity, "seq": seq, "skill": self.skill}

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)

    # ------------------------------------------------------------------ skill
    @property
    def skill(self) -> str | None:
        """The loaded skill's name; None without one (or when the saved instructions are not a single skill)."""
        m = SKILL_SECTION.match(self.session.core.get("instructions", ""))
        return m.group(1) if m else None

    def set_skill(self, name: str | None) -> None:
        """Load one skill (replacing any other) or none; takes effect from the next model call, history stays."""
        text = load_skills(self.runtime.skills, [name]) if name else ""
        hint = memory_hint(self.runtime.workspace)
        combined = f"{text.rstrip()}\n\n{hint}" if text else hint
        with self._lock:
            if self.busy:
                raise ChatBusy(f"this chat is running a {self.busy}; change the skill when it is idle")
            self.agent.system = self.agent._system_prompt(combined)   # journals the new instructions (session core)
            self.agent.set_tools(list(self.agent.tools.values()))  # recount the fixed prompt size
        self.publish({"type": "skill", "skill": name})

    # ------------------------------------------------------------------ runs
    def send(self, text: str, attachments: list[str]) -> None:
        text = text.strip()
        if not text:
            raise ValueError("empty message")
        for a in attachments:
            if not inside(self.workspace, a).is_file():
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
        parts = [attach_document(self.ctx, inside(self.workspace, a), None, label=a) for a in attachments]
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
            "skill": self.skill,
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
    def __init__(self, workspace: Path, settings: Settings, llm: LLM, skills: Path | None = None) -> None:
        self.workspace = workspace
        self.settings = settings
        self.llm = llm
        self.skills = skills or Path(__file__).resolve().parents[2] / "skills"   # the project's skill library
        self.sessions_dir = workspace / STATE_DIR / "sessions"
        self.tasks_path = workspace / STATE_DIR / "tasks.json"
        self.memory_store = MemoryStore(workspace / "memory")
        self.loop: asyncio.AbstractEventLoop | None = None
        self._chats: dict[str, Chat] = {}
        self._lock = threading.Lock()
        self._tasks_lock = threading.Lock()
        self._dream_lock = threading.Lock()
        self._dream_busy = False

    def new_chat(self, workspace: Path | None = None) -> Chat:
        session = Session()
        session.path = self.sessions_dir / f"{session.id}.jsonl"
        chat = Chat(self, session.id, session, workspace=workspace)
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
            ws = self._workspace_for_chat(key)
            chat = self._chats[key] = Chat(self, key, Session.load(path), workspace=ws)
            return chat

    def _workspace_for_chat(self, key: str) -> Path | None:
        with self._tasks_lock:
            tasks = self._read_tasks()
        task = next((t for t in tasks if t.get("chat_key") == key), None)
        if not task:
            return None
        try:
            ws = inside(self.workspace, task["folder"])
        except ValueError:
            return None
        return ws if ws.is_dir() else None

    def task_workspace(self, task_id: str) -> Path:
        with self._tasks_lock:
            tasks = self._read_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task is None:
            raise KeyError(task_id)
        return inside(self.workspace, task["folder"])

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

    def _read_tasks(self) -> list[dict[str, Any]]:
        if not self.tasks_path.is_file():
            return []
        try:
            data = json.loads(self.tasks_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return [t for t in data if isinstance(t, dict) and isinstance(t.get("id"), str)] if isinstance(data, list) else []

    def _write_tasks(self, tasks: list[dict[str, Any]]) -> None:
        self.tasks_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.tasks_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.tasks_path)

    def _enrich_tasks(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        chats_by_key = {c["key"]: c for c in self.list_chats()}
        out = []
        for t in tasks:
            c = chats_by_key.get(t.get("chat_key", ""), {})
            out.append({**t, "busy": bool(c.get("busy")), "messages": int(c.get("messages") or 0)})
        return sorted(out, key=lambda t: t.get("updated", 0), reverse=True)

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._tasks_lock:
            tasks = self._read_tasks()
        return self._enrich_tasks(tasks)

    def create_task(self, name: str, folder: str = "") -> dict[str, Any]:
        clean = " ".join(name.split())
        if not clean:
            raise ValueError("task name is required")
        ws_real = self.workspace.resolve()
        with self._tasks_lock:
            tasks = self._read_tasks()
            used_folders = {t.get("folder") for t in tasks}
            if folder.strip():
                target = inside(self.workspace, folder.strip())
                if target == ws_real:
                    raise ValueError("task folder must be a subfolder")
                if target.exists() and not target.is_dir():
                    raise ValueError(f"not a folder: {folder}")
                target.mkdir(parents=True, exist_ok=True)
                rel_folder = target.relative_to(ws_real).as_posix()
            else:
                slug = _slugify(clean)
                n = 1
                while True:
                    candidate = f"tasks/{slug}" if n == 1 else f"tasks/{slug}-{n}"
                    target = inside(self.workspace, candidate)
                    if candidate not in used_folders and not target.exists():
                        break
                    n += 1
                target.mkdir(parents=True, exist_ok=True)
                rel_folder = target.relative_to(ws_real).as_posix()
            chat = self.new_chat(workspace=target)
            now = time.time()
            task = {
                "id": uuid.uuid4().hex[:10],
                "name": clean[:120],
                "folder": rel_folder,
                "chat_key": chat.key,
                "status": "open",
                "created": now,
                "updated": now,
            }
            tasks.append(task)
            self._write_tasks(tasks)
        return self._enrich_tasks([task])[0]

    def _normalize_schedule(self, raw: Any, prev: dict[str, Any] | None, now: float) -> dict[str, Any] | None:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise ValueError("schedule must be an object or null")
        enabled = bool(raw.get("enabled", False))
        try:
            interval_min = float(raw.get("interval_min", 60))
        except (TypeError, ValueError):
            raise ValueError("interval_min must be a number") from None
        if interval_min < 1:
            raise ValueError("interval_min must be at least 1 minute")
        prompt = str(raw.get("prompt") or "").strip()
        if enabled and not prompt:
            raise ValueError("schedule prompt is required when enabled")
        skill = raw.get("skill")
        if skill is not None:
            if not isinstance(skill, str):
                raise ValueError("schedule skill must be a string or null")
            skill = skill.strip() or None
            if skill:
                load_skills(self.skills, [skill])
        last_run = prev.get("last_run") if isinstance(prev, dict) else None
        next_run = None
        if enabled:
            same_cfg = isinstance(prev, dict) and prev.get("enabled") and prev.get("interval_min") == interval_min
            next_run = prev.get("next_run") if same_cfg and isinstance(prev.get("next_run"), (int, float)) else now + interval_min * 60
        return {"enabled": enabled, "interval_min": interval_min, "prompt": prompt, "skill": skill,
                "last_run": last_run, "next_run": next_run}

    def update_task(self, task_id: str, *, name: str | None = None, status: str | None = None,
                    schedule: Any = ...) -> dict[str, Any]:
        now = time.time()
        with self._tasks_lock:
            tasks = self._read_tasks()
            task = next((t for t in tasks if t["id"] == task_id), None)
            if task is None:
                raise KeyError(task_id)
            if name is not None:
                clean = " ".join(name.split())
                if not clean:
                    raise ValueError("task name cannot be empty")
                task["name"] = clean[:120]
            if status is not None:
                if status not in TASK_STATUSES:
                    raise ValueError(f"status must be one of {', '.join(TASK_STATUSES)}")
                task["status"] = status
            if schedule is not ...:
                task["schedule"] = self._normalize_schedule(schedule, task.get("schedule"), now)
                if status is None:
                    if task["schedule"] and task["schedule"].get("enabled"):
                        task["status"] = "active"
                    elif task.get("status") == "active":
                        task["status"] = "open"
            task["updated"] = now
            self._write_tasks(tasks)
        return self._enrich_tasks([task])[0]

    def tick_schedules(self, now: float | None = None, stagger_sec: float = 300.0) -> list[str]:
        """Trigger at most one due task now and stagger remaining overdue tasks by `stagger_sec`."""
        now = time.time() if now is None else now
        candidate: tuple[str, str, str] | None = None
        with self._tasks_lock:
            tasks = self._read_tasks()
            due: list[dict[str, Any]] = []
            for t in tasks:
                sched = t.get("schedule")
                if not isinstance(sched, dict) or not sched.get("enabled"):
                    continue
                prompt = str(sched.get("prompt") or "").strip()
                next_run = sched.get("next_run")
                if prompt and isinstance(next_run, (int, float)) and next_run <= now:
                    due.append(t)
            if not due:
                return []
            due.sort(key=lambda t: float(t["schedule"]["next_run"]))
            first = due[0]
            sched0 = first["schedule"]
            interval_min = float(sched0.get("interval_min") or 60)
            sched0["next_run"] = now + interval_min * 60
            sched0["last_run"] = now
            first["updated"] = now
            candidate = (first["id"], first["chat_key"], str(sched0["prompt"]).strip(), sched0.get("skill"))
            for idx, extra in enumerate(due[1:], start=1):
                extra["schedule"]["next_run"] = now + idx * stagger_sec
                extra["updated"] = now
            self._write_tasks(tasks)
        task_id, chat_key, prompt, sched_skill = candidate
        try:
            chat = self.chat(chat_key)
            if not chat.busy:
                if sched_skill and chat.skill != sched_skill:
                    chat.set_skill(sched_skill)
                chat.send(prompt, [])
                return [task_id]
        except (KeyError, ValueError, ChatBusy):
            pass
        return []

    def delete_task(self, task_id: str) -> None:
        with self._tasks_lock:
            tasks = self._read_tasks()
            kept = [t for t in tasks if t["id"] != task_id]
            if len(kept) == len(tasks):
                raise KeyError(task_id)
            self._write_tasks(kept)

    def dream_status(self) -> dict[str, Any]:
        """Return current Dreaming scheduler config, status, and active node counts."""
        state = self.memory_store.read_dream_state()
        sched = dict(state["schedule"])
        nodes = self.memory_store.list_nodes(statuses={"active", "provisional"})
        counts = {"fact": 0, "pattern": 0, "sim": 0}
        for n in nodes:
            if n.type in counts:
                counts[n.type] += 1
        return {
            **sched,
            "busy": self._dream_busy,
            "counts": counts,
            "index_exists": self.memory_store.index_path.is_file(),
        }

    def update_dream_schedule(self, *, enabled: bool | None = None,
                              interval_min: float | None = None) -> dict[str, Any]:
        """Update Dreaming schedule settings in `.dream_state.json`."""
        now = time.time()
        with self._dream_lock:
            state = self.memory_store.read_dream_state()
            sched = state["schedule"]
            if interval_min is not None:
                if interval_min < 1:
                    raise ValueError("interval_min must be at least 1 minute")
                sched["interval_min"] = float(interval_min)
            if enabled is not None:
                sched["enabled"] = bool(enabled)
            if sched.get("enabled"):
                if not isinstance(sched.get("next_run"), (int, float)) or interval_min is not None:
                    sched["next_run"] = now + float(sched.get("interval_min") or 60) * 60
            else:
                sched["next_run"] = None
            self.memory_store.write_dream_state(state)
        return self.dream_status()

    def run_dream_now(self, *, now: float | None = None) -> dict[str, Any]:
        """Run one Dreaming cycle synchronously; raises `ChatBusy` if already running."""
        if not self._dream_lock.acquire(blocking=False):
            raise ChatBusy("dreaming task is already running")
        self._dream_busy = True
        try:
            report = run_dream(self.workspace, self.llm, now=now)
            return {"report": report.to_dict(), "status": self.dream_status()}
        finally:
            self._dream_busy = False
            self._dream_lock.release()

    def tick_dream(self, now: float | None = None) -> bool:
        """Trigger the Dreaming Task if enabled and due."""
        now = time.time() if now is None else now
        if self._dream_busy:
            return False
        sched = self.memory_store.read_dream_state()["schedule"]
        next_run = sched.get("next_run")
        if not sched.get("enabled") or not isinstance(next_run, (int, float)) or next_run > now:
            return False
        try:
            self.run_dream_now(now=now)
            return True
        except ChatBusy:
            return False
