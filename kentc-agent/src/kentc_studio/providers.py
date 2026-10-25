"""Who runs an agent job, and how to reach it.

- LocalAgentProvider runs an agent the app manifest declares inline: a contract (the studio's fixed inputs for its
  role, an `output` shape, `checks`, `tools`, `max_turns`) equipped with skills (kentc-agent/skills/<name>.md).
  It runs in-process on the configured LLM server as a one-step kentc-agent workflow built in memory: the task
  message lists the inputs (file inputs inlined), the skills are the system prompt, and the agent works until its
  answer fits the shape and passes the checks, or its turn budget is spent. A local server serves one request at
  a time, so these jobs run one by one.
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
from kentc_agent.checks import Rule, parse_checks
from kentc_agent.config import Settings
from kentc_agent.ports import Events
from kentc_agent.skills import SkillError, load_skills
from kentc_agent.workflow import Runner, Step, Workflow

# Studio agents read uploaded (untrusted) documents: a prompt injected into a document must not reach a shell.
UNTRUSTED_INPUT_DENY = {"bash"}
EFFORTS = ("none", "low", "medium", "high")

# What each studio input is, for the task message. File inputs the studio prepares are inlined; `file` is a
# document the agent reads itself.
INPUT_NOTES = {
    "case_brief": "the case",
    "file": "the document to work on, in the case folder - read it",
    "feedback": "the analyst's feedback on your previous answer",
    "previous": "your previous answer, which the feedback refers to",
    "instruction": "the analyst's prompt for this version",
    "lane_file": "the lane's documents, converted to text",
    "materials_file": "the case materials",
    "previous_report_file": "the previous report version",
}
INLINED = ("lane_file", "materials_file", "previous_report_file")


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


def task_prompt(inputs: set[str]) -> str:
    """The task message (a Jinja template over `inputs`): the given inputs, then the inlined files. Empty inputs
    are left out; what to do with them is the skills' business."""
    order = [k for k in INPUT_NOTES if k in inputs and k not in INLINED] + sorted(inputs - set(INPUT_NOTES))
    lines = ["Do the task your skills describe, with these inputs."]
    lines += [f"{{% if inputs.{k} %}}- {k} ({INPUT_NOTES.get(k, 'input')}): {{{{ inputs.{k} }}}}\n{{% endif %}}"
              for k in order]
    lines += [f"{{% if inputs.{k} %}}\n### {k} ({INPUT_NOTES[k]})\n{{{{ read_file(inputs.{k}) }}}}\n{{% endif %}}"
              for k in INLINED if k in inputs]
    return "\n".join(lines[:1]) + "\n" + "".join(lines[1:])


@dataclass
class LocalAgentProvider(Provider):
    skills: str = ""                                  # the skill texts, loaded at studio start
    tools: list[str] = field(default_factory=list)
    max_turns: int = 100
    effort: str | None = None
    output: dict[str, Any] = field(default_factory=dict)
    checks: list[Rule] = field(default_factory=list)
    inputs: set[str] = field(default_factory=set)
    source: Path = Path()                             # the app manifest declaring the agent

    @property
    def local(self) -> bool:
        return True

    @property
    def schema(self) -> dict[str, Any] | None:
        return self.output

    def describe(self) -> str:
        return f"local agent {self.label} ({self.source.name})"

    def workflow(self) -> Workflow:
        step = Step(self.name, "prompt", {"prompt": task_prompt(self.inputs), "tools": self.tools,
                                          "format": "json", "schema": self.output, "checks": self.checks,
                                          "repairs": None})
        return Workflow(self.label, "", {k: {"default": ""} for k in sorted(self.inputs)}, "", self.tools,
                        self.max_turns, self.effort, [step], self.source, self.skills)

    def run(self, *, case_dir, job_dir, inputs, events, settings, llm, request):
        """Uploaded documents are untrusted: the agent's reads stay inside the case folder."""
        ctx = ToolContext(case_dir, settings, llm, events, confine_reads=True)
        given = {k: inputs.get(k) or "" for k in self.inputs}
        state = Runner(self.workflow(), ctx, given, job_dir).run()
        return state["steps"][self.name]["data"]


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


def make_provider(name: str, spec: dict[str, Any], skills: Path, inputs: set[str], source: Path) -> Provider:
    """An agent declared in an app manifest. `spec`: a local agent (skills, output, checks, tools, max_turns,
    effort) or an external one (url, timeout). `skills`: the skill library. `inputs`: what the studio passes this
    agent's role. Every mistake is reported here, when the studio loads."""
    label = str(spec.get("label") or name)
    local = [k for k in ("skills", "output", "checks") if spec.get(k)]
    if spec.get("url"):
        if local:
            raise AgentError(f"agent {name}: an external (url) agent takes no {', '.join(local)}")
        return HttpProvider(name, label, bool(spec.get("default")), url=str(spec["url"]),
                            timeout=float(spec.get("timeout", 1800)))
    try:
        text = load_skills(skills, list(spec.get("skills") or []))
    except SkillError as e:
        raise AgentError(f"agent {name}: {e} (skills live in {skills})") from None
    output = spec.get("output")
    if not isinstance(output, dict) or not output:
        raise AgentError(f"agent {name}: output must give the JSON answer's shape, e.g. {{summary: string}}")
    tools = list(spec.get("tools") if spec.get("tools") is not None else ["read"])
    unknown = [t for t in tools if t not in CORE_TOOLS]
    if unknown:
        raise AgentError(f"agent {name}: unknown tool(s) {', '.join(unknown)}; available: {', '.join(CORE_TOOLS)}")
    unsafe = sorted(set(tools) & UNTRUSTED_INPUT_DENY)
    if unsafe:
        raise AgentError(f"agent {name}: offers {', '.join(unsafe)}; studio agents read untrusted uploaded documents, "
                         "so they get no shell")
    effort = spec.get("effort")
    if effort is not None and effort not in EFFORTS:
        raise AgentError(f"agent {name}: effort must be one of {', '.join(EFFORTS)}")
    try:
        rules = parse_checks(spec.get("checks"), output)
    except ValueError as e:
        raise AgentError(f"agent {name}: checks: {e}") from None
    return LocalAgentProvider(name, label, bool(spec.get("default")), skills=text, tools=tools,
                              max_turns=int(spec.get("max_turns", 100)), effort=effort, output=output,
                              checks=rules, inputs=set(inputs), source=source)
