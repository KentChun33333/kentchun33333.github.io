"""OpenRouter as an alternative OpenAI-compatible provider (no network)."""

from __future__ import annotations

import json

import pytest

from kentc_agent import cli, config
from kentc_agent.adapters import llm


def test_openrouter_defaults_key_and_routed_context_limit(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-router-key")
    client = llm.LLMClient(config.Settings(provider="openrouter"))
    assert client.base == "https://openrouter.ai/api/v1"
    assert client._headers()["Authorization"] == "Bearer test-router-key"
    entry = {"id": "qwen/qwen3.8-flash", "context_length": 1_000_000,
             "top_provider": {"context_length": 262_144},
             "architecture": {"input_modalities": ["text", "image"]}}
    monkeypatch.setattr(client, "_get", lambda _path: {"data": [entry]})
    assert client.info() == llm.ModelInfo("qwen/qwen3.8-flash", 262_144, True)
    entry["top_provider"]["context_length"] = None
    assert client.info(refresh=True).context_window == 1_000_000
    entry["context_length"] = 0
    with pytest.raises(llm.LLMError, match="context_length"):
        client.info(refresh=True)


def test_openrouter_explicit_settings_win_over_defaults(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-key")
    client = llm.LLMClient(config.Settings(provider="openrouter", base_url="https://proxy.example/v1",
                                           api_key="explicit-key", model="anthropic/claude"))
    assert client.base == "https://proxy.example/v1"
    assert client._headers()["Authorization"] == "Bearer explicit-key"
    assert client.settings.model == "anthropic/claude"


def test_openrouter_streams_reasoning_tool_calls_and_usage():
    client = llm.LLMClient(config.Settings(provider="openrouter", model="selected", api_key="test-key"))
    client._info = llm.ModelInfo("selected", 8192, False)
    captured, deltas = [], []

    class Response:
        def __init__(self, events):
            self.events = events

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def __iter__(self):
            return iter([*(f"data: {json.dumps(e)}\n\n".encode() for e in self.events), b"data: [DONE]\n\n"])

    events = [{"choices": [{"delta": {"reasoning": "think"}}]},
              {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "read-1", "type": "function",
                "function": {"name": "read", "arguments": '{"path":"a.txt"}'}}]},
                "finish_reason": "tool_calls"}]},
              {"choices": [], "usage": {"prompt_tokens": 100, "completion_tokens": 20}}]

    def open_request(request, timeout):
        captured.append(json.loads(request.data))
        return Response(events)

    client._open = open_request
    result = client.chat([{"role": "user", "content": "Read a.txt"}], max_tokens=512, effort="low",
                         on_delta=lambda kind, text: deltas.append((kind, text)))
    assert result.tool_calls[0]["function"] == {"name": "read", "arguments": '{"path":"a.txt"}'}
    assert result.usage.total == 120
    assert ("reasoning", "think") in deltas
    assert captured[0]["reasoning"] == {"effort": "low"}
    assert "reasoning_effort" not in captured[0]
    assert captured[0]["stream_options"] == {"include_usage": True}


def test_openrouter_selectable_from_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-router-key")
    args = cli.parser().parse_args(["-w", str(tmp_path), "--provider", "openrouter"])
    ctx = cli.make_context(args, cli.ConsoleUI())
    assert ctx.llm.base == "https://openrouter.ai/api/v1"
    assert ctx.llm.settings.model == "qwen/qwen3.8-flash"
