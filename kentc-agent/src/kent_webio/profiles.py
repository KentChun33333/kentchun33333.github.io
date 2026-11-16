"""Server-selected profiles and workspace-confined YAML workflow runs."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from kentc_agent.adapters.tools import Tool, ToolContext
from kentc_agent.workflow import NeedsAnswer, Runner, Workflow, WorkflowError, load

from .workspace import HTML_SUFFIXES, TOOLS, WorkspaceAgent, workspace_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_TOOLS = {tool.name: tool for tool in TOOLS}


def load_workspace_workflow(path: Path) -> Workflow:
    workflow = load(path)
    if any(step.kind == "web" or not set(step.spec.get("tools", workflow.tools) or ()) <= WORKSPACE_TOOLS.keys()
           for step in workflow.steps):
        raise WorkflowError("This workflow requires tools outside the WebIO task workspace.")
    return workflow


class ProfileCatalog:
    def __init__(self, root: Path) -> None:
        self.personas = self._markdown(root / "personas")
        self.skills = self._markdown(root / "skills")
        self.workflows: dict[str, Workflow] = {}
        for directory in (root / "config" / "cli" / "workflows", root / "workflows"):
            for path in sorted(directory.glob("*.y*ml")):
                if path.suffix not in (".yaml", ".yml") or path.is_symlink() or not path.is_file():
                    continue
                try:
                    workflow = load_workspace_workflow(path)
                except (OSError, ValueError, TypeError, WorkflowError):
                    continue
                self.workflows[path.stem] = workflow

    @staticmethod
    def _markdown(directory: Path) -> dict[str, Path]:
        profiles = {path.stem: path for path in sorted(directory.glob("*.md"))
                    if path.is_file() and not path.is_symlink()}
        for path in sorted(directory.glob("*/SKILL.md")):
            if path.is_file() and not path.is_symlink() and not path.parent.is_symlink():
                profiles[path.parent.name] = path
        return profiles

    def describe(self) -> dict[str, Any]:
        return {
            "personas": list(self.personas), "skills": list(self.skills),
            "workflows": [{"id": key, "name": wf.name, "description": wf.description}
                          for key, wf in self.workflows.items()],
        }

    def instructions(self, persona: str, skills: list[str]) -> str:
        try:
            profiles = ([self.personas[persona]] if persona else []) + [self.skills[skill] for skill in skills]
        except KeyError as error:
            raise ValueError(f"Unknown agent profile {error.args[0]!r}.") from None
        return "\n\n".join(path.read_text(encoding="utf-8") for path in profiles)


class WorkspaceRunner(Runner):
    agent_type = WorkspaceAgent

    def __init__(self, wf: Workflow, ctx: ToolContext, inputs: dict[str, Any], run_dir: Path, *,
                 answers: dict[str, str], on_save: Callable[[dict[str, Any]], None]) -> None:
        self.on_save = on_save
        super().__init__(wf, ctx, inputs, run_dir, ask_user=self._pause, answers=answers)

    @staticmethod
    def _pause(step: str, message: str, options: list[str] | None, default: str | None) -> str:
        raise NeedsAnswer(step, message, options, default)

    def _tools(self, names: list[str] | None) -> list[Tool]:
        if names is None:
            return TOOLS
        try:
            return [WORKSPACE_TOOLS[name] for name in names]
        except KeyError as error:
            raise WorkflowError(f"Tool {error.args[0]!r} is unavailable in the task workspace.") from None

    def _write_output(self, path: str, text: str) -> None:
        target = workspace_path(self.ctx.workspace, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        if target.suffix.lower() in HTML_SUFFIXES:
            self.agent.saved_outputs[target.relative_to(self.ctx.workspace).as_posix()] = None

    def save(self) -> None:
        super().save()
        self.on_save(self.state)
