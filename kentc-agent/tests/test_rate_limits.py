from __future__ import annotations

import io
import json
import threading
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from email.message import Message

import pytest

from kentc_agent.adapters.llm import IncompleteReply, LLMClient, LLMError, ModelInfo, RateLimitError
from kentc_agent.adapters.rate_limit import RateLimitExceeded, RollingTokenBudget, retry_after
from kentc_agent.config import Settings


class Clock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def event(payload):
    return f"data: {json.dumps(payload)}\n\n".encode()


class Response:
    def __init__(self, chunks):
        self.chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __iter__(self):
        for chunk in self.chunks:
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk


def response(*, usage=None):
    chunks = [event({"choices": [{"delta": {"content": "answer"}, "finish_reason": "stop"}]})]
    if usage is not None:
        chunks.append(event({"choices": [], "usage": {"prompt_tokens": usage[0], "completion_tokens": usage[1]}}))
    return Response([*chunks, b"data: [DONE]\n\n"])


def http_error(code=429, after=None):
    headers = Message()
    if after is not None:
        headers["Retry-After"] = after
    return urllib.error.HTTPError("http://llm.example/chat/completions", code, "rejected", headers,
                                  io.BytesIO(b'{"error":{"message":"provider rejected request"}}'))


def client(clock, *outcomes, limit=0, max_wait=120, qwen=False):
    budget = RollingTokenBudget(limit, max_wait, clock=clock.monotonic, sleep=clock.sleep)
    settings = Settings(provider="qwen38" if qwen else "openai", base_url="http://primary.example",
                        api_key="primary-key", model="test-model", qwen_context_window=4000,
                        tokens_per_minute=limit, rate_limit_max_wait=max_wait)
    llm = LLMClient(settings, _rate_limit=budget)
    if not qwen:
        llm._info = ModelInfo("test-model", 4000, False)
    if not outcomes:
        return llm
    sent, it = [], iter(outcomes)

    def open_req(req, timeout):
        sent.append(clock.now)
        item = next(it, outcomes[-1])
        if isinstance(item, Exception):
            raise item
        return item() if callable(item) else item

    llm._open = open_req
    return llm, sent


MESSAGES = [{"role": "user", "content": ""}]


def test_rolling_admission_and_sixty_second_boundary():
    clock = Clock()
    budget = RollingTokenBudget(100, 120, clock=clock.monotonic, sleep=clock.sleep)
    budget.reserve(40, budget.new_wait())
    clock.now = 10
    budget.reserve(60, budget.new_wait())
    budget.reserve(50, budget.new_wait())
    assert (clock.sleeps, clock.now) == ([60], 70)

    clock2 = Clock()
    b2 = RollingTokenBudget(100, 0, clock=clock2.monotonic, sleep=clock2.sleep)
    b2.reserve(100, b2.new_wait())
    clock2.now = 59.999
    with pytest.raises(RateLimitExceeded, match="rate-limit wait"):
        b2.reserve(1, b2.new_wait())
    clock2.now = 60
    b2.reserve(100, b2.new_wait())
    assert clock2.sleeps == []


def test_concurrent_callers_and_network_lock_release():
    clock = Clock()
    budget = RollingTokenBudget(100, 0, clock=clock.monotonic, sleep=clock.sleep)
    barrier = threading.Barrier(2)

    def reserve():
        barrier.wait()
        try:
            budget.reserve(60, budget.new_wait())
            return "admitted"
        except RateLimitExceeded:
            return "limited"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: reserve(), range(2))) == ["admitted", "limited"]

    llm = client(Clock(), limit=200, max_wait=0)
    opened, release = threading.Event(), threading.Event()
    llm._open = lambda req, timeout: (opened.set(), release.wait(2), response())[2]
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(llm.chat, MESSAGES, max_tokens=100)
        try:
            assert opened.wait(2)
            with pytest.raises(RateLimitError, match="rate-limit wait"):
                llm.chat(MESSAGES, max_tokens=100)
        finally:
            release.set()
        assert first.result(timeout=2).content == "answer"


@pytest.mark.parametrize("first_outcome,fails,expected_sent,expected_sleeps", [
    (lambda: response(usage=(10, 10)), False, [0, 0], []),
    (lambda: response(usage=(100, 60)), False, [0, 60], [60]),
    (lambda: response(), False, [0, 60], [60]),
    (http_error(503), True, [0, 60], [60]),
])
def test_usage_reconciliation_and_conservative_reservations(first_outcome, fails, expected_sent, expected_sleeps):
    clock = Clock()
    llm, sent = client(clock, first_outcome, lambda: response(usage=(10, 10)), limit=200)
    if fails:
        with pytest.raises(LLMError, match="HTTP 503"):
            llm.chat(MESSAGES, max_tokens=100)
    else:
        assert llm.chat(MESSAGES, max_tokens=100).content == "answer"
    assert llm.chat(MESSAGES, max_tokens=100).content == "answer"
    assert (sent, clock.sleeps) == (expected_sent, expected_sleeps)


def test_request_larger_than_quota_and_keyboard_interrupt():
    clock = Clock()
    llm, sent = client(clock, response(), limit=100)
    with pytest.raises(RateLimitError, match="request reservation.*exceeds tokens_per_minute=100"):
        llm.chat(MESSAGES, max_tokens=100)
    assert sent == [] and clock.sleeps == []

    def interrupt(seconds):
        raise KeyboardInterrupt

    budget = RollingTokenBudget(100, 120, clock=clock.monotonic, sleep=interrupt)
    llm2 = LLMClient(Settings(model="test"), _rate_limit=budget)
    llm2._info = ModelInfo("test", 4000, False)
    budget.reserve(100, budget.new_wait())
    with pytest.raises(KeyboardInterrupt):
        llm2.chat(MESSAGES, max_tokens=10)


@pytest.mark.parametrize("after,expected", [("2.5", 2.5), ("Thu, 01 Jan 1970 00:00:07 GMT", 7)])
def test_http_429_honors_seconds_and_http_date_without_disabling_streaming(monkeypatch, after, expected):
    clock = Clock()
    monkeypatch.setattr("kentc_agent.adapters.rate_limit.time.time", lambda: 0)
    llm, sent = client(clock, http_error(after=after), response())
    deltas = []
    reply = llm.chat(MESSAGES, max_tokens=100, on_delta=lambda *d: deltas.append(d))
    assert (reply.content, sent, clock.sleeps, deltas) == ("answer", [0, expected], [expected], [("content", "answer")])
    assert retry_after("Thu, 01 Jan 1970 00:00:07 GMT", now=10) == 0


@pytest.mark.parametrize("after", [None, "not a date", "nan", "inf"])
def test_missing_or_invalid_retry_after_uses_bounded_backoff(after):
    clock = Clock()
    llm, sent = client(clock, http_error(after=after))
    with pytest.raises(RateLimitError, match="HTTP 429"):
        llm.chat(MESSAGES, max_tokens=100)
    assert (sent, clock.sleeps) == ([0, 1, 3], [1, 2])


def test_wait_allowance_cooldown_and_429_reservation_retention():
    clock = Clock()
    llm, sent = client(clock, http_error(after="3"), max_wait=5)
    with pytest.raises(RateLimitError, match="only 2.000s remains"):
        llm.chat(MESSAGES, max_tokens=100)
    assert (sent, clock.sleeps) == ([0, 3], [3])

    clock2 = Clock()
    llm2, sent2 = client(clock2, http_error(after="10"), response(), max_wait=0)
    for _ in range(2):
        with pytest.raises(RateLimitError, match="rate-limit wait"):
            llm2.chat(MESSAGES, max_tokens=100)
    assert sent2 == [0]
    clock2.now = 10
    assert llm2.chat(MESSAGES, max_tokens=100).content == "answer" and sent2 == [0, 10]

    clock3 = Clock()
    llm3, sent3 = client(clock3, http_error(after="1"), lambda: response(usage=(10, 10)),
                         lambda: response(usage=(10, 10)), limit=200)
    llm3.chat(MESSAGES, max_tokens=100)
    llm3.chat(MESSAGES, max_tokens=100)
    assert (sent3, clock3.sleeps) == ([0, 60, 60], [60])

    clock4 = Clock()
    llm4, sent4 = client(clock4, response(), http_error(after="2"), limit=1000, max_wait=61)
    llm4.chat(MESSAGES, max_tokens=900)
    with pytest.raises(RateLimitError, match="only 1.000s remains"):
        llm4.chat(MESSAGES, max_tokens=100)
    assert (sent4, clock4.sleeps) == ([0, 60], [60])


@pytest.fixture
def fallback_env(monkeypatch):
    monkeypatch.setenv("GATEWAY_URL", "http://backup.example")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "backup-key")
    monkeypatch.setenv("QWEN38_LITELLM_MODEL", "backup-model")


def test_qwen_fallback_shares_token_reservation_and_wait_budget(monkeypatch, fallback_env):
    clock = Clock()
    llm = client(clock, limit=200, qwen=True)
    sent = []

    def open_req(self, req, timeout):
        sent.append((self.settings.qwen_backend, clock.now))
        if self.settings.qwen_backend == "coordinator":
            raise http_error(503)
        if len(sent) == 2:
            raise http_error(after="2")
        return response()

    monkeypatch.setattr(LLMClient, "_open", open_req)
    assert llm.chat(MESSAGES, max_tokens=100).content == "answer"
    assert sent == [("coordinator", 0), ("litellm", 60), ("litellm", 120)]

    clock2 = Clock()
    llm2 = client(clock2, max_wait=5, qwen=True)
    sent2 = []
    monkeypatch.setattr(LLMClient, "_open", lambda self, req, timeout: (
        sent2.append((self.settings.qwen_backend, clock2.now)), (_ for _ in ()).throw(http_error(after="2"))))
    with pytest.raises(RateLimitError, match="only 1.000s remains"):
        llm2.chat(MESSAGES, max_tokens=100)
    assert (sent2, clock2.sleeps) == ([("coordinator", 0), ("coordinator", 2), ("coordinator", 4)], [2, 2])


@pytest.mark.parametrize("qwen", [False, True])
def test_streamed_rate_error_and_partial_stream_never_replay(qwen):
    clock = Clock()
    stream = Response([event({"choices": [{"delta": {"content": "partial"}}]}),
                       event({"error": {"code": 429, "message": "TPM exhausted"}})])
    llm, sent = client(clock, stream, qwen=qwen)
    deltas = []
    with pytest.raises(RateLimitError, match="after output began; automatic replay is unsafe"):
        llm.chat(MESSAGES, max_tokens=100, on_delta=lambda *d: deltas.append(d))
    assert (deltas, len(sent), clock.sleeps) == ([("content", "partial")], 1, [])


@pytest.mark.parametrize("ending", [b"data: [DONE]\n\n", b"data: invalid JSON\n\n", OSError("disconnected")])
def test_qwen_partial_stream_is_incomplete_even_when_done_is_present(ending):
    clock = Clock()
    llm, sent = client(clock, Response([event({"choices": [{"delta": {"content": '{"partial":'}}]}), ending]),
                       qwen=True)
    with pytest.raises(IncompleteReply, match="after output began; automatic replay is unsafe"):
        llm.chat(MESSAGES, max_tokens=100)
    assert len(sent) == 1


@pytest.mark.parametrize("usage", [
    {"prompt_tokens": 10},
    {"completion_tokens": 10},
    {"prompt_tokens": -10, "completion_tokens": 20},
])
def test_incomplete_usage_counters_cannot_release_reserved_prompt_tokens(usage):
    clock = Clock()
    chunk = Response([event({"choices": [{"delta": {"content": "answer"}, "finish_reason": "stop"}]}),
                      event({"choices": [], "usage": usage}), b"data: [DONE]\n\n"])
    llm, sent = client(clock, chunk, response(), limit=200)
    assert llm.chat(MESSAGES, max_tokens=100).usage is None
    llm.chat(MESSAGES, max_tokens=100)
    assert sent == [0, 60]
