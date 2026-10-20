"""OpenAI-compatible chat client (stdlib only, streaming SSE).

Connection and request policy are configuration; deployed context limits come only from server inspection.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..config import Settings

# kind is "reasoning" | "content" | "tool" (a tool call's name, once per call)
DeltaHandler = Callable[[str, str], None]


class LLMError(RuntimeError):
    pass


class ContextOverflow(LLMError):
    """The server refused the request: prompt + max_tokens does not fit its context window. The real numbers are
    read from the error when the server gives them (Strata, vLLM directly or behind LiteLLM, OpenAI, llama.cpp):
    `prompt_tokens` the prompt's real size, `window` the server's context, `fit` the largest max_tokens that fits."""

    PROMPT = (r"prompt \((\d+) tokens?\)", r"\((\d+) in the messages", r"has (\d+) input tokens",
              r"resulted in (\d+) tokens", r'"n_prompt_tokens":\s*(\d+)')
    WINDOW = (r"maximum context length is (\d+)", r"exceeds the context \((\d+)\)", r'"n_ctx":\s*(\d+)')

    def __init__(self, message: str, raw: str = "") -> None:
        super().__init__(message)
        text = f"{message}\n{raw}"

        def first(patterns: tuple[str, ...]) -> int | None:
            for p in patterns:
                m = re.search(p, text)
                if m:
                    return int(m.group(1))
            return None
        self.prompt_tokens, self.window = first(self.PROMPT), first(self.WINDOW)
        fit = re.search(r"at most (\d+)", text)
        self.fit: int | None = int(fit.group(1)) if fit else \
            self.window - self.prompt_tokens if self.window and self.prompt_tokens and \
            self.window > self.prompt_tokens else None

    @property
    def prompt_too_long(self) -> bool:
        """The prompt alone does not fit: a smaller reply cannot help, only compaction can."""
        return bool(self.window and self.prompt_tokens and self.prompt_tokens >= self.window)


OVERFLOW_MARKERS = ("context length", "context window", "context size", "maximum context", "exceeds the context",
                    "context_length_exceeded", "contextwindowexceeded")


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class Reply:
    content: str = ""
    reasoning: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish: str = ""
    usage: Usage | None = None

    def message(self) -> dict[str, Any]:
        """The assistant message to keep in the conversation."""
        msg: dict[str, Any] = {"role": "assistant", "content": self.content}
        if self.reasoning:
            msg["reasoning_content"] = self.reasoning
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        return msg


@dataclass(frozen=True)
class ModelInfo:
    id: str
    context_window: int
    vision: bool


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base = settings.base_url.rstrip("/")
        self._info: ModelInfo | None = None

    # ------------------------------------------------------------------ discovery
    def info(self, *, refresh: bool = False) -> ModelInfo:
        """Inspect the selected deployment; callers refresh at each run, then reuse its snapshot."""
        if refresh:
            self._info = None
        if self._info is None:
            data = self._get("/models").get("data") or []
            if not data:
                raise LLMError(f"{self.base}/models lists no loaded model")
            model = self.settings.model
            entry = next((m for m in data if m.get("id") == model), None) if model else data[0]
            if entry is None:
                raise LLMError(f"{self.base}/models does not report the selected model {model!r}")
            model = entry["id"]
            raw = (entry.get("meta") or {}).get("n_ctx")
            if raw is None:
                raw = entry.get("max_model_len")
            if isinstance(raw, bool) or not isinstance(raw, (int, str)) or not str(raw).isdigit() or int(raw) <= 0:
                raise LLMError(
                    f"{self.base}/models must report a positive deployed context limit "
                    f"(meta.n_ctx or max_model_len) for {model!r}; no config override or default is used"
                )
            modalities = (entry.get("architecture") or {}).get("input_modalities")
            vision = True if modalities is None else "image" in modalities
            self._info = ModelInfo(id=model, context_window=int(raw), vision=vision)
        return self._info

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.settings.api_key:
            h["Authorization"] = f"Bearer {self.settings.api_key}"
        return h

    def _get(self, path: str) -> dict[str, Any]:
        req = urllib.request.Request(self.base + path, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
            raise LLMError(f"cannot reach the LLM server at {self.base}: {e}. Is it running?") from None

    # ------------------------------------------------------------------ chat
    def chat(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None,
             max_tokens: int, effort: str | None = None, on_delta: DeltaHandler | None = None) -> Reply:
        s = self.settings
        body: dict[str, Any] = {
            "model": self.info().id,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            body["tools"] = tools
        effort = effort if effort is not None else s.reasoning_effort
        if effort:
            body["reasoning_effort"] = effort
        if s.temperature is not None:
            body["temperature"] = s.temperature
        data = json.dumps(body, ensure_ascii=False).encode()
        for attempt in range(3):
            req = urllib.request.Request(self.base + "/chat/completions", data=data, headers=self._headers())
            try:
                resp = urllib.request.urlopen(req, timeout=s.request_timeout)
            except urllib.error.HTTPError as e:
                raise self._http_error(e) from None
            except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
                if attempt == 2:
                    raise LLMError(f"cannot reach the LLM server at {self.base}: {e}") from None
                time.sleep(2 * (attempt + 1))
                continue
            with resp:
                return self._read_stream(resp, on_delta)
        raise AssertionError("unreachable")

    @staticmethod
    def _http_error(e: urllib.error.HTTPError) -> LLMError:
        raw = e.read().decode("utf-8", "replace")
        try:
            msg = json.loads(raw)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            msg = raw[:500]
        if e.code in (400, 413) and any(k in raw.lower() for k in OVERFLOW_MARKERS):
            return ContextOverflow(msg, raw)
        return LLMError(f"HTTP {e.code}: {msg}")

    @staticmethod
    def _read_stream(resp: Any, on_delta: DeltaHandler | None) -> Reply:
        reply = Reply()
        content: list[str] = []
        reasoning: list[str] = []
        calls: dict[int, dict[str, Any]] = {}
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue                                # blank lines and ": keep-alive" comments
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            chunk = json.loads(payload)
            if chunk.get("error"):
                raise LLMError(str(chunk["error"].get("message", chunk["error"])))
            if chunk.get("usage"):
                u = chunk["usage"]
                reply.usage = Usage(int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0))
            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                if delta.get("reasoning_content"):
                    reasoning.append(delta["reasoning_content"])
                    if on_delta:
                        on_delta("reasoning", delta["reasoning_content"])
                if delta.get("content"):
                    content.append(delta["content"])
                    if on_delta:
                        on_delta("content", delta["content"])
                for tc in delta.get("tool_calls") or []:
                    i = tc.get("index", len(calls))
                    cur = calls.setdefault(i, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                    cur["id"] = tc.get("id") or cur["id"]
                    fn = tc.get("function") or {}
                    if fn.get("name"):
                        cur["function"]["name"] += fn["name"]
                        if on_delta:
                            on_delta("tool", fn["name"])
                    if fn.get("arguments"):
                        cur["function"]["arguments"] += fn["arguments"]
                if choice.get("finish_reason"):
                    reply.finish = choice["finish_reason"]
        reply.content = "".join(content).strip()
        reply.reasoning = "".join(reasoning).strip()
        for n, i in enumerate(sorted(calls)):
            call = calls[i]
            call["id"] = call["id"] or f"call_{int(time.time() * 1000)}_{n}"
            reply.tool_calls.append(call)
        return reply
