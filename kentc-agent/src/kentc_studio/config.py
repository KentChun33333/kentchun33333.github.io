"""Studio configuration (config/studio.yaml): the apps one studio serves, the skill library their agents draw on,
and the bank databases and SQL data pulls they share. Paths are relative to this file.

    apps:                          # name -> app manifest (apps.py): intake, agents (contract + skills), report
      ter: apps/ter/app.yaml
    skills: ../skills              # skill library: <name>.md files the apps' agents name (the default)
    public_url: http://127.0.0.1:8090
    databases: {...}               # data.py
    data_pulls: {...}              # an app lists the pulls it offers; their SQL binds the app's fields
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .apps import App, load_app
from .data import DataError, DataPull, load_pulls
from .providers import AgentError


class StudioRaw(BaseModel):
    """Top-level studio.yaml shape; unknown keys are rejected before apps are built."""

    model_config = ConfigDict(extra="forbid")

    apps: dict[str, str] = Field(default_factory=dict)
    skills: str = "../skills"
    public_url: str = "http://127.0.0.1:8090"
    databases: dict[str, dict[str, Any]] = Field(default_factory=dict)
    data_pulls: dict[str, dict[str, Any]] = Field(default_factory=dict)


@dataclass
class StudioConfig:
    apps: dict[str, App]
    public_url: str
    pulls: dict[str, DataPull]            # SQL data pulls (no model), offered by the apps that list them


def load_config(path: Path) -> StudioConfig:
    try:
        raw = StudioRaw.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    except (ValidationError, yaml.YAMLError) as e:
        raise AgentError(f"{path}: invalid studio.yaml: {e}") from None
    if not raw.apps:
        raise AgentError(f"{path}: apps needs at least one app (name: path to its app.yaml)")
    base = path.parent
    try:
        pulls = load_pulls(raw.model_dump(), base)
    except DataError as e:
        raise AgentError(f"{path}: {e}") from None
    skills = (base / raw.skills).resolve()
    if not skills.is_dir():
        raise AgentError(f"{path}: skills folder {skills} not found")
    apps = {name: load_app(name, (base / rel).resolve(), pulls, skills) for name, rel in raw.apps.items()}
    return StudioConfig(apps, str(raw.public_url or "http://127.0.0.1:8090").rstrip("/"), pulls)
