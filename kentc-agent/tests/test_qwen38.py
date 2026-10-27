from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from kentc_agent.adapters.llm import ContextOverflow, LLMClient, LLMError
from kentc_agent.config import Settings


@pytest.fixture
def coordinator():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_error(404, "Coordinator has no model discovery")

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            messages = body["messages"]
            valid = self.path == "/chat/completions" and self.headers.get("Authorization") == "Bearer test-key"
            valid = valid and messages[0] == {"role": "system", "content": "first\n\nsecond"}
            valid = valid and [m["role"] for m in messages] == ["system", "user"]
            valid = valid and not ({"reasoning_effort", "stream_options"} & body.keys())
            if not valid:
                self.send_error(400, "Unsupported coordinator request")
                return
            if body["max_tokens"] > 8192:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": {"message": "maximum context length is 8192 tokens, "
                                                       "resulted in 9000 tokens"}}).encode())
                return
            chunks = [
                {"choices": [{"delta": {"reasoning_content": "inspect source"}}]},
                {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "read-1", "type": "function",
                    "function": {"name": "read", "arguments": '{"path":'}}]}}]},
                {"choices": [{"delta": {"tool_calls": [{"index": 0,
                    "function": {"arguments": '"evidence.txt"}'}}]}, "finish_reason": "tool_calls"}]},
                {"choices": [], "usage": {"prompt_tokens": 43, "completion_tokens": 12}},
            ]
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for chunk in chunks:
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_coordinator_without_discovery_streams_executable_tool_call(coordinator):
    client = LLMClient(Settings(provider="qwen38", base_url=coordinator, api_key="test-key",
                                qwen_context_window=8192, trust_env=False))
    messages = [{"role": "system", "content": "first"}, {"role": "user", "content": "Read evidence"},
                {"role": "system", "content": "second"}]
    reply = client.chat(messages, max_tokens=1024, effort="low")
    assert reply.tool_calls == [{"id": "read-1", "type": "function",
                                 "function": {"name": "read", "arguments": '{"path":"evidence.txt"}'}}]
    assert reply.reasoning == "inspect source"
    assert reply.finish == "tool_calls"
    assert reply.usage.total == 55
    assert len(messages) == 3 and messages[-1]["content"] == "second"
    with pytest.raises(ContextOverflow) as exc:
        client.chat(messages, max_tokens=9000)
    assert exc.value.window == 8192
    assert exc.value.prompt_too_long


@pytest.mark.parametrize("backend,endpoint_var,key_var,model_var,expected_path", [
    ("coordinator", "QWEN38_COORDINATOR_ENDPOINT", "VLM_API_KEY", "QWEN38_COORDINATOR_MODEL", "/"),
    ("litellm", "GATEWAY_URL", "LITELLM_MASTER_KEY", "QWEN38_LITELLM_MODEL", "/v1"),
])
def test_selected_environment_credentials_never_fall_back(monkeypatch, backend, endpoint_var, key_var,
                                                          model_var, expected_path):
    for key in ("VLM_API_KEY", "LITELLM_MASTER_KEY", "QWEN38_COORDINATOR_ENDPOINT", "GATEWAY_URL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(endpoint_var, "https://selected.example/")
    monkeypatch.setenv(model_var, "selected-model")
    other_key = "LITELLM_MASTER_KEY" if backend == "coordinator" else "VLM_API_KEY"
    monkeypatch.setenv(other_key, "wrong-environment-key")
    settings = Settings(provider="qwen38", qwen_backend=backend, qwen_context_window=16384)
    client = LLMClient(settings)
    assert client._headers()["Authorization"] != "Bearer wrong-environment-key"
    monkeypatch.setenv(key_var, "selected-key")
    client = LLMClient(settings)
    assert client.base == "https://selected.example" + expected_path.rstrip("/")
    assert client._headers()["Authorization"] == "Bearer selected-key"
    assert client.info().id == "selected-model"
    assert client.info().context_window == 16384
    assert client.info().vision is False


@pytest.mark.parametrize("window", [0, -1, True])
def test_qwen_rejects_invalid_deployment_limit(window):
    with pytest.raises(LLMError, match="verified deployed token limit"):
        LLMClient(Settings(provider="qwen38", qwen_context_window=window))


def test_qwen_rejects_missing_user_query_before_connecting():
    client = LLMClient(Settings(provider="qwen38", base_url="http://127.0.0.1:1", api_key="test-key",
                                qwen_context_window=8192))
    with pytest.raises(LLMError, match="user query"):
        client.chat([{"role": "system", "content": "instructions"}], max_tokens=100)


@pytest.fixture
def qwen_backends(monkeypatch):
    state = {"modes": {"coordinator": "success", "litellm": "success"}, "requests": []}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            backend = "litellm" if self.path.startswith("/v1/") else "coordinator"
            auth = self.headers.get("Authorization")
            state["requests"].append((backend, auth, body["model"]))
            mode = state["modes"][backend]
            if mode == "unavailable":
                self.send_error(503, "Backend unavailable")
                return
            if auth != f"Bearer {backend}-key" or body["model"] != f"{backend}-model":
                self.send_error(401, "Wrong backend credential or model")
                return
            if mode == "overflow":
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"maximum context length is 8192 tokens; '
                                 b'resulted in 9000 tokens"}}')
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            if mode == "empty":
                return
            if mode == "stream_error":
                chunk = {"error": {"message": "Backend unavailable"}}
            else:
                delta = {
                    "success": {"content": f"Answer from {backend}"},
                    "content": {"content": "partial answer"},
                    "reasoning": {"reasoning_content": "partial reasoning"},
                    "tool": {"tool_calls": [{"index": 0, "id": "partial", "function": {"name": "read"}}]},
                    "role": {"role": "assistant"},
                }[mode]
                choice = {"delta": delta}
                if mode == "success":
                    choice["finish_reason"] = "stop"
                chunk = {"choices": [choice]}
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            if mode == "success":
                self.wfile.write(b"data: [DONE]\n\n")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    monkeypatch.setenv("QWEN38_COORDINATOR_ENDPOINT", url + "/coordinator")
    monkeypatch.setenv("GATEWAY_URL", url)
    for backend, key, model in (
        ("coordinator", "VLM_API_KEY", "QWEN38_COORDINATOR_MODEL"),
        ("litellm", "LITELLM_MASTER_KEY", "QWEN38_LITELLM_MODEL"),
    ):
        monkeypatch.setenv(key, backend + "-key")
        monkeypatch.setenv(model, backend + "-model")
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("primary", ["coordinator", "litellm"])
@pytest.mark.parametrize("mode", ["unavailable", "stream_error", "empty"])
def test_qwen_fails_over_before_any_chunk_with_backup_credentials(qwen_backends, primary, mode):
    backup = "litellm" if primary == "coordinator" else "coordinator"
    qwen_backends["modes"][primary] = mode
    client = LLMClient(Settings(provider="qwen38", qwen_backend=primary, qwen_context_window=8192,
                                trust_env=False))
    deltas = []
    reply = client.chat([{"role": "user", "content": "Answer"}], max_tokens=512,
                        on_delta=lambda kind, text: deltas.append((kind, text)))
    assert reply.content == f"Answer from {backup}"
    assert deltas == [("content", f"Answer from {backup}")]
    assert qwen_backends["requests"] == [
        (primary, f"Bearer {primary}-key", f"{primary}-model"),
        (backup, f"Bearer {backup}-key", f"{backup}-model"),
    ]


@pytest.mark.parametrize("mode", ["content", "reasoning", "tool", "role"])
def test_qwen_never_replays_after_any_streamed_chunk(qwen_backends, mode):
    qwen_backends["modes"]["coordinator"] = mode
    client = LLMClient(Settings(provider="qwen38", qwen_context_window=8192, trust_env=False))
    with pytest.raises(LLMError, match="after output began; automatic replay is unsafe"):
        client.chat([{"role": "user", "content": "Answer"}], max_tokens=512)
    assert qwen_backends["requests"] == [("coordinator", "Bearer coordinator-key", "coordinator-model")]


def test_qwen_backup_does_not_inherit_primary_overrides(qwen_backends):
    qwen_backends["modes"]["coordinator"] = "unavailable"
    client = LLMClient(Settings(provider="qwen38", qwen_context_window=8192, trust_env=False,
                                api_key="primary-only-key", model="primary-only-model"))
    reply = client.chat([{"role": "user", "content": "Answer"}], max_tokens=512)
    assert reply.content == "Answer from litellm"
    assert qwen_backends["requests"] == [
        ("coordinator", "Bearer primary-only-key", "primary-only-model"),
        ("litellm", "Bearer litellm-key", "litellm-model"),
    ]


def test_qwen_both_backends_failing_ends_without_looping(qwen_backends):
    qwen_backends["modes"] = {"coordinator": "unavailable", "litellm": "unavailable"}
    client = LLMClient(Settings(provider="qwen38", qwen_context_window=8192, trust_env=False))
    with pytest.raises(LLMError, match="litellm fallback failed"):
        client.chat([{"role": "user", "content": "Answer"}], max_tokens=512)
    assert [r[0] for r in qwen_backends["requests"]] == ["coordinator", "litellm"]


def test_qwen_overflow_is_left_for_agent_budget_recovery(qwen_backends):
    qwen_backends["modes"]["coordinator"] = "overflow"
    client = LLMClient(Settings(provider="qwen38", qwen_context_window=8192, trust_env=False))
    with pytest.raises(ContextOverflow):
        client.chat([{"role": "user", "content": "Answer"}], max_tokens=512)
    assert [r[0] for r in qwen_backends["requests"]] == ["coordinator"]
