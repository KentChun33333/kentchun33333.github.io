from __future__ import annotations

import pytest

from kentc_agent.config import Settings
from kentc_agent.adapters.llm import LLMClient, LLMError


def deployment(window, model="deployed", **metadata):
    return {"id": model, "meta": {"n_ctx": window}, **metadata}


def test_refresh_tracks_deployed_limit_for_same_model_and_endpoint(monkeypatch):
    current = deployment(15536)
    client = LLMClient(Settings(model="deployed"))
    monkeypatch.setattr(client, "_get", lambda _: {"data": [current]})
    assert client.info().context_window == 15536

    current = deployment(64000)
    assert client.info(refresh=True).context_window == 64000

    current = {"id": "deployed"}
    with pytest.raises(LLMError, match="deployed context limit"):
        client.info(refresh=True)
    with pytest.raises(LLMError, match="deployed context limit"):
        client.info()


def test_selected_model_never_borrows_another_deployments_limit(monkeypatch):
    client = LLMClient(Settings(model="selected"))
    monkeypatch.setattr(client, "_get", lambda _: {"data": [deployment(8192, "other")]})
    with pytest.raises(LLMError, match="selected model 'selected'"):
        client.info()


@pytest.mark.parametrize("window", [None, 0, -1, True, 8192.5, "unknown"])
def test_missing_or_invalid_limit_is_not_replaced_with_a_default(monkeypatch, window):
    client = LLMClient(Settings())
    monkeypatch.setattr(client, "_get", lambda _: {"data": [deployment(window)]})
    with pytest.raises(LLMError, match="deployed context limit"):
        client.info()


def test_vllm_deployment_limit_and_optimistic_vision(monkeypatch):
    client = LLMClient(Settings())
    monkeypatch.setattr(client, "_get", lambda _: {"data": [{"id": "deployed", "max_model_len": 24576}]})
    info = client.info()
    assert info.context_window == 24576
    assert info.vision is True


def test_explicit_text_only_metadata_disables_visual_input(monkeypatch):
    client = LLMClient(Settings())
    entry = deployment(8192, architecture={"input_modalities": ["text"]})
    monkeypatch.setattr(client, "_get", lambda _: {"data": [entry]})
    assert client.info().vision is False
