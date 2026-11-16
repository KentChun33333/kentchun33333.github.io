"""Persistent task catalog for one WebIO workspace."""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from kentc_agent.workflow import WorkflowError

from .profiles import ProfileCatalog, load_workspace_workflow
from .runtime import WebIO
from .workspace import atomic_text

TASK_ID = re.compile(r"[0-9a-f]{32}")


class Tasks:
    def __init__(self, legacy: WebIO, profiles: ProfileCatalog) -> None:
        self.legacy = legacy
        self.profiles = profiles
        self.root = legacy.root / "tasks"
        self.lock = Lock()
        self.opened: dict[str, WebIO] = {}

    def _folder(self, task: str) -> Path:
        if not TASK_ID.fullmatch(task):
            raise FileNotFoundError("Task not found.")
        folder = self.root / task
        if folder.resolve() != folder:
            raise FileNotFoundError("Task folder is unavailable.")
        return folder

    def _metadata(self, folder: Path) -> dict[str, Any]:
        path = folder / "task.json"
        if path.is_symlink():
            raise FileNotFoundError("Task not found.")
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self) -> list[dict[str, Any]]:
        with self.lock:
            rows = [self.legacy.task_summary()]
            if self.root.resolve() != self.root or not self.root.is_dir():
                return rows
            for folder in self.root.iterdir():
                if not TASK_ID.fullmatch(folder.name) or folder.is_symlink():
                    continue
                web = self.opened.get(folder.name)
                if web:
                    rows.append(web.task_summary())
                    continue
                try:
                    metadata = self._metadata(folder)
                    workspace = folder / "workspace"
                    if workspace.resolve() != workspace or not workspace.is_dir() or metadata["id"] != folder.name:
                        continue
                    rows.append(WebIO.stored_task_summary(metadata, workspace))
                except (OSError, ValueError, KeyError, TypeError):
                    continue
            return sorted(rows, key=lambda row: (not row["id"], -row["updated"], row["title"].casefold()))

    def get(self, task: str) -> WebIO:
        if not task:
            return self.legacy
        with self.lock:
            if task not in self.opened:
                folder = self._folder(task)
                self.opened[task] = self._open(folder, self._metadata(folder))
            return self.opened[task]

    def _open(self, folder: Path, metadata: dict[str, Any]) -> WebIO:
        workspace = folder / "workspace"
        if workspace.resolve() != workspace or not workspace.is_dir() or metadata["id"] != folder.name:
            raise FileNotFoundError("Task workspace is unavailable.")
        workflow_path = folder / "workflow.yaml"
        if metadata["workflow"] and (workflow_path.is_symlink() or not workflow_path.is_file()):
            raise FileNotFoundError("Task workflow is unavailable.")
        workflow = load_workspace_workflow(workflow_path) if metadata["workflow"] else None
        settings = self.legacy.agent.ctx.settings
        return WebIO(workspace, settings, self.legacy.agent.ctx.llm, task=metadata, workflow=workflow)

    def create(self, title: str, persona: str, skills: list[str], workflow: str) -> dict[str, Any]:
        title = title.strip()
        if not title:
            raise ValueError("Enter a task name.")
        skills = list(dict.fromkeys(skills))
        instructions = self.profiles.instructions(persona, skills)
        selected = self.profiles.workflows.get(workflow)
        if workflow and selected is None:
            raise ValueError("Choose a workflow available to this workspace.")
        task = uuid4().hex
        metadata = {"id": task, "title": title, "persona": persona, "skills": skills, "workflow": workflow,
                    "instructions": instructions, "created": time.time()}
        with self.lock:
            folder = self._folder(task)
            folder.mkdir(parents=True)
            try:
                (folder / "workspace").mkdir()
                if selected:
                    atomic_text(folder / "workflow.yaml", selected.path.read_text(encoding="utf-8"))
                try:
                    web = self._open(folder, metadata)
                except WorkflowError as error:
                    raise ValueError(str(error)) from None
                atomic_text(folder / "task.json", json.dumps(metadata, ensure_ascii=False))
            except BaseException:
                shutil.rmtree(folder, ignore_errors=True)
                raise
            self.opened[task] = web
            return web.task_summary()

    def set_closed(self, web: WebIO, closed: bool) -> dict[str, Any]:
        folder = self._folder(web.task["id"])
        updated = {**web.task, "closed": closed, "modified": time.time()}
        atomic_text(folder / "task.json", json.dumps(updated, ensure_ascii=False))
        with web.condition:
            web.task = updated
            web.push({"patch": {"task": web.task_view()}})
        return web.task_summary()
