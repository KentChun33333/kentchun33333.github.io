"""Studio configuration: which agent does each job, and how to reach it.

- WorkflowProvider runs a kentc-agent workflow in-process on the configured LLM server. The result is the JSON
  answer of the workflow's last step. A local server serves one request at a time, so these jobs run one by one.
- HttpProvider calls an external agent: another process or host, any implementation. It POSTs
      {"role", "case_id", "job_id", "inputs", "documents": [{"name", "role", "url"}], "materials"}
  and expects back a JSON object (the result itself, or {"result": {...}}). These jobs run in parallel with
  the local ones.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from kentc_agent.adapters.llm import LLMClient
from kentc_agent.adapters.tools import CORE_TOOLS, ToolContext
from kentc_agent.config import Settings
from kentc_agent.ports import Events
from kentc_agent.workflow import Runner, Workflow, WorkflowError, load, resolve_inputs

from .data import DataError, DataPull, load_pulls

# Studio agents read uploaded (untrusted) documents: a prompt injected into a document must not reach a shell, so
# their workflows may not offer these tools; nor may they have web steps, so case data never leaves the machine in
# search queries.
UNTRUSTED_INPUT_DENY = {"bash"}


class AgentError(RuntimeError):
    pass


class StudioRaw(BaseModel):
    """Top-level studio.yaml shape; unknown keys are rejected before providers are built."""

    model_config = ConfigDict(extra="forbid")

    agents: dict[str, dict[str, Any]] = Field(default_factory=dict)
    extra_agents: dict[str, dict[str, Any]] = Field(default_factory=dict)
    public_url: str = "http://127.0.0.1:8090"
    databases: dict[str, dict[str, Any]] = Field(default_factory=dict)
    data_pulls: dict[str, dict[str, Any]] = Field(default_factory=dict)


@dataclass
class Provider:
    name: str
    label: str
    default: bool = False

    @property
    def local(self) -> bool:          # runs on the local model: one at a time
        return False

    def describe(self) -> str:
        raise NotImplementedError

    def run(self, *, case_dir: Path, job_dir: Path, inputs: dict[str, Any], events: Events, settings: Settings,
            llm: LLMClient, request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


@dataclass
class WorkflowProvider(Provider):
    path: Path = Path()

    @property
    def local(self) -> bool:
        return True

    def describe(self) -> str:
        return f"kentc-agent workflow {self.path.name}"

    def run(self, *, case_dir, job_dir, inputs, events, settings, llm, request):
        """Uploaded documents are untrusted: the agent's reads stay inside the case folder."""
        wf = load(self.path)
        ctx = ToolContext(case_dir, settings, llm, events, confine_reads=True)
        state = Runner(wf, ctx, resolve_inputs(wf, inputs), job_dir).run()
        data = state["steps"][wf.steps[-1].id].get("data")
        if not isinstance(data, dict):
            raise AgentError(f"{self.path.name}: the last step gave no JSON object (add format: json to it)")
        return data


@dataclass
class HttpProvider(Provider):
    url: str = ""
    timeout: float = 1800

    def describe(self) -> str:
        return f"external agent at {self.url}"

    def run(self, *, case_dir, job_dir, inputs, events, settings, llm, request):
        events.status(self.name, f"calling {self.url}")
        body = json.dumps(request, ensure_ascii=False).encode()
        req = urllib.request.Request(self.url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            raise AgentError(f"{self.label}: {e}") from None
        data = data.get("result", data) if isinstance(data, dict) else data
        if not isinstance(data, dict):
            raise AgentError(f"{self.label}: the external agent did not return a JSON object")
        (job_dir / "result.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        return data


@dataclass
class StudioConfig:
    agents: dict[str, Provider]           # doc, context, report
    extras: dict[str, Provider]           # optional agents feeding the report
    public_url: str
    pulls: dict[str, DataPull]            # SQL data pulls (no model)


def _offered_tools(wf: Workflow) -> set[str]:
    """Every tool some prompt step of `wf` offers the model."""
    out: set[str] = set()
    for step in wf.steps:
        if step.kind == "prompt":
            names = step.spec.get("tools", wf.tools)
            out |= set(CORE_TOOLS if names is None else names)
    return out


def _provider(name: str, spec: dict[str, Any], base: Path) -> Provider:
    label = spec.get("label") or name
    if "workflow" in spec:
        path = (base / spec["workflow"]).resolve()
        if not path.is_file():
            raise AgentError(f"agent {name}: workflow {path} not found")
        try:
            wf = load(path)
        except WorkflowError as e:
            raise AgentError(f"agent {name}: {e}") from None
        unsafe = sorted(_offered_tools(wf) & UNTRUSTED_INPUT_DENY)
        if unsafe:
            raise AgentError(f"agent {name}: {path.name} offers {', '.join(unsafe)} (omitted `tools` means all); studio "
                             "agents read untrusted uploaded documents, so they get no shell")
        web = [s.id for s in wf.steps if s.kind == "web"]
        if web:
            raise AgentError(f"agent {name}: {path.name} has web step(s) {', '.join(web)}; studio agents work on case "
                             "data, which must not leave the machine in search queries")
        return WorkflowProvider(name, label, bool(spec.get("default")), path=path)
    if "url" in spec:
        return HttpProvider(name, label, bool(spec.get("default")), url=spec["url"],
                            timeout=float(spec.get("timeout", 1800)))
    raise AgentError(f"agent {name}: needs `workflow` or `url`")


def load_config(path: Path) -> StudioConfig:
    raw_text = path.read_text(encoding="utf-8")
    try:
        raw = StudioRaw.model_validate(yaml.safe_load(raw_text) or {})
    except ValidationError as e:
        raise AgentError(f"{path}: invalid studio.yaml: {e}") from None
    base = path.parent
    agents = {k: _provider(k, v, base) for k, v in raw.agents.items()}
    missing = {"doc", "context", "report"} - set(agents)
    if missing:
        raise AgentError(f"{path}: agents needs {', '.join(sorted(missing))}")
    extras = {k: _provider(k, v, base) for k, v in raw.extra_agents.items()}
    try:
        pulls = load_pulls(raw.model_dump(), base)
    except DataError as e:
        raise AgentError(f"{path}: {e}") from None
    return StudioConfig(agents, extras, str(raw.public_url or "http://127.0.0.1:8090").rstrip("/"), pulls)
