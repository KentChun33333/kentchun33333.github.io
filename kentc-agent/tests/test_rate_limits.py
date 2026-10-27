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


def client(clock, *, limit=0, max_wait=120, qwen=False):
    budget = RollingTokenBudget(limit, max_wait, clock=clock.monotonic, sleep=clock.sleep)
    settings = Settings(provider="qwen38" if qwen else "openai", base_url="http://primary.example",
                        api_key="primary-key", model="test-model", qwen_context_window=4000,
                        tokens_per_minute=limit, rate_limit_max_wait=max_wait)
    result = LLMClient(settings, _rate_limit=budget)
    if not qwen:
        result._info = ModelInfo("test-model", 4000, False)
    return result


MESSAGES = [{"role": "user", "content": ""}]


def test_rolling_admission_waits_only_until_enough_reservations_expire():
    clock = Clock()
    budget = RollingTokenBudget(100, 120, clock=clock.monotonic, sleep=clock.sleep)
    budget.reserve(40, budget.new_wait())
    clock.now = 10
    budget.reserve(60, budget.new_wait())
    budget.reserve(50, budget.new_wait())
    assert clock.sleeps == [60]
    assert clock.now == 70


def test_reservations_expire_at_the_sixty_second_boundary():
    clock = Clock()
    budget = RollingTokenBudget(100, 0, clock=clock.monotonic, sleep=clock.sleep)
    budget.reserve(100, budget.new_wait())
    clock.now = 59.999
    with pytest.raises(RateLimitExceeded, match="rate-limit wait"):
        budget.reserve(1, budget.new_wait())
    clock.now = 60
    budget.reserve(100, budget.new_wait())
    assert clock.sleeps == []


def test_concurrent_callers_cannot_overbook_the_shared_window():
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
        results = list(pool.map(lambda _: reserve(), range(2)))
    assert sorted(results) == ["admitted", "limited"]


def test_successful_usage_releases_only_the_unused_reservation():
    clock = Clock()
    llm = client(clock, limit=200)
    sent = []

    def open_request(req, timeout):
        sent.append(clock.now)
        return response(usage=(10, 10))

    llm._open = open_request
    assert llm.chat(MESSAGES, max_tokens=100).content == "answer"
    assert llm.chat(MESSAGES, max_tokens=100).content == "answer"
    assert sent == [0, 0]
    assert clock.sleeps == []


def test_reported_usage_above_the_estimate_blocks_later_calls():
    clock = Clock()
    llm = client(clock, limit=200)
    sent = []

    def open_request(req, timeout):
        sent.append(clock.now)
        return response(usage=(100, 60))

    llm._open = open_request
    llm.chat(MESSAGES, max_tokens=100)
    llm.chat(MESSAGES, max_tokens=100)
    assert sent == [0, 60]


@pytest.mark.parametrize("failed", [False, True])
def test_missing_usage_or_failed_request_keeps_its_conservative_reservation(failed):
    clock = Clock()
    llm = client(clock, limit=200)
    sent = []

    def open_request(req, timeout):
        sent.append(clock.now)
        if failed and len(sent) == 1:
            raise http_error(503)
        return response()

    llm._open = open_request
    if failed:
        with pytest.raises(LLMError, match="HTTP 503"):
            llm.chat(MESSAGES, max_tokens=100)
    else:
        llm.chat(MESSAGES, max_tokens=100)
    llm.chat(MESSAGES, max_tokens=100)
    assert sent == [0, 60]
    assert clock.sleeps == [60]


def test_request_larger_than_quota_fails_before_http():
    clock = Clock()
    llm = client(clock, limit=100)
    sent = []
    llm._open = lambda req, timeout: sent.append(req)
    with pytest.raises(RateLimitError, match="request reservation.*exceeds tokens_per_minute=100"):
        llm.chat(MESSAGES, max_tokens=100)
    assert sent == []
    assert clock.sleeps == []


def test_a_network_call_does_not_hold_the_admission_lock():
    clock = Clock()
    llm = client(clock, limit=200, max_wait=0)
    opened = threading.Event()
    release = threading.Event()
    sent = []

    def open_request(req, timeout):
        sent.append(req)
        opened.set()
        assert release.wait(2)
        return response()

    llm._open = open_request
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(llm.chat, MESSAGES, max_tokens=100)
        try:
            assert opened.wait(2)
            with pytest.raises(RateLimitError, match="rate-limit wait"):
                llm.chat(MESSAGES, max_tokens=100)
        finally:
            release.set()
        assert first.result(timeout=2).content == "answer"
    assert len(sent) == 1


@pytest.mark.parametrize("after,expected", [("2.5", 2.5), ("Thu, 01 Jan 1970 00:00:07 GMT", 7)])
def test_http_429_honors_seconds_and_http_date_without_disabling_streaming(monkeypatch, after, expected):
    clock = Clock()
    monkeypatch.setattr("kentc_agent.adapters.rate_limit.time.time", lambda: 0)
    llm = client(clock)
    sent = []
    deltas = []

    def open_request(req, timeout):
        body = json.loads(req.data)
        assert body["stream"] is True
        sent.append(clock.now)
        if len(sent) == 1:
            raise http_error(after=after)
        return response()

    llm._open = open_request
    reply = llm.chat(MESSAGES, max_tokens=100, on_delta=lambda *delta: deltas.append(delta))
    assert reply.content == "answer"
    assert sent == [0, expected]
    assert clock.sleeps == [expected]
    assert deltas == [("content", "answer")]


@pytest.mark.parametrize("after", [None, "not a date", "nan", "inf"])
def test_missing_or_invalid_retry_after_uses_bounded_backoff(after):
    clock = Clock()
    llm = client(clock)
    sent = []

    def open_request(req, timeout):
        sent.append(clock.now)
        raise http_error(after=after)

    llm._open = open_request
    with pytest.raises(RateLimitError, match="HTTP 429"):
        llm.chat(MESSAGES, max_tokens=100)
    assert sent == [0, 1, 3]
    assert clock.sleeps == [1, 2]


def test_retry_after_exhaustion_uses_one_total_wait_allowance():
    clock = Clock()
    llm = client(clock, max_wait=5)
    sent = []

    def open_request(req, timeout):
        sent.append(clock.now)
        raise http_error(after="3")

    llm._open = open_request
    with pytest.raises(RateLimitError, match="only 2.000s remains"):
        llm.chat(MESSAGES, max_tokens=100)
    assert sent == [0, 3]
    assert clock.sleeps == [3]


def test_provider_cooldown_is_shared_with_other_calls_even_without_local_quota():
    clock = Clock()
    llm = client(clock, max_wait=0)
    sent = []

    def open_request(req, timeout):
        sent.append(clock.now)
        if len(sent) == 1:
            raise http_error(after="10")
        return response()

    llm._open = open_request
    with pytest.raises(RateLimitError, match="rate-limit wait"):
        llm.chat(MESSAGES, max_tokens=100)
    with pytest.raises(RateLimitError, match="rate-limit wait"):
        llm.chat(MESSAGES, max_tokens=100)
    assert sent == [0]
    clock.now = 10
    assert llm.chat(MESSAGES, max_tokens=100).content == "answer"
    assert sent == [0, 10]


def test_keyboard_interrupt_during_admission_wait_is_not_retried():
    clock = Clock()

    def interrupt(seconds):
        raise KeyboardInterrupt

    budget = RollingTokenBudget(100, 120, clock=clock.monotonic, sleep=interrupt)
    llm = LLMClient(Settings(model="test"), _rate_limit=budget)
    llm._info = ModelInfo("test", 4000, False)
    budget.reserve(100, budget.new_wait())
    sent = []
    llm._open = lambda req, timeout: sent.append(req)
    with pytest.raises(KeyboardInterrupt):
        llm.chat(MESSAGES, max_tokens=10)
    assert sent == []


@pytest.fixture
def fallback_env(monkeypatch):
    monkeypatch.setenv("GATEWAY_URL", "http://backup.example")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "backup-key")
    monkeypatch.setenv("QWEN38_LITELLM_MODEL", "backup-model")


def test_qwen_fallback_uses_the_primary_conservative_token_reservation(monkeypatch, fallback_env):
    clock = Clock()
    llm = client(clock, limit=200, qwen=True)
    sent = []

    def open_request(self, req, timeout):
        sent.append((self.settings.qwen_backend, clock.now))
        if self.settings.qwen_backend == "coordinator":
            raise http_error(503)
        return response()

    monkeypatch.setattr(LLMClient, "_open", open_request)
    assert llm.chat(MESSAGES, max_tokens=100).content == "answer"
    assert sent == [("coordinator", 0), ("litellm", 60)]


def test_qwen_fallback_does_not_reset_the_total_rate_wait(monkeypatch, fallback_env):
    clock = Clock()
    llm = client(clock, max_wait=5, qwen=True)
    sent = []

    def open_request(self, req, timeout):
        sent.append((self.settings.qwen_backend, clock.now))
        raise http_error(after="2")

    monkeypatch.setattr(LLMClient, "_open", open_request)
    with pytest.raises(RateLimitError, match="only 1.000s remains"):
        llm.chat(MESSAGES, max_tokens=100)
    assert sent == [("coordinator", 0), ("coordinator", 2), ("coordinator", 4)]
    assert clock.sleeps == [2, 2]


def test_qwen_backup_can_retry_429_before_its_first_chunk(monkeypatch, fallback_env):
    clock = Clock()
    llm = client(clock, qwen=True)
    sent = []

    def open_request(self, req, timeout):
        sent.append((self.settings.qwen_backend, clock.now))
        if self.settings.qwen_backend == "coordinator":
            raise http_error(503)
        if len(sent) == 2:
            raise http_error(after="2")
        return response()

    monkeypatch.setattr(LLMClient, "_open", open_request)
    assert llm.chat(MESSAGES, max_tokens=100).content == "answer"
    assert sent == [("coordinator", 0), ("litellm", 0), ("litellm", 2)]


@pytest.mark.parametrize("qwen", [False, True])
def test_streamed_rate_error_after_a_chunk_never_replays_or_fails_over(qwen):
    clock = Clock()
    llm = client(clock, qwen=qwen)
    sent = []
    deltas = []

    def open_request(req, timeout):
        sent.append(req)
        return Response([event({"choices": [{"delta": {"content": "partial"}}]}),
                         event({"error": {"code": 429, "message": "TPM exhausted"}})])

    llm._open = open_request
    with pytest.raises(RateLimitError, match="after output began; automatic replay is unsafe"):
        llm.chat(MESSAGES, max_tokens=100, on_delta=lambda *delta: deltas.append(delta))
    assert deltas == [("content", "partial")]
    assert len(sent) == 1
    assert clock.sleeps == []


@pytest.mark.parametrize("ending", [b"data: [DONE]\n\n", b"data: invalid JSON\n\n", OSError("disconnected")])
def test_qwen_partial_stream_is_incomplete_even_when_done_is_present(ending):
    clock = Clock()
    llm = client(clock, qwen=True)
    sent = []

    def open_request(req, timeout):
        sent.append(req)
        return Response([event({"choices": [{"delta": {"content": '{"partial":'}}]}), ending])

    llm._open = open_request
    with pytest.raises(IncompleteReply, match="after output began; automatic replay is unsafe"):
        llm.chat(MESSAGES, max_tokens=100)
    assert len(sent) == 1


def test_retry_after_past_dates_do_not_add_delay():
    assert retry_after("Thu, 01 Jan 1970 00:00:07 GMT", now=10) == 0


@pytest.mark.parametrize("usage", [
    {"prompt_tokens": 10},
    {"completion_tokens": 10},
    {"prompt_tokens": -10, "completion_tokens": 20},
])
def test_incomplete_usage_counters_cannot_release_reserved_prompt_tokens(usage):
    clock = Clock()
    llm = client(clock, limit=200)
    sent = []

    def open_request(req, timeout):
        sent.append(clock.now)
        return Response([
            event({"choices": [{"delta": {"content": "answer"}, "finish_reason": "stop"}]}),
            event({"choices": [], "usage": usage}),
            b"data: [DONE]\n\n",
        ])

    llm._open = open_request
    assert llm.chat(MESSAGES, max_tokens=100).usage is None
    llm.chat(MESSAGES, max_tokens=100)
    assert sent == [0, 60]


def test_429_does_not_immediately_refund_its_unknown_request_charge():
    clock = Clock()
    llm = client(clock, limit=200)
    sent = []

    def open_request(req, timeout):
        sent.append(clock.now)
        if len(sent) == 1:
            raise http_error(after="1")
        return response(usage=(10, 10))

    llm._open = open_request
    llm.chat(MESSAGES, max_tokens=100)
    llm.chat(MESSAGES, max_tokens=100)
    assert sent == [0, 60, 60]
    assert clock.sleeps == [60]


def test_admission_and_429_waits_share_one_allowance():
    clock = Clock()
    llm = client(clock, limit=1000, max_wait=61)
    sent = []

    def open_request(req, timeout):
        sent.append(clock.now)
        if len(sent) == 1:
            return response()
        raise http_error(after="2")

    llm._open = open_request
    llm.chat(MESSAGES, max_tokens=900)
    with pytest.raises(RateLimitError, match="only 1.000s remains"):
        llm.chat(MESSAGES, max_tokens=100)
    assert sent == [0, 60]
    assert clock.sleeps == [60]
