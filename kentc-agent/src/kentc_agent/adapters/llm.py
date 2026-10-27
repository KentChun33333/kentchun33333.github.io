"""OpenAI-compatible chat client (stdlib only, streaming SSE).

Connection and request policy are configuration. OpenAI deployments are inspected; Qwen38
coordinators use an explicitly configured deployed limit when discovery is unavailable.
"""

from __future__ import annotations

import http.client
import json
import logging
import re
import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..config import Settings
from .qwen38 import connection, fallback_settings, normalise_messages
from .rate_limit import RateLimitExceeded, RateWait, RollingTokenBudget, retry_after

# kind is "reasoning" | "content" | "tool" (a tool call's name, once per call)
DeltaHandler = Callable[[str, str], None]


class LLMError(RuntimeError):
    pass


class IncompleteReply(LLMError):
    """A streamed reply is incomplete and must not be accepted as conversation evidence."""


class RateLimitError(LLMError):
    """Provider throttling or exhausted local admission/wait allowance."""

    def __init__(self, message: str, *, retry_after: float | None = None, local: bool = False) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.local = local


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
    def __init__(self, settings: Settings, *, _rate_limit: RollingTokenBudget | None = None) -> None:
        if settings.provider not in ("openai", "qwen38"):
            raise LLMError("provider must be openai or qwen38")
        try:
            self.settings = connection(settings) if settings.provider == "qwen38" else settings
            self._rate_limit = _rate_limit or RollingTokenBudget(settings.tokens_per_minute,
                                                                settings.rate_limit_max_wait)
        except ValueError as e:
            raise LLMError(str(e)) from None
        self.base = self.settings.base_url.rstrip("/")
        self._info: ModelInfo | None = None
        self._opener = None
        if not settings.verify_tls or not settings.trust_env:
            context = ssl.create_default_context() if settings.verify_tls else ssl._create_unverified_context()
            handlers: list[Any] = [urllib.request.HTTPSHandler(context=context)]
            if not settings.trust_env:
                handlers.append(urllib.request.ProxyHandler({}))
            self._opener = urllib.request.build_opener(*handlers)

    # ------------------------------------------------------------------ discovery
    def info(self, *, refresh: bool = False) -> ModelInfo:
        """Refresh deployment metadata, or the explicit Qwen38 capability configuration."""
        if refresh:
            self._info = None
        if self._info is None:
            if self.settings.provider == "qwen38":
                self._info = ModelInfo(self.settings.model, self.settings.qwen_context_window,
                                       self.settings.qwen_vision)
                return self._info
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

    def _open(self, request: urllib.request.Request, timeout: float) -> Any:
        if self._opener is not None:
            return self._opener.open(request, timeout=timeout)
        return urllib.request.urlopen(request, timeout=timeout)

    def _get(self, path: str) -> dict[str, Any]:
        req = urllib.request.Request(self.base + path, headers=self._headers())
        try:
            with self._open(req, timeout=10) as resp:
                return json.loads(resp.read())
        except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
            raise LLMError(f"cannot reach the LLM server at {self.base}: {e}. Is it running?") from None

    # ------------------------------------------------------------------ chat
    def chat(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None,
             max_tokens: int, effort: str | None = None, on_delta: DeltaHandler | None = None) -> Reply:
        if self.settings.provider != "qwen38":
            waiting = self._rate_limit.new_wait()
            return self._chat(messages, tools=tools, max_tokens=max_tokens, effort=effort, on_delta=on_delta,
                              waiting=waiting)
        try:
            messages = normalise_messages(messages)
        except ValueError as e:
            raise LLMError(str(e)) from None
        started = False
        waiting = self._rate_limit.new_wait()

        def mark_started() -> None:
            nonlocal started
            started = True

        try:
            return self._chat(messages, tools=tools, max_tokens=max_tokens, effort=effort, on_delta=on_delta,
                              on_chunk=mark_started, waiting=waiting)
        except ContextOverflow:
            raise                       # the agent adjusts its budget; switching is not a context fix
        except (LLMError, OSError, http.client.HTTPException, ValueError) as e:
            if isinstance(e, RateLimitError) and (e.local or started):
                raise
            if isinstance(e, IncompleteReply) and started:
                raise
            if started:
                raise LLMError(f"{self.settings.qwen_backend} stream failed after output began; "
                               "automatic replay is unsafe") from e
            primary_error = e
        try:
            backup = LLMClient(fallback_settings(self.settings), _rate_limit=self._rate_limit)
        except LLMError as e:
            if isinstance(primary_error, RateLimitError):
                raise RateLimitError(f"{self.settings.qwen_backend} was rate limited ({primary_error}); "
                                     f"Qwen38 fallback is unavailable: {e}",
                                     retry_after=primary_error.retry_after) from e
            raise LLMError(f"{self.settings.qwen_backend} failed ({primary_error}); "
                           f"Qwen38 fallback is unavailable: {e}") from e
        logging.warning("Qwen38 %s failed before output; failing over to %s",
                        self.settings.qwen_backend, backup.settings.qwen_backend)
        try:
            return backup._chat(messages, tools=tools, max_tokens=max_tokens, effort=effort, on_delta=on_delta,
                                on_chunk=mark_started, attempts=1, waiting=waiting)
        except ContextOverflow:
            raise
        except (LLMError, OSError, http.client.HTTPException, ValueError) as e:
            if isinstance(e, IncompleteReply) and started:
                raise
            if isinstance(e, RateLimitError):
                raise
            detail = "stream failed after output began; automatic replay is unsafe" if started else "failed"
            raise LLMError(f"{backup.settings.qwen_backend} fallback {detail}: {e}") from e

    def _chat(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None,
              max_tokens: int, effort: str | None, on_delta: DeltaHandler | None,
              on_chunk: Callable[[], None] | None = None, attempts: int = 3,
              waiting: RateWait | None = None) -> Reply:
        s = self.settings
        body: dict[str, Any] = {
            "model": self.info().id,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if s.provider == "qwen38":
            body.pop("stream_options")
        if tools:
            body["tools"] = tools
        effort = effort if effort is not None else s.reasoning_effort
        if effort and s.provider != "qwen38":
            body["reasoning_effort"] = effort
        if s.temperature is not None:
            body["temperature"] = s.temperature
        data = json.dumps(body, ensure_ascii=False).encode()
        reserved_tokens = 0
        if self._rate_limit.limit:
            # Session imports Usage, so reuse its estimator only after module initialization.
            from .session import estimate_tokens

            reserved_tokens = max_tokens + sum(estimate_tokens(message) for message in messages)
            if tools:
                reserved_tokens += estimate_tokens({"content": json.dumps(tools, ensure_ascii=False)})
        waiting = waiting or self._rate_limit.new_wait()
        network_failures = rate_retries = 0
        started = False

        def mark_started() -> None:
            nonlocal started
            started = True
            if on_chunk:
                on_chunk()

        while True:
            try:
                reservation = self._rate_limit.reserve(reserved_tokens, waiting)
            except RateLimitExceeded as e:
                raise RateLimitError(str(e), local=True) from None
            req = urllib.request.Request(self.base + "/chat/completions", data=data, headers=self._headers())
            try:
                resp = self._open(req, timeout=s.request_timeout)
            except urllib.error.HTTPError as e:
                error = self._http_error(e)
                if not isinstance(error, RateLimitError):
                    raise error from None
            except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
                network_failures += 1
                if network_failures >= attempts:
                    raise LLMError(f"cannot reach the LLM server at {self.base}: {e}") from None
                time.sleep(2 * network_failures)
                continue
            else:
                try:
                    with resp:
                        reply = self._read_stream(resp, on_delta, on_chunk=mark_started,
                                                  require_complete=s.provider == "qwen38")
                except RateLimitError as e:
                    error = e
                except (OSError, http.client.HTTPException, ValueError) as e:
                    if started:
                        raise IncompleteReply("stream failed after output began; automatic replay is unsafe") from e
                    raise LLMError(f"stream failed before output began: {e}") from e
                except IncompleteReply as e:
                    if started:
                        raise IncompleteReply("stream failed after output began; automatic replay is unsafe: "
                                              f"{e}") from e
                    raise
                else:
                    if reply.usage is not None and reply.usage.total >= 0:
                        self._rate_limit.reconcile(reservation, reply.usage.total)
                    return reply
            delay = error.retry_after if error.retry_after is not None else min(30.0, 2.0 ** rate_retries)
            self._rate_limit.defer(delay)
            if started:
                raise RateLimitError(f"rate limited after output began; automatic replay is unsafe: {error}",
                                     retry_after=error.retry_after) from error
            if rate_retries >= 2:
                raise error
            rate_retries += 1

    @staticmethod
    def _http_error(e: urllib.error.HTTPError) -> LLMError:
        raw = e.read().decode("utf-8", "replace")
        try:
            msg = json.loads(raw)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            msg = raw[:500]
        if e.code in (400, 413) and any(k in raw.lower() for k in OVERFLOW_MARKERS):
            return ContextOverflow(msg, raw)
        if e.code == 429:
            return RateLimitError(f"HTTP 429: {msg}", retry_after=retry_after((e.headers or {}).get("Retry-After")))
        return LLMError(f"HTTP {e.code}: {msg}")

    @staticmethod
    def _read_stream(resp: Any, on_delta: DeltaHandler | None, *,
                     on_chunk: Callable[[], None] | None = None, require_complete: bool = False) -> Reply:
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
            if not isinstance(chunk, dict):
                raise IncompleteReply("stream event must be a JSON object")
            if chunk.get("error"):
                error = chunk["error"]
                message = str(error.get("message", error))
                if str(error.get("code", "")).lower() in ("429", "rate_limit_exceeded") or \
                        error.get("type") == "rate_limit_exceeded":
                    raise RateLimitError(message)
                raise LLMError(message)
            if on_chunk:
                on_chunk()
            u = chunk.get("usage")
            if isinstance(u, dict) and all(
                isinstance(u.get(key), int) and not isinstance(u[key], bool) and u[key] >= 0
                for key in ("prompt_tokens", "completion_tokens")
            ):
                reply.usage = Usage(u["prompt_tokens"], u["completion_tokens"])
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
        if require_complete and not reply.finish:
            raise IncompleteReply("stream ended before a finish reason")
        reply.content = "".join(content).strip()
        reply.reasoning = "".join(reasoning).strip()
        for n, i in enumerate(sorted(calls)):
            call = calls[i]
            call["id"] = call["id"] or f"call_{int(time.time() * 1000)}_{n}"
            reply.tool_calls.append(call)
        return reply
