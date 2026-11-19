"""Folder-as-Studio-Agent bridge for kentc-breezeman.

Any folder inside Breezeman's workspace containing `studio.yaml` or `app.yaml` is recognized as a Studio folder:
its `cases/` subfolders follow the strict 3-step workflow (Intake -> Verify -> Report) with output contracts
and checks, while Breezeman remains the single HTTP/WebSocket host, workspace manager, and dynamic task runner.
"""

from __future__ import annotations

import os
import re
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from kentc_studio.api import create_app as create_studio_app
from kentc_studio.models import Case
from kentc_studio.providers import AgentError
from kentc_studio.service.cases import CaseService

from .memory_store import memory_hint
from .workspace import HIDDEN, inside

ROOT = Path(__file__).resolve().parents[2]
BUNDLED_STUDIO = ROOT / "config" / "studio.yaml"
BUNDLED_APPS = ROOT / "config" / "apps"
SKIP_DIRS = HIDDEN | {"cases", "docs", "outputs", "data", "jobs", "node_modules", ".venv"}
_SLUG_RE = re.compile(r"[^a-z0-9]+")

BLANK_APP_YAML = """\
title: {title}
description: Structured 3-step case workflow inside Breezeman.

fields:
  - {{name: title, label: Case title, required: true, column: true, wide: true}}
  - {{name: summary, label: Context, type: textarea}}

lanes:
  - name: documents
    hint: Drop supporting files -> analyst extraction
    required: true
    agent:
      label: Document agent
      per: file
      skills: [document-extraction]
      tools: [read]
      output:
        document_type: string
        summary: string
        key_values: [{{field: string, value: string, location: string, confidence: number}}]
      checks:
        key_values[].location: required
        key_values[].confidence: 0..100

report:
  name: Case report
  verdicts: {{Approved: ok, Needs review: warn}}
  skills: [report-revision]
  tools: [read]
  output:
    title: string
    verdict: "Approved|Needs review"
    reply: string
    requests: [{{document: string, reason: string}}]
    questions: [string]
    executive_summary: string
  checks:
    title: required
    executive_summary: required
"""


def _slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-") or "studio"


def _app_id(text: str) -> str:
    clean = re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")
    if not clean or not clean[0].isalpha():
        clean = f"app_{clean}" if clean else "app"
    return clean[:32]


@dataclass
class _MountedStudio:
    studio_id: str
    folder: Path
    config_path: Path
    service: CaseService
    asgi: Any


class StudioRegistry:
    """Discovers, scaffolds, and lazily mounts Studio folders inside Breezeman's workspace."""

    def __init__(self, workspace: Path, skills_dir: Path, effort: str | None = None) -> None:
        self.workspace = workspace.resolve()
        self.skills_dir = skills_dir.resolve()
        self.effort = effort
        self._lock = threading.Lock()
        self._mounted: dict[str, _MountedStudio] = {}

    def templates(self) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        if BUNDLED_APPS.is_dir():
            for d in sorted(BUNDLED_APPS.iterdir()):
                manifest = d / "app.yaml"
                if d.is_dir() and manifest.is_file():
                    try:
                        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
                    except yaml.YAMLError:
                        data = {}
                    out.append({
                        "id": d.name,
                        "title": str(data.get("title") or d.name.upper()),
                        "description": str(data.get("description") or ""),
                    })
        out.append({"id": "blank", "title": "Blank 3-step Studio", "description": "Minimal 3-step intake -> verify -> report template."})
        return out

    def _scan_dirs(self) -> list[Path]:
        """Find folders (up to depth 2, plus tasks/*) containing studio.yaml or app.yaml."""
        found: list[Path] = []
        seen: set[Path] = set()

        def visit(folder: Path, depth: int) -> None:
            if folder in seen or not folder.is_dir():
                return
            seen.add(folder)
            if (folder / "studio.yaml").is_file() or (folder / "app.yaml").is_file():
                found.append(folder)
                return  # a Studio folder owns its subtree (cases/)
            if depth >= 2:
                return
            try:
                children = sorted(folder.iterdir(), key=lambda p: p.name.casefold())
            except OSError:
                return
            for child in children:
                if child.is_dir() and child.name not in SKIP_DIRS and not child.name.startswith("."):
                    visit(child, depth + 1)

        visit(self.workspace, 0)
        return found

    def _studio_id_for(self, folder: Path) -> str:
        if folder == self.workspace:
            return "root"
        rel = folder.relative_to(self.workspace).as_posix()
        return _slugify(rel.replace("/", "-"))

    def _ensure_studio_yaml(self, folder: Path) -> Path:
        """Return studio.yaml path, synthesizing one when a folder only provides app.yaml."""
        studio_yaml = folder / "studio.yaml"
        if studio_yaml.is_file():
            return studio_yaml
        app_yaml = folder / "app.yaml"
        if not app_yaml.is_file():
            raise FileNotFoundError(f"no studio.yaml or app.yaml in {folder}")
        app_id = _app_id(folder.name)
        rel_skills = os.path.relpath(self.skills_dir, folder)
        doc: dict[str, Any] = {"apps": {app_id: "app.yaml"}, "skills": rel_skills}
        # Inherit shared databases / data_pulls if app.yaml references pulls from bundled config.
        try:
            app_raw = yaml.safe_load(app_yaml.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            app_raw = {}
        if app_raw.get("pulls") and BUNDLED_STUDIO.is_file():
            bundled = yaml.safe_load(BUNDLED_STUDIO.read_text(encoding="utf-8")) or {}
            bdir = BUNDLED_STUDIO.parent
            if bundled.get("databases"):
                dbs = {}
                for k, v in bundled["databases"].items():
                    item = dict(v)
                    if "path" in item:
                        item["path"] = os.path.relpath((bdir / item["path"]).resolve(), folder)
                    dbs[k] = item
                doc["databases"] = dbs
            if bundled.get("data_pulls"):
                pulls = {}
                for k, v in bundled["data_pulls"].items():
                    item = dict(v)
                    if "sql_file" in item:
                        item["sql_file"] = os.path.relpath((bdir / item["sql_file"]).resolve(), folder)
                    pulls[k] = item
                doc["data_pulls"] = pulls
        studio_yaml.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return studio_yaml

    def _describe(self, folder: Path) -> dict[str, Any]:
        sid = self._studio_id_for(folder)
        rel = "" if folder == self.workspace else folder.relative_to(self.workspace).as_posix()
        title = folder.name
        apps: list[str] = []
        app_yaml = folder / "app.yaml"
        studio_yaml = folder / "studio.yaml"
        try:
            if app_yaml.is_file():
                raw = yaml.safe_load(app_yaml.read_text(encoding="utf-8")) or {}
                title = str(raw.get("title") or title)
                apps = [folder.name]
            elif studio_yaml.is_file():
                raw = yaml.safe_load(studio_yaml.read_text(encoding="utf-8")) or {}
                apps = list((raw.get("apps") or {}).keys())
                if len(apps) == 1:
                    sub_app = (folder / raw["apps"][apps[0]]).resolve()
                    if sub_app.is_file():
                        sub_raw = yaml.safe_load(sub_app.read_text(encoding="utf-8")) or {}
                        title = str(sub_raw.get("title") or title)
        except (OSError, yaml.YAMLError):
            pass
        cases_dir = folder / "cases"
        case_count = sum(1 for c in cases_dir.iterdir() if c.is_dir()) if cases_dir.is_dir() else 0
        return {
            "id": sid,
            "name": title,
            "folder": rel or ".",
            "apps": apps,
            "cases": case_count,
            "url": f"/studios/{sid}/",
        }

    def list_studios(self) -> list[dict[str, Any]]:
        return [self._describe(f) for f in self._scan_dirs()]

    def folder_of(self, studio_id: str) -> Path:
        target = next((f for f in self._scan_dirs() if self._studio_id_for(f) == studio_id), None)
        if target is None:
            raise KeyError(studio_id)
        return target

    def create_studio(self, name: str, folder: str = "", template: str = "ter") -> dict[str, Any]:
        clean = " ".join(name.split())
        if not clean:
            raise ValueError("studio name is required")
        if folder.strip():
            target = inside(self.workspace, folder.strip())
            if target == self.workspace:
                raise ValueError("studio folder must be a subfolder")
        else:
            slug = _slugify(clean)
            n = 1
            while True:
                cand = f"tasks/{slug}" if n == 1 else f"tasks/{slug}-{n}"
                target = inside(self.workspace, cand)
                if not target.exists():
                    break
                n += 1
        if (target / "app.yaml").is_file() or (target / "studio.yaml").is_file():
            raise ValueError(f"folder already has a studio manifest: {target.relative_to(self.workspace)}")
        target.mkdir(parents=True, exist_ok=True)
        if template != "blank":
            src = BUNDLED_APPS / template / "app.yaml"
            if not src.is_file():
                raise ValueError(f"unknown studio template: {template}")
            raw_text = src.read_text(encoding="utf-8")
            try:
                parsed = yaml.safe_load(raw_text) or {}
                if isinstance(parsed.get("sample"), str):
                    sample_abs = (src.parent / parsed["sample"]).resolve()
                    if sample_abs.exists():
                        raw_text = raw_text.replace(parsed["sample"], os.path.relpath(sample_abs, target), 1)
            except yaml.YAMLError:
                pass
            (target / "app.yaml").write_text(raw_text, encoding="utf-8")
        else:
            (target / "app.yaml").write_text(BLANK_APP_YAML.format(title=clean), encoding="utf-8")
        self._ensure_studio_yaml(target)
        return self._describe(target)

    def mount(self, studio_id: str) -> _MountedStudio:
        with self._lock:
            if studio_id in self._mounted:
                return self._mounted[studio_id]
            target = next((f for f in self._scan_dirs() if self._studio_id_for(f) == studio_id), None)
            if target is None:
                raise KeyError(studio_id)
            config_path = self._ensure_studio_yaml(target)
            try:
                svc = CaseService(target, config_path, self.effort)
            except AgentError as e:
                raise ValueError(str(e)) from None
            hint = memory_hint(self.workspace)
            for app in svc.config.apps.values():
                providers = [
                    *(a.provider for a in app.agents.values()),
                    *app.extras.values(),
                    app.report.provider,
                ]
                for provider in providers:
                    if hasattr(provider, "skills") and isinstance(provider.skills, str) and hint not in provider.skills:
                        provider.skills = f"{provider.skills.rstrip()}\n\n{hint}" if provider.skills else hint
            mounted = _MountedStudio(
                studio_id=studio_id,
                folder=target,
                config_path=config_path,
                service=svc,
                asgi=create_studio_app(svc, token=""),
            )
            self._mounted[studio_id] = mounted
            return mounted

    def sync_cases(self, mounted: _MountedStudio) -> None:
        """Pick up case folders created on disk outside the running CaseService."""
        svc = mounted.service
        root = svc.root
        if not root.is_dir():
            return
        disk_ids = {d.name for d in root.iterdir() if d.is_dir() and (d / "case.json").is_file()}
        if disk_ids <= set(svc.cases):
            return
        loaded = svc.store.load_all(Case, svc.config.apps)
        for cid, case in loaded.items():
            svc.cases.setdefault(cid, case)

    def close(self) -> None:
        with self._lock:
            mounted = list(self._mounted.values())
            self._mounted.clear()
        for m in mounted:
            disp = getattr(m.service, "dispatcher", None)
            if disp is not None and hasattr(disp, "stop"):
                disp.stop()
