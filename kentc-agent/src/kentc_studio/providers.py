"""Who runs an agent job, and how to reach it.

- WorkflowProvider runs a kentc-agent workflow in-process on the configured LLM server. The workflow is named in the
  app manifest and found in the studio's shared agent library (studio.yaml `workflows`, default apps/workflows/), so
  any app may use any agent there. The result is the JSON answer of the workflow's last step. A local server serves
  one request at a time, so these jobs run one by one.
- HttpProvider calls an external agent: another process or host, any implementation. It POSTs
      {"role", "app", "case_id", "job_id", "inputs", "documents": [{"name", "lane", "url"}], "materials"}
  and expects back a JSON object (the result itself, or {"result": {...}}). These jobs run in parallel with
  the local ones.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kentc_agent.adapters.llm import LLMClient
from kentc_agent.adapters.tools import CORE_TOOLS, ToolContext
from kentc_agent.config import Settings
from kentc_agent.ports import Events
from kentc_agent.workflow import Runner, Workflow, WorkflowError, load, resolve_inputs

# Studio agents read uploaded (untrusted) documents: a prompt injected into a document must not reach a shell, so
# their workflows may not offer these tools; nor may they have web steps, so case data never leaves the machine in
# search queries.
UNTRUSTED_INPUT_DENY = {"bash"}


class AgentError(RuntimeError):
    pass


@dataclass
class Provider:
    name: str
    label: str
    default: bool = False

    @property
    def local(self) -> bool:          # runs on the local model: one at a time
        return False

    @property
    def schema(self) -> dict[str, Any] | None:
        """The result shape, when the studio can know it before the agent runs."""
        return None

    def describe(self) -> str:
        raise NotImplementedError

    def run(self, *, case_dir: Path, job_dir: Path, inputs: dict[str, Any], events: Events, settings: Settings,
            llm: LLMClient, request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


@dataclass
class WorkflowProvider(Provider):
    path: Path = Path()
    inputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    result_schema: dict[str, Any] | None = None

    @property
    def local(self) -> bool:
        return True

    @property
    def schema(self) -> dict[str, Any] | None:
        return self.result_schema

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


def workflow_path(library: Path, name: str) -> Path:
    """An agent workflow by name (`doc-agent`) in the studio's shared library."""
    for ext in (".yaml", ".yml"):
        if (library / f"{name}{ext}").is_file():
            return (library / f"{name}{ext}").resolve()
    return (library / f"{name}.yaml").resolve()


def _offered_tools(wf: Workflow) -> set[str]:
    """Every tool some prompt step of `wf` offers the model."""
    out: set[str] = set()
    for step in wf.steps:
        if step.kind == "prompt":
            names = step.spec.get("tools", wf.tools)
            out |= set(CORE_TOOLS if names is None else names)
    return out


def make_provider(name: str, spec: dict[str, Any], library: Path, inputs: set[str]) -> Provider:
    """`spec["workflow"]`: a workflow name in `library`. `inputs`: what the studio passes this agent; a workflow must
    declare exactly those (it refuses unknown inputs) and may not require any other."""
    label = str(spec.get("label") or name)
    if spec.get("workflow"):
        path = workflow_path(library, str(spec["workflow"]))
        if not path.is_file():
            raise AgentError(f"agent {name}: workflow {spec['workflow']!r} not found in {library} (give its name, "
                             "without .yaml)")
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
        missing = sorted(inputs - set(wf.inputs))
        extra = sorted(k for k, v in wf.inputs.items() if k not in inputs and (v or {}).get("required"))
        if missing or extra:
            raise AgentError(f"agent {name}: {path.name} must declare the inputs {', '.join(sorted(inputs))}"
                             + (f" (missing {', '.join(missing)})" if missing else "")
                             + (f"; the studio never passes required {', '.join(extra)}" if extra else ""))
        last = wf.steps[-1]
        schema = last.spec.get("schema") if last.kind == "prompt" and last.spec.get("format") == "json" else None
        if schema is None:
            raise AgentError(f"agent {name}: the last step of {path.name} must answer with format: json and a schema")
        return WorkflowProvider(name, label, bool(spec.get("default")), path=path, inputs=wf.inputs,
                                result_schema=schema)
    if spec.get("url"):
        return HttpProvider(name, label, bool(spec.get("default")), url=str(spec["url"]),
                            timeout=float(spec.get("timeout", 1800)))
    raise AgentError(f"agent {name}: needs `workflow` or `url`")
