"""Settings, layered: defaults < ~/.config/kentc-agent/config.yaml < <workspace>/.kentc-agent/config.yaml
< KENTC_AGENT_* environment variables < CLI flags."""

from __future__ import annotations

import os
import types
import typing
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any

import yaml

STATE_DIR = ".kentc-agent"
USER_CONFIG = Path.home() / ".config" / "kentc-agent" / "config.yaml"
ENV_PREFIX = "KENTC_AGENT_"


@dataclass(frozen=True)
class Settings:
    """Connection and agent policy; deployed model capabilities are inspected by LLMClient."""
    base_url: str = "http://127.0.0.1:8081/v1"   # any OpenAI-compatible server; default: a local Strata
    api_key: str = ""               # sent as "Authorization: Bearer ..." (e.g. a LiteLLM proxy key)
    model: str = ""                 # "" -> the first model the server lists
    max_output_tokens: int = 8192   # requested per-reply budget, thinking included; clamped to available room
    reserve_tokens: int = 16384     # compact when context > window - reserve
    keep_recent_tokens: int = 20000 # recent history kept verbatim by a compaction
    reasoning_effort: str = ""      # "" -> server default; none | low | medium | high
    sub_effort: str = "low"         # effort for summaries and the parsing sub-agent
    temperature: float | None = None
    max_turns: int = 60             # model calls per prompt; 0 = no limit
    request_timeout: float = 900.0
    bash_timeout: float = 120.0
    web_search_timeout: float = 10.0   # seconds per web_search provider call (ddgs proxy: $DDGS_PROXY)
    web_search_providers: str = "ddgs,searxng"  # tried in order until one has results (adapters/web.py)
    web_search_searxng_url: str = ""   # e.g. http://127.0.0.1:8085 ("" skips searxng); needs json in search.formats
    safety_check: bool = True          # flag prompt-injection text in tool results, strip hidden chars (safety.py)
    tool_output_max_bytes: int = 32_000
    tool_output_max_lines: int = 2000
    big_result_tokens: int = 3000      # one tool result above this -> stored in the operation folder + digest
    big_turn_tokens: int = 12_000      # one turn's tool results above this -> largest stored first until it fits
    big_digest_tokens: int = 1500      # the most a stored result's digest takes in the context
    doc_chunk_tokens: int = 12_000     # upper bound; effective document chunks also fit inspected input/output room
    doc_max_images: int = 4            # page images per sub-agent call
    doc_image_px: int = 1400           # longest side of a rendered PDF page / downscaled image
    doc_render: str = "auto"           # auto | always | never: render PDF pages as images
    show_reasoning: bool = True
    trace: bool = True                 # operation trace per session: .kentc-agent/traces/<session id>.jsonl

    def with_overrides(self, **values: Any) -> Settings:
        return replace(self, **{k: v for k, v in values.items() if v is not None})


def _hint(name: str) -> Any:
    hints = typing.get_type_hints(Settings)
    t = hints[name]
    if isinstance(t, types.UnionType):
        t = next(a for a in typing.get_args(t) if a is not type(None))
    return t


def _coerce(name: str, raw: Any) -> Any:
    t = _hint(name)
    if isinstance(raw, t) and not (t is int and isinstance(raw, bool)):
        return raw
    s = str(raw).strip()
    if t is bool:
        if s.lower() in ("1", "true", "yes", "on"):
            return True
        if s.lower() in ("0", "false", "no", "off"):
            return False
        raise ValueError(f"{name}: expected a boolean, got {raw!r}")
    if t in (int, float):
        return t(s)
    return s


def _apply(values: dict[str, Any], data: dict[str, Any], origin: str) -> None:
    known = {f.name for f in fields(Settings)}
    for key, raw in data.items():
        if key not in known:
            raise ValueError(f"{origin}: unknown setting {key!r}")
        if raw is None:              # `key:` / `key: null` in YAML -> keep the default
            continue
        values[key] = _coerce(key, raw)


def read_yaml_config(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ValueError(f"{path}: invalid YAML: {e}") from None
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping of settings")
    return data


def load_settings(workspace: Path, overrides: dict[str, Any] | None = None) -> Settings:
    values: dict[str, Any] = {}
    for path in (USER_CONFIG, workspace / STATE_DIR / "config.yaml"):
        if path.is_file():
            _apply(values, read_yaml_config(path), str(path))
    env = {f.name: os.environ[f"{ENV_PREFIX}{f.name.upper()}"] for f in fields(Settings)
           if f"{ENV_PREFIX}{f.name.upper()}" in os.environ}
    _apply(values, env, "environment")
    _apply(values, {k: v for k, v in (overrides or {}).items() if v is not None}, "command line")
    return Settings(**values)
