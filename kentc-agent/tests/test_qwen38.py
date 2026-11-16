from __future__ import annotations

import io
import json
import urllib.error
from email.message import Message

import pytest

from kentc_agent.adapters.llm import ContextOverflow, LLMClient, LLMError
from kentc_agent.config import Settings


def sse(*chunks: dict, done: bool = True) -> io.BytesIO:
    lines = [f"data: {json.dumps(c)}\n\n".encode() for c in chunks]
    if done:
        lines.append(b"data: [DONE]\n\n")
    return io.BytesIO(b"".join(lines))


def http_err(code: int, body: dict) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://qwen.example", code, "err", Message(), io.BytesIO(json.dumps(body).encode()))


def test_coordinator_without_discovery_streams_executable_tool_call():
    client = LLMClient(Settings(provider="qwen38", base_url="http://coord.example", api_key="test-key",
                                qwen_context_window=8192, trust_env=False))

    def open_req(req, timeout):
        body = json.loads(req.data)
        msgs = body["messages"]
        assert req.full_url == "http://coord.example/chat/completions"
        assert req.headers.get("Authorization") == "Bearer test-key"
        assert msgs[0] == {"role": "system", "content": "first\n\nsecond"}
        assert [m["role"] for m in msgs] == ["system", "user"]
        assert not ({"reasoning_effort", "stream_options"} & body.keys())
        if body["max_tokens"] > 8192:
            raise http_err(400, {"error": {"message": "maximum context length is 8192 tokens, resulted in 9000 tokens"}})
        return sse(
            {"choices": [{"delta": {"reasoning_content": "inspect source"}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "read-1", "type": "function",
                                                    "function": {"name": "read", "arguments": '{"path":'}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '"evidence.txt"}'}}]},
                          "finish_reason": "tool_calls"}]},
            {"choices": [], "usage": {"prompt_tokens": 43, "completion_tokens": 12}},
        )

    client._open = open_req
    messages = [{"role": "system", "content": "first"}, {"role": "user", "content": "Read evidence"},
                {"role": "system", "content": "second"}]
    reply = client.chat(messages, max_tokens=1024, effort="low")
    assert reply.tool_calls == [{"id": "read-1", "type": "function",
                                 "function": {"name": "read", "arguments": '{"path":"evidence.txt"}'}}]
    assert (reply.reasoning, reply.finish, reply.usage.total) == ("inspect source", "tool_calls", 55)
    assert len(messages) == 3 and messages[-1]["content"] == "second"
    with pytest.raises(ContextOverflow) as exc:
        client.chat(messages, max_tokens=9000)
    assert exc.value.window == 8192 and exc.value.prompt_too_long


@pytest.mark.parametrize("backend,endpoint_var,key_var,model_var,expected_path", [
    ("coordinator", "QWEN38_COORDINATOR_ENDPOINT", "VLM_API_KEY", "QWEN38_COORDINATOR_MODEL", ""),
    ("litellm", "GATEWAY_URL", "LITELLM_MASTER_KEY", "QWEN38_LITELLM_MODEL", "/v1"),
])
def test_selected_environment_credentials_never_fall_back(monkeypatch, backend, endpoint_var, key_var,
                                                          model_var, expected_path):
    for k in ("VLM_API_KEY", "LITELLM_MASTER_KEY", "QWEN38_COORDINATOR_ENDPOINT", "GATEWAY_URL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv(endpoint_var, "https://selected.example/")
    monkeypatch.setenv(model_var, "selected-model")
    monkeypatch.setenv("LITELLM_MASTER_KEY" if backend == "coordinator" else "VLM_API_KEY", "wrong-environment-key")
    settings = Settings(provider="qwen38", qwen_backend=backend, qwen_context_window=16384)
    with pytest.raises(LLMError):
        LLMClient(settings)
    monkeypatch.setenv(key_var, "selected-key")
    client = LLMClient(settings)
    assert client.base == "https://selected.example" + expected_path
    assert client._headers()["Authorization"] == "Bearer selected-key"
    assert (client.info().id, client.info().context_window, client.info().vision) == ("selected-model", 16384, False)


@pytest.mark.parametrize("window", [0, -1, True])
def test_qwen_rejects_invalid_deployment_limit_and_missing_user_query(window):
    with pytest.raises(LLMError, match="verified deployed token limit"):
        LLMClient(Settings(provider="qwen38", qwen_context_window=window))
    client = LLMClient(Settings(provider="qwen38", base_url="http://127.0.0.1:1", api_key="test-key",
                                qwen_context_window=8192))
    with pytest.raises(LLMError, match="user query"):
        client.chat([{"role": "system", "content": "instructions"}], max_tokens=100)


@pytest.fixture
def qwen_backends(monkeypatch):
    state = {"modes": {"coordinator": "success", "litellm": "success"}, "requests": []}
    for k, v in (("QWEN38_COORDINATOR_ENDPOINT", "http://qwen.local/coordinator"), ("GATEWAY_URL", "http://qwen.local"),
                 ("VLM_API_KEY", "coordinator-key"), ("QWEN38_COORDINATOR_MODEL", "coordinator-model"),
                 ("LITELLM_MASTER_KEY", "litellm-key"), ("QWEN38_LITELLM_MODEL", "litellm-model")):
        monkeypatch.setenv(k, v)

    def open_req(self, req, timeout):
        body = json.loads(req.data)
        backend = "litellm" if "/v1/" in req.full_url else "coordinator"
        auth = req.headers.get("Authorization")
        state["requests"].append((backend, auth, body["model"]))
        mode = state["modes"][backend]
        if mode == "unavailable":
            raise http_err(503, {"error": {"message": "Backend unavailable"}})
        if auth != f"Bearer {backend}-key" or body["model"] != f"{backend}-model":
            raise http_err(401, {"error": {"message": "Wrong backend credential or model"}})
        if mode == "overflow":
            raise http_err(400, {"error": {"message": "maximum context length is 8192 tokens; resulted in 9000 tokens"}})
        if mode == "empty":
            return sse(done=False)
        if mode == "stream_error":
            return sse({"error": {"message": "Backend unavailable"}}, done=False)
        delta = {"success": {"content": f"Answer from {backend}"}, "content": {"content": "partial answer"},
                 "reasoning": {"reasoning_content": "partial reasoning"}, "role": {"role": "assistant"},
                 "tool": {"tool_calls": [{"index": 0, "id": "partial", "function": {"name": "read"}}]}} [mode]
        choice = {"delta": delta, **({"finish_reason": "stop"} if mode == "success" else {})}
        return sse({"choices": [choice]}, done=(mode == "success"))

    monkeypatch.setattr(LLMClient, "_open", open_req)
    return state


@pytest.mark.parametrize("primary", ["coordinator", "litellm"])
@pytest.mark.parametrize("mode", ["unavailable", "stream_error", "empty"])
def test_qwen_fails_over_before_any_chunk_with_backup_credentials(qwen_backends, primary, mode):
    backup = "litellm" if primary == "coordinator" else "coordinator"
    qwen_backends["modes"][primary] = mode
    client = LLMClient(Settings(provider="qwen38", qwen_backend=primary, qwen_context_window=8192, trust_env=False))
    deltas = []
    reply = client.chat([{"role": "user", "content": "Answer"}], max_tokens=512,
                        on_delta=lambda k, t: deltas.append((k, t)))
    assert reply.content == f"Answer from {backup}" and deltas == [("content", f"Answer from {backup}")]
    assert qwen_backends["requests"] == [(primary, f"Bearer {primary}-key", f"{primary}-model"),
                                         (backup, f"Bearer {backup}-key", f"{backup}-model")]


@pytest.mark.parametrize("mode", ["content", "reasoning", "tool", "role"])
def test_qwen_never_replays_after_any_streamed_chunk(qwen_backends, mode):
    qwen_backends["modes"]["coordinator"] = mode
    client = LLMClient(Settings(provider="qwen38", qwen_context_window=8192, trust_env=False))
    with pytest.raises(LLMError, match="after output began; automatic replay is unsafe"):
        client.chat([{"role": "user", "content": "Answer"}], max_tokens=512)
    assert qwen_backends["requests"] == [("coordinator", "Bearer coordinator-key", "coordinator-model")]


def test_qwen_backup_isolation_both_failing_and_overflow_passthrough(qwen_backends):
    qwen_backends["modes"]["coordinator"] = "unavailable"
    client = LLMClient(Settings(provider="qwen38", qwen_context_window=8192, trust_env=False,
                                api_key="primary-only-key", model="primary-only-model"))
    assert client.chat([{"role": "user", "content": "Answer"}], max_tokens=512).content == "Answer from litellm"
    assert qwen_backends["requests"] == [("coordinator", "Bearer primary-only-key", "primary-only-model"),
                                         ("litellm", "Bearer litellm-key", "litellm-model")]

    qwen_backends["requests"].clear()
    qwen_backends["modes"] = {"coordinator": "unavailable", "litellm": "unavailable"}
    with pytest.raises(LLMError, match="litellm fallback failed"):
        LLMClient(Settings(provider="qwen38", qwen_context_window=8192)).chat([{"role": "user", "content": "hi"}],
                                                                              max_tokens=512)
    assert [r[0] for r in qwen_backends["requests"]] == ["coordinator", "litellm"]

    qwen_backends["requests"].clear()
    qwen_backends["modes"] = {"coordinator": "overflow", "litellm": "success"}
    with pytest.raises(ContextOverflow):
        LLMClient(Settings(provider="qwen38", qwen_context_window=8192)).chat([{"role": "user", "content": "hi"}],
                                                                              max_tokens=512)
    assert [r[0] for r in qwen_backends["requests"]] == ["coordinator"]
