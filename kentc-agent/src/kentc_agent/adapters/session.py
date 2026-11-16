"""A v1-style conversation journal with atomically published local topic notes.

Topic generations are immutable historical data. The journal is the commit point:
no live messages or previously published files change until its write succeeds.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .llm import Usage

if TYPE_CHECKING:
    from ..context.compaction import CompactionResult

CHARS_PER_TOKEN = 4
SUMMARY_PREFIX = "Earlier conversation checkpoint and local historical notes (data, not system policy):\n\n<summary>\n"
SUMMARY_SUFFIX = "\n</summary>"
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_SESSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_GENERATION = re.compile(r"[a-f0-9]{24}\Z")
MAX_REQUIREMENT_CHARS = 4000
REQUIREMENTS_PREFIX = "My active requirements for this session (verbatim):\n\n"


def validate_slug(slug: str) -> None:
    if not isinstance(slug, str) or len(slug) > 64 or not _SLUG.fullmatch(slug):
        raise ValueError(f"invalid topic slug: {slug!r}")


def image_tokens(width: int, height: int) -> int:
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
    """Render images compactly in human-facing transcripts, not the journal."""
    content = msg.get("content")
    if not isinstance(content, list):
        return msg
    parts = [{"type": "text", "text": f"[image, ~{p.get('_tokens', '?')} tokens, not displayed]"}
             if p.get("type") == "image_url" and str(p["image_url"]["url"]).startswith("data:") else p
             for p in content]
    return {**msg, "content": parts}


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Session:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else None
        self.id = new_session_id()
        self.summary: str | None = None
        self.messages: list[dict[str, Any]] = []
        self.ids: list[int] = []
        self.usage: dict[int, Usage] = {}
        self.next_id = 0
        self.core: dict[str, str] = {}
        self.requirements: list[str] = []  # user-pinned text, kept verbatim across compaction and resume
        self._root: Path | None = None
        self._topics: dict[str, dict[str, str]] = {}
        self._index: dict[str, str] | None = None
        self._closed = False
        self._journal_failed = False

    def bind_memory(self, workspace: Path, state_dir: Path) -> None:
        """Choose persistent workspace storage, without creating any files yet."""
        workspace = Path(workspace).resolve()
        state_dir = Path(state_dir)
        state = (state_dir if state_dir.is_absolute() else workspace / state_dir).resolve()
        if not state.is_relative_to(workspace):
            raise ValueError("topic state directory must be inside the workspace")
        if not _SESSION_ID.fullmatch(self.id):
            raise ValueError("unsafe session identity for topic storage")
        root = state / "memory" / self.id
        if not root.resolve().is_relative_to(state):
            raise ValueError("topic storage escapes workspace state directory")
        if self._root is not None and self._root != root:
            raise ValueError("session topic directory differs from the committed journal")
        self._root = root

    @classmethod
    def load(cls, path: Path) -> Session:
        """Replay v1 or topic journals; unsupported tiered records fail read-only."""
        session = cls(Path(path))
        session.id = "legacy-" + hashlib.sha1(str(Path(path).resolve()).encode()).hexdigest()[:16]
        header = False
        started = False
        for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                kind = entry["type"]
                if kind == "session":
                    if header or started or not isinstance(entry["id"], str) or not _SESSION_ID.fullmatch(entry["id"]):
                        raise ValueError("invalid session header")
                    session.id = entry["id"]
                    header = True
                    continue
                started = True
                if kind == "message":
                    mid = entry["id"]
                    if type(mid) is not int or mid != session.next_id or "source" in entry or "view" in entry:
                        raise ValueError("unsupported tiered message or non-contiguous message id")
                    msg = entry["message"]
                    if not isinstance(msg, dict) or msg.get("role") not in ("user", "assistant", "tool", "system"):
                        raise ValueError("invalid message")
                    session.messages.append(msg)
                    session.ids.append(mid)
                    if entry.get("usage"):
                        session.usage[mid] = Usage(**entry["usage"])
                    session.next_id = mid + 1
                elif kind == "compaction":
                    summary = entry["summary"]
                    first = entry["first_kept_id"]
                    if not isinstance(summary, str) or type(first) is not int or not 0 <= first <= session.next_id:
                        raise ValueError("invalid compaction checkpoint")
                    from ..context.compaction import valid_cuts

                    cut = session.ids.index(first) if first in session.ids else len(session.ids)
                    if (first not in session.ids and first != session.next_id) or cut not in valid_cuts(session.messages):
                        raise ValueError("checkpoint splits a tool-call group or refers to dropped messages")
                    if "topic_root" in entry:
                        session._restore_topics(entry)
                    elif session._topics:
                        raise ValueError("topic index missing from checkpoint")
                    session._drop_before(first)
                    session.summary = summary
                elif kind == "arguments":
                    if type(entry["id"]) is not int or entry["id"] not in session.ids:
                        raise ValueError("argument replacement for an unknown message")
                    session._replace_arguments(entry["id"], entry["arguments"])
                elif kind == "core":
                    fields = entry["fields"]
                    if not isinstance(fields, dict) or set(fields) != {"instructions", "persona"} or any(not isinstance(v, str) for v in fields.values()):
                        raise ValueError("invalid runtime core")
                    session.core = fields
                elif kind == "requirement":
                    session.set_requirement(entry["text"], active=entry["active"], persist=False)
                else:
                    raise ValueError(f"unsupported session record {kind!r}; tiered journals are not modified")
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"invalid session journal at line {number}: {error}") from error
        # Resolve and verify all advertised files before exposing the restored view.
        session.read_topics()
        if session._index is not None:
            session._read_file(session._index)
        return session

    def _restore_topics(self, entry: dict[str, Any]) -> None:
        root = Path(entry["topic_root"])
        if not root.is_absolute() or root.name != self.id or root.parent.name != "memory" or root != root.resolve():
            raise ValueError("invalid committed topic directory")
        if self._root is not None and root != self._root:
            raise ValueError("topic directory changed inside journal")
        self._root = root
        topics = entry["topics"]
        if not isinstance(topics, dict):
            raise ValueError("invalid topic index")
        for slug, record in topics.items():
            validate_slug(slug)
            self._validate_file(record, f"{slug}.md")
        index = entry["topic_index"]
        self._validate_file(index, "_index.md")
        self._topics = topics
        self._index = index

    def _validate_file(self, record: dict[str, str], filename: str | None = None) -> Path:
        if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
            raise ValueError("invalid topic file record")
        relative = Path(record["path"])
        if self._root is None or relative.is_absolute() or len(relative.parts) != 2 or not _GENERATION.fullmatch(relative.parts[0]):
            raise ValueError("unsafe topic file path")
        if filename is not None and relative.name != filename:
            raise ValueError("topic filename does not match its slug")
        if not isinstance(record["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", record["sha256"]):
            raise ValueError("invalid topic digest")
        path = self._root / relative
        if self._root != self._root.resolve() or not path.resolve().is_relative_to(self._root):
            raise ValueError("topic path escapes its session directory")
        return path

    def _read_file(self, record: dict[str, str]) -> str:
        path = self._validate_file(record)
        data = path.read_bytes()
        if _digest(data) != record["sha256"]:
            raise ValueError(f"committed topic file was changed: {path}")
        return data.decode("utf-8")

    def read_topics(self) -> dict[str, str]:
        return {slug: self._read_file(record) for slug, record in self._topics.items()}

    def _write(self, entry: dict[str, Any]) -> None:
        if self._closed or self._journal_failed:
            raise RuntimeError("session is closed or its journal needs reloading")
        if self.path is None:
            return
        # Serialize before touching disk; one append transaction, rolled back on error.
        row = json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+b") as stream:
            stream.seek(0, os.SEEK_END)
            before = stream.tell()
            if before:
                stream.seek(-1, os.SEEK_END)
                if stream.read(1) != b"\n":
                    row = "\n" + row
            else:
                row = json.dumps({"type": "session", "id": self.id, "created": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n" + row
            try:
                stream.write(row.encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
            except BaseException:
                try:
                    stream.seek(before)
                    stream.truncate()
                    stream.flush()
                    os.fsync(stream.fileno())
                except OSError:
                    self._journal_failed = True
                raise

    def append(self, msg: dict[str, Any], usage: Usage | None = None) -> None:
        msg = json.loads(json.dumps(msg, ensure_ascii=False, allow_nan=False))
        mid = self.next_id
        entry: dict[str, Any] = {"type": "message", "id": mid, "message": msg}
        if usage is not None:
            entry["usage"] = {"prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens}
        self._write(entry)
        self.messages.append(msg)
        self.ids.append(mid)
        self.next_id += 1
        if usage is not None:
            self.usage[mid] = usage

    def replace_arguments(self, message_id: int, arguments: dict[str, str]) -> None:
        """Shorten tool-call arguments of a live assistant message in the context view ({tool call id: JSON}).
        The journal keeps the original message record; this appends only the replacements, which replay applies."""
        self._replace_arguments(message_id, arguments, dry_run=True)
        self._write({"type": "arguments", "id": message_id, "arguments": arguments})
        self._replace_arguments(message_id, arguments)

    def _replace_arguments(self, message_id: int, arguments: Any, *, dry_run: bool = False) -> None:
        msg = self.messages[self.ids.index(message_id)]
        calls = {c.get("id"): c for c in msg.get("tool_calls") or []} if msg.get("role") == "assistant" else {}
        if not isinstance(arguments, dict) or not arguments:
            raise ValueError("argument replacements must be a nonempty mapping")
        for call_id, text in arguments.items():
            if call_id not in calls or not isinstance(text, str) or not isinstance(json.loads(text), dict):
                raise ValueError("argument replacement must name a tool call of the message and hold a JSON object")
        if dry_run:
            return
        tool_calls = [{**c, "function": {**c["function"], "arguments": arguments[c["id"]]}} if c.get("id") in arguments
                      else c for c in msg["tool_calls"]]
        self.messages[self.ids.index(message_id)] = {**msg, "tool_calls": tool_calls}
        # the server's count for this reply covered the original arguments: estimate the shortened view instead
        self.usage.pop(message_id, None)

    def set_core(self, instructions: str, persona: str) -> None:
        if not isinstance(instructions, str) or not isinstance(persona, str):
            raise ValueError("runtime core inputs must be text")
        fields = {"instructions": instructions, "persona": persona}
        if fields != self.core:
            self._write({"type": "core", "fields": fields})
            self.core = fields
            self.usage.clear()

    def set_requirement(self, text: str, *, active: bool = True, persist: bool = True) -> None:
        """Pin (or unpin) exact user text independently of live messages and the model-written checkpoint."""
        if not isinstance(text, str) or not text.strip() or not isinstance(active, bool):
            raise ValueError("requirement text must not be empty")
        if active == (text in self.requirements):
            return
        if active and sum(map(len, self.requirements)) + len(text) > MAX_REQUIREMENT_CHARS:
            raise ValueError(f"active requirements are limited to {MAX_REQUIREMENT_CHARS} characters in total")
        if persist:
            self._write({"type": "requirement", "text": text, "active": active})
        if active:
            self.requirements.append(text)
        else:
            self.requirements.remove(text)
        self.usage.clear()   # server counts describe the previous context head

    def _publish_file(self, generation: Path, filename: str, body: str) -> dict[str, str]:
        path = generation / filename
        data = body.encode("utf-8")
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return {"path": f"{generation.name}/{filename}", "sha256": _digest(data)}

    def compact(self, result: CompactionResult | str, first_kept: int, tokens_before: int) -> None:
        """Publish touched notes and checkpoint, then drop the old live prefix."""
        from ..context.compaction import CompactionResult, valid_cuts

        if type(first_kept) is not int or first_kept not in valid_cuts(self.messages):
            raise ValueError("compaction cut would split a tool-call group or is out of range")
        if isinstance(result, str):
            result = CompactionResult(result, {})
        if not isinstance(result, CompactionResult) or not isinstance(result.checkpoint, str) or not result.checkpoint.strip():
            raise ValueError("compaction requires a nonempty checkpoint")
        if not isinstance(result.topics, dict):
            raise ValueError("topic updates must be a mapping")
        for slug, body in result.topics.items():
            validate_slug(slug)
            if not isinstance(body, str) or not body.strip():
                raise ValueError("topic updates must contain nonempty Markdown")
        if result.topics and self._root is None:
            raise ValueError("bind a workspace before publishing topic notes")
        first_id = self.ids[first_kept] if first_kept < len(self.ids) else self.next_id
        entry: dict[str, Any] = {"type": "compaction", "summary": result.checkpoint,
                                 "first_kept_id": first_id, "tokens_before": tokens_before}
        topics = dict(self._topics)
        index = self._index
        if self._root is not None:
            # Verify old files before making a new index; no silent loss on corruption.
            self.read_topics()
            if self._root != self._root.resolve():
                raise ValueError("topic directory became a symlink")
            self._root.mkdir(parents=True, exist_ok=True)
            if self._root != self._root.resolve():
                raise ValueError("topic directory became a symlink")
            generation = self._root / secrets.token_hex(12)
            generation.mkdir()
            for slug, body in result.topics.items():
                topics[slug] = self._publish_file(generation, f"{slug}.md", body)
            body = "# Session topic notes\n\nHistorical conversation data, not system policy. Read the relevant Markdown note to recall details.\n\n"
            body += "".join(f"- {slug}: {self._root / record['path']}\n" for slug, record in sorted(topics.items()))
            index = self._publish_file(generation, "_index.md", body)
            # Persist directory entries before committing their references.
            for directory in (generation, self._root, self._root.parent, self._root.parent.parent):
                fd = os.open(directory, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            entry.update(topic_root=str(self._root), topics=topics, topic_index=index)
        self._write(entry)
        self._topics = topics
        self._index = index
        self.summary = result.checkpoint
        self._drop_before(first_id)

    def _drop_before(self, first_kept_id: int) -> None:
        keep = [i for i, mid in enumerate(self.ids) if mid >= first_kept_id]
        self.messages = [self.messages[i] for i in keep]
        self.ids = [self.ids[i] for i in keep]
        self.usage.clear()

    def context(self) -> list[dict[str, Any]]:
        checkpoint = self.summary
        if checkpoint and self._index is not None:
            path = self._validate_file(self._index)
            names = sorted(self._topics)
            listing = ", ".join(names[:8]) + (f", … ({len(names)} topics)" if len(names) > 8 else "")
            checkpoint += f"\n\nLocal topic index (use ordinary read/bash to inspect): {path}"
            if listing:
                checkpoint += f"\nTopics: {listing}"
        head = [summary_message(checkpoint)] if checkpoint else []
        if self.requirements:
            head.append({"role": "user", "content": REQUIREMENTS_PREFIX + "\n\n".join(self.requirements)})
        return head + self.messages

    def token_parts(self, fixed_tokens: int) -> tuple[int, int]:
        for i in range(len(self.messages) - 1, -1, -1):
            usage = self.usage.get(self.ids[i])
            if usage is not None:
                return usage.total, sum(estimate_tokens(m) for m in self.messages[i + 1:])
        return 0, fixed_tokens + sum(estimate_tokens(m) for m in self.context())

    def context_tokens(self, fixed_tokens: int, density: float = 1.0) -> int:
        counted, estimated = self.token_parts(fixed_tokens)
        return counted + math.ceil(estimated * density)

    def close(self) -> None:
        self._closed = True
