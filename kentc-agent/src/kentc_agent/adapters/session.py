"""The conversation: an append-only JSONL log plus the live context rebuilt from it.

Log entries:
  {"type": "session", "id": "<session id>", "created": "<iso time>"}      first line; names the trace (trace.py)
  {"type": "message", "id": N, "message": {...}, "usage": {...}?}
  {"type": "compaction", "summary": "...", "first_kept_id": N, "tokens_before": T}
  {"type": "requirement", "text": "...", "active": true}
  {"type": "tool_arguments", "id": N, "arguments": {"<tool call id>": "<shortened JSON>"}}

Live context includes the latest summary, active user requirements, and messages with id >= first_kept_id.
"""

from __future__ import annotations

import hashlib
import json
import math
import secrets
import time
from pathlib import Path
from typing import Any

from .llm import Usage

CHARS_PER_TOKEN = 4  # conservative for English/code; CJK runs denser, the server's usage corrects it each turn
SUMMARY_PREFIX = "The earlier conversation was compacted into this summary:\n\n<summary>\n"
SUMMARY_SUFFIX = "\n</summary>"
MAX_REQUIREMENT_CHARS = 4000


def image_tokens(width: int, height: int) -> int:
    """Qwen-VL style: one token per 28x28 patch."""
    return max(64, math.ceil(width / 28) * math.ceil(height / 28))


def estimate_tokens(msg: dict[str, Any]) -> int:
    chars = 0
    content = msg.get("content")
    if isinstance(content, str):
        chars += len(content)
    elif isinstance(content, list):
        for part in content:
            if part.get("type") == "text":
                chars += len(part.get("text", ""))
            elif part.get("type") == "image_url":
                chars += CHARS_PER_TOKEN * int(part.get("_tokens", 1500))
    chars += len(msg.get("reasoning_content") or "")
    for call in msg.get("tool_calls") or []:
        chars += len(call["function"]["name"]) + len(call["function"]["arguments"]) + 16
    return math.ceil(chars / CHARS_PER_TOKEN) + 4


def summary_message(summary: str) -> dict[str, Any]:
    return {"role": "user", "content": SUMMARY_PREFIX + summary + SUMMARY_SUFFIX}


def new_session_id() -> str:
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2)}"


def loggable(msg: dict[str, Any]) -> dict[str, Any]:
    """The message as logged: inline (base64) images become a placeholder, so transcripts stay small and readable."""
    content = msg.get("content")
    if not isinstance(content, list):
        return msg
    parts = [{"type": "text", "text": f"[image, ~{p.get('_tokens', '?')} tokens, not logged]"}
             if p.get("type") == "image_url" and str(p["image_url"]["url"]).startswith("data:") else p
             for p in content]
    return {**msg, "content": parts}


class Session:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.id = new_session_id()
        self.summary: str | None = None
        self.messages: list[dict[str, Any]] = []   # live, without the system prompt or summary
        self.ids: list[int] = []                   # log id of each live message
        self.usage: dict[int, Usage] = {}          # log id of an assistant reply -> what the server counted
        self.next_id = 0
        self.compactions = 0
        self.requirements: list[str] = []

    # ------------------------------------------------------------------ persistence
    @classmethod
    def load(cls, path: Path) -> Session:
        s = cls(path)
        s.id = f"{path.stem}-{hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:6]}"   # a log without a header
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            if e["type"] == "session":
                s.id = e["id"]
            elif e["type"] == "message":
                s.messages.append(e["message"])
                s.ids.append(e["id"])
                if e.get("usage"):
                    s.usage[e["id"]] = Usage(**e["usage"])
                s.next_id = e["id"] + 1
            elif e["type"] == "compaction":
                s._drop_before(e["first_kept_id"])
                s.summary = e["summary"]
                s.compactions += 1
            elif e["type"] == "requirement":
                s.set_requirement(e["text"], active=e["active"], persist=False)
            elif e["type"] == "replacement" and e["id"] in s.ids:
                s.replace_content(s.ids.index(e["id"]), e["content"], persist=False)
            elif e["type"] == "tool_arguments" and e["id"] in s.ids:
                s.replace_tool_arguments(s.ids.index(e["id"]), e["arguments"], persist=False)
        return s

    def _write(self, entry: dict[str, Any]) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.is_file()
        with self.path.open("a", encoding="utf-8") as f:
            if new:
                f.write(json.dumps({"type": "session", "id": self.id, "created": time.strftime("%Y-%m-%dT%H:%M:%S")})
                        + "\n")
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------ mutation
    def set_requirement(self, text: str, *, active: bool = True, persist: bool = True) -> None:
        """Pin user-supplied text independently of the live messages and model summary."""
        if not text.strip():
            raise ValueError("requirement text must not be empty")
        if active == (text in self.requirements):
            return
        if active and sum(map(len, self.requirements)) + len(text) > MAX_REQUIREMENT_CHARS:
            raise ValueError(f"active requirements are limited to {MAX_REQUIREMENT_CHARS} characters total")
        if persist:
            self._write({"type": "requirement", "text": text, "active": active})
        if active:
            self.requirements.append(text)
        else:
            self.requirements.remove(text)
        self.usage.clear()

    def append(self, msg: dict[str, Any], usage: Usage | None = None) -> None:
        mid = self.next_id
        self.next_id += 1
        self.messages.append(msg)
        self.ids.append(mid)
        entry: dict[str, Any] = {"type": "message", "id": mid, "message": loggable(msg)}
        if usage is not None:
            self.usage[mid] = usage
            entry["usage"] = {"prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens}
        self._write(entry)

    def compact(self, summary: str, first_kept: int, tokens_before: int) -> None:
        """Replace live messages [0, first_kept) (and any previous summary) by `summary`."""
        first_kept_id = self.ids[first_kept] if first_kept < len(self.ids) else self.next_id
        self._write({"type": "compaction", "summary": summary, "first_kept_id": first_kept_id,
                     "tokens_before": tokens_before})
        self._drop_before(first_kept_id)
        self.summary = summary
        self.compactions += 1

    def replace_content(self, index: int, content: str, *, persist: bool = True) -> None:
        """Replace an archived message's live payload while retaining its role and tool-call identity."""
        if persist:
            self._write({"type": "replacement", "id": self.ids[index], "content": content})
        self.messages[index] = {**self.messages[index], "content": content}
        self.usage.clear()  # earlier server counts describe the longer, original payload

    def replace_tool_arguments(self, index: int, arguments: dict[str, str], *, persist: bool = True) -> None:
        """Shorten selected historical calls while preserving their identity and the original log entry."""
        message = self.messages[index]
        calls = [{**call, "function": {**call["function"], "arguments": arguments[call["id"]]}}
                 if call["id"] in arguments else call for call in message["tool_calls"]]
        if persist:
            self._write({"type": "tool_arguments", "id": self.ids[index], "arguments": arguments})
        self.messages[index] = {**message, "tool_calls": calls}
        self.usage.clear()

    def _drop_before(self, first_kept_id: int) -> None:
        keep = [i for i, mid in enumerate(self.ids) if mid >= first_kept_id]
        self.messages = [self.messages[i] for i in keep]
        self.ids = [self.ids[i] for i in keep]
        self.usage = {}   # counts taken before a compaction describe the old, longer prompt

    # ------------------------------------------------------------------ views
    def context(self) -> list[dict[str, Any]]:
        """The messages to send after the system prompt."""
        head = [summary_message(self.summary)] if self.summary else []
        if self.requirements:
            head.append({"role": "user", "content": "My active requirements for this session (verbatim):\n\n"
                         + "\n\n".join(self.requirements)})
        return head + self.messages

    def token_parts(self, fixed_tokens: int) -> tuple[int, int]:
        """(counted, estimated) tokens of the next request's prompt. `fixed_tokens`: system prompt + tool schemas
        (estimated). Counted = the newest reply the server counted (its prompt + completion); estimated = chars/4 of
        the messages after it. With no counted reply in the live context (e.g. right after a compaction), all of it
        is estimated."""
        for i in range(len(self.messages) - 1, -1, -1):
            u = self.usage.get(self.ids[i])
            if u is not None:
                return u.total, sum(estimate_tokens(m) for m in self.messages[i + 1:])
        return 0, fixed_tokens + sum(estimate_tokens(m) for m in self.context())

    def context_tokens(self, fixed_tokens: int, density: float = 1.0) -> int:
        """Tokens the next request's prompt will take; `density` scales the estimated part (server tokens per
        chars/4 token, learned by the agent: paths, JSON and code run denser than chars/4)."""
        counted, estimated = self.token_parts(fixed_tokens)
        return counted + math.ceil(estimated * density)
