"""Financial document key-value extraction backend powered by local Qwen3.8 and PaddleOCR."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "extraction_schema.yaml"


class ConfigNode(dict):
    """Minimal dot-accessible wrapper around plain YAML dicts (no redundant config.py needed)."""

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = _wrap(value)


def _wrap(obj: Any) -> Any:
    if isinstance(obj, dict):
        return ConfigNode({k: _wrap(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_wrap(v) for v in obj]
    return obj


def load_config(config_path: str | Path | None = None) -> ConfigNode:
    """Load config.yaml directly with lightweight env overrides and guardrail checks."""
    path = Path(config_path) if config_path else Path(
        os.environ.get("FIN_PLAN_CONFIG", DEFAULT_CONFIG_PATH)
    )
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        cfg = _wrap(yaml.safe_load(f) or {})

    if env_llm_url := os.environ.get("QWEN_BASE_URL"):
        cfg.llm.base_url = env_llm_url
    if env_llm_model := os.environ.get("QWEN_MODEL"):
        cfg.llm.model = env_llm_model
    if env_ocr_url := os.environ.get("PADDLE_OCR_URL"):
        cfg.paddle_ocr.base_url = env_ocr_url
    if env_ocr_engine := os.environ.get("PADDLE_OCR_ENGINE"):
        cfg.paddle_ocr.engine = env_ocr_engine

    if not (1 <= int(cfg.llm.pages_per_call) <= 5):
        raise ValueError(f"llm.pages_per_call must be in 1..5, got {cfg.llm.pages_per_call}")
    return cfg


def load_extraction_schema(cfg: ConfigNode | None = None) -> dict[str, Any]:
    """Load configurable document_type key definitions & prompt templates from YAML."""
    schema_rel = None
    if cfg and "extraction" in cfg and "schema_file" in cfg["extraction"]:
        schema_rel = cfg["extraction"]["schema_file"]
    env_override = os.environ.get("FIN_PLAN_SCHEMA")
    if env_override:
        path = Path(env_override)
    elif schema_rel:
        p = Path(schema_rel)
        path = p if p.is_absolute() else PROJECT_ROOT / p
    else:
        path = DEFAULT_SCHEMA_PATH

    if not path.exists():
        raise FileNotFoundError(f"Extraction schema YAML not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
