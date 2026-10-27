"""Qwen38 coordinator/LiteLLM defaults and isolated per-backend overrides."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from typing import Any

from ..config import Settings, read_yaml_config


_CONFIG_PATH = Path(__file__).resolve().parents[1] / "deployment_config" / "qwen38.yaml"
if not _CONFIG_PATH.is_file():  # source checkout; wheels carry the same file as package data
    _CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "qwen38.yaml"


def _backend_defaults(backend: str) -> dict[str, str]:
    try:
        data = read_yaml_config(_CONFIG_PATH).get(backend)
    except OSError:
        raise ValueError(f"Cannot read Qwen deployment configuration: {_CONFIG_PATH}") from None
    if not isinstance(data, dict) or any(
        not isinstance(data.get(key), str) or not data[key].strip()
        for key in ("base_url", "api_key", "model")
    ):
        raise ValueError(f"{_CONFIG_PATH}: {backend} requires non-empty base_url, api_key and model strings")
    return data


def connection(settings: Settings) -> Settings:
    """Resolve the selected backend using only its own endpoint, credential and model."""
    backend = settings.qwen_backend
    if backend not in ("coordinator", "litellm"):
        raise ValueError("qwen_backend must be coordinator or litellm")
    if isinstance(settings.qwen_context_window, bool) or settings.qwen_context_window <= 0:
        raise ValueError("qwen38 requires a positive qwen_context_window: set the verified deployed token limit")
    coordinator = backend == "coordinator"
    defaults = _backend_defaults(backend)
    endpoint = settings.base_url
    if not endpoint or endpoint == Settings.base_url:
        endpoint = (os.getenv("QWEN38_COORDINATOR_ENDPOINT" if coordinator else "GATEWAY_URL") or
                    defaults["base_url"]).rstrip("/")
        if endpoint and not coordinator and not endpoint.endswith("/v1"):
            endpoint += "/v1"
    key = settings.api_key or os.getenv("VLM_API_KEY" if coordinator else "LITELLM_MASTER_KEY") or \
        defaults["api_key"]
    model = settings.model or os.getenv("QWEN38_COORDINATOR_MODEL" if coordinator else "QWEN38_LITELLM_MODEL") or \
        defaults["model"]
    return replace(settings, base_url=endpoint, api_key=key, model=model)


def fallback_settings(settings: Settings) -> Settings:
    """Discard primary overrides so credentials and model cannot leak to the other backend."""
    backend = "litellm" if settings.qwen_backend == "coordinator" else "coordinator"
    return replace(settings, qwen_backend=backend, base_url=Settings.base_url, api_key="", model="")


def normalise_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fold system messages into the first position without mutating stored conversation."""
    systems: list[str] = []
    conversation: list[dict[str, Any]] = []
    for raw in messages:
        message = dict(raw)
        if message.get("role") == "system":
            value = message.get("content")
            if value not in (None, ""):
                systems.append(value if isinstance(value, str) else str(value))
        else:
            conversation.append(message)
    if not any(message.get("role") == "user" for message in conversation):
        raise ValueError("Qwen38 requires a user query after context preparation")
    return ([{"role": "system", "content": "\n\n".join(systems)}] if systems else []) + conversation
