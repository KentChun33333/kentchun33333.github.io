from __future__ import annotations

import json

import pytest

from kentc_agent.adapters.llm import LLMClient, LLMError, ModelInfo
from kentc_agent.config import Settings
from kentc_agent import cli


def test_openrouter_uses_its_model_metadata_and_environment_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-router-key")
    client = LLMClient(Settings(provider="openrouter"))
    assert client.base == "https://openrouter.ai/api/v1"
    assert client._headers()["Authorization"] == "Bearer test-router-key"
    entry = {"id": "qwen/qwen3.8-flash", "context_length": 1_000_000,
             "top_provider": {"context_length": 262_144},
             "architecture": {"input_modalities": ["text", "image"]}}
    monkeypatch.setattr(client, "_get", lambda _path: {"data": [entry]})
    assert client.info() == ModelInfo("qwen/qwen3.8-flash", 262_144, True)
    entry["top_provider"]["context_length"] = 16_384
    assert client.info(refresh=True).context_window == 16_384


def test_ollama_reads_the_running_allocation_instead_of_model_maximum(monkeypatch):
    client = LLMClient(Settings(provider="ollama", model="local:latest"))
    assert client.base == "http://127.0.0.1:11434/v1"

    def get(path, *, native=False):
        if native:
            assert path == "/api/ps"
            return {"models": [{"name": "different:latest", "context_length": 128_000},
                               {"name": "local:latest", "context_length": 8192}]}
        return {"data": [{"id": "local:latest", "context_length": 262_144}]}

    monkeypatch.setattr(client, "_get", get)
    assert client.info() == ModelInfo("local:latest", 8192, False)


def test_ollama_requires_a_verified_limit_when_the_model_is_not_running(monkeypatch):
    client = LLMClient(Settings(provider="ollama", model="local:latest"))
    monkeypatch.setattr(client, "_get", lambda _path, **kwargs:
                        {"models": []} if kwargs.get("native") else {"data": [{"id": "local:latest"}]})
    with pytest.raises(LLMError, match="verified num_ctx"):
        client.info()
    configured = LLMClient(Settings(provider="ollama", model="local:latest", ollama_context_window=8192))
    monkeypatch.setattr(configured, "_get", client._get)
    assert configured.info().context_window == 8192


@pytest.mark.parametrize("provider", ["openrouter", "ollama"])
def test_alternative_provider_streams_tool_calls_and_usage(monkeypatch, provider):
    client = LLMClient(Settings(provider=provider, model="selected", api_key="test-key"))
    client._info = ModelInfo("selected", 8192, False)
    captured = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def __iter__(self):
            events = [{"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "read-1",
                       "type": "function", "function": {"name": "read", "arguments": '{"path":"a.txt"}'}}]},
                       "finish_reason": "tool_calls"}]},
                      {"choices": [], "usage": {"prompt_tokens": 100, "completion_tokens": 20}}]
            return iter([*(f"data: {json.dumps(event)}\n\n".encode() for event in events), b"data: [DONE]\n\n"])

    def open_request(request, timeout):
        captured.append(json.loads(request.data))
        return Response()

    monkeypatch.setattr(client, "_open", open_request)
    result = client.chat([{"role": "user", "content": "Read a.txt"}], max_tokens=512, effort="low")
    assert result.tool_calls[0]["function"] == {"name": "read", "arguments": '{"path":"a.txt"}'}
    assert result.usage.total == 120
    assert captured[0]["model"] == "selected"
    assert ("stream_options" in captured[0]) == (provider == "openrouter")
    if provider == "openrouter":
        assert captured[0]["reasoning"] == {"effort": "low"}
    else:
        assert captured[0]["reasoning_effort"] == "low"


def test_provider_flags_work_through_cli_setup(tmp_path):
    args = cli.parser().parse_args(["-w", str(tmp_path), "--provider", "ollama", "--model", "local:latest",
                                    "--ollama-context-window", "8192", "--context-budget-tokens", "4096"])
    ctx = cli.make_context(args, cli.ConsoleUI())
    assert ctx.llm.base == "http://127.0.0.1:11434/v1"
    assert ctx.settings.context_budget_tokens == 4096
    assert ctx.settings.ollama_context_window == 8192
