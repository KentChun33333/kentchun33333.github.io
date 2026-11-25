"""Finite-State Workflow (FSM) engine: deterministic macro controller + fresh single-agent states.

Design principle:
- The runtime owns control (macro states, allowlisted transitions, budgets, retries, no-progress detection, exit gates).
- Skills own procedures (per-state lazy-loaded Markdown SOPs from `skills/`).
- One fresh `Agent` executes each prompt state in an isolated session (`100% fresh`, zero cross-state chat bleed).
- Independent runtime validators establish objective evidence (real command exit codes, file existence, git diff,
  JSON schema + `checks.py` rules, deterministic expressions).

Canonical YAML format uses `entry:` + `states:` (with `prompt`, `gate`, `ask`, `web` state kinds and `routes:`).
Legacy linear `steps:` lists are compiled at load time into the exact same FSM representation (`step[i] -> step[i+1] -> DONE`),
so there is only ONE workflow engine in the repository.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jinja2 import StrictUndefined, TemplateError
from jinja2.sandbox import SandboxedEnvironment

from .adapters.session import Session
from .adapters.tools import CORE_TOOLS, ToolContext, ToolError, inside, reject_unsupported, rel, resolve
from .adapters.web_research import run_web_agent
from .agent import Aborted, Agent, build_tools
from .checks import check_rules
from .config import STATE_DIR
from .skills import SkillError, load_skills

TERMINAL_STATES = ("DONE", "PAUSE", "ESCALATE")
TERMINAL_SET = set(TERMINAL_STATES)

TOP_KEYS = {
    "name", "description", "version", "inputs", "instructions", "tools", "max_turns", "effort",
    "skills_dir", "runtime", "entry", "states", "steps",
}
RUNTIME_KEYS = {
    "max_cycles", "max_retries_per_state", "max_total_tokens", "max_step_seconds",
    "no_progress_limit", "fail_closed_on_unknown_event",
}
STATE_KEYS = {
    "id", "kind", "macro_phase", "prompt", "gate", "ask", "web",
    "tools", "skills", "max_turns", "max_searches", "foreach", "max_items", "approve",
    "effort", "format", "schema", "checks", "output", "when", "options", "default",
    "validators", "routes", "route_on",
}
PROMPT_ONLY = {"tools", "skills", "max_turns", "effort", "format", "schema", "checks"}
ASK_ONLY = {"options", "default"}
WEB_ONLY = {"max_searches", "foreach", "max_items", "approve"}
GATE_ONLY = {"gate"}
NOT_FOR = {
    "prompt": ASK_ONLY | WEB_ONLY | GATE_ONLY,
    "ask": PROMPT_ONLY | WEB_ONLY | GATE_ONLY | {"validators"},
    "web": ASK_ONLY | GATE_ONLY | {"tools", "skills", "format", "schema", "checks", "validators"},
    "gate": PROMPT_ONLY | ASK_ONLY | WEB_ONLY | {"output"},
}

WEB_MAX_TURNS = 8
WEB_MAX_SEARCHES = 6
WEB_MAX_ITEMS = 4
DEFAULT_MAX_CYCLES = 20
DEFAULT_MAX_RETRIES_PER_STATE = 3
DEFAULT_NO_PROGRESS_LIMIT = 2

PLAN_PROMPT = """Plan web research for the work so far. List the outside facts it still needs that the workspace \
files cannot give: facts that change over time or are public (regulation, market data, news, public figures). Most \
important first; at most {cap} tasks; an empty list if nothing is needed.
Each task is self-contained and generic: never put names, account numbers, amounts or other confidential details in \
it, because it becomes a public web search. Describe what to find; do not assert document numbers, dates or names \
you are not sure of - the web agent will look them up."""
PLAN_SCHEMA = {"web_tasks": [{"topic": "2-4 words", "task": "what to research, one or two sentences",
                              "why": "the gap it closes"}]}
ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
REF_RE = re.compile(r"steps\.([A-Za-z_][A-Za-z0-9_]*)|steps\[['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\]")

AskUser = Callable[[str, str, list[str] | None, str | None], str]


class WorkflowError(RuntimeError):
    pass


class NeedsAnswer(WorkflowError):
    """A human gate with no answer yet: the run stops cleanly there; resume it with the answer."""

    def __init__(self, step: str, message: str, options: list[str] | None, default: str | None) -> None:
        super().__init__(f"{step}: needs a human answer. Run in a terminal, or resume with --answer {step}=<value>")
        self.gate = {"step": step, "message": message, "options": options, "default": default}


@dataclass
class Step:
    id: str
    kind: str                  # "prompt" | "gate" | "ask" | "web"
    spec: dict[str, Any]


@dataclass
class RuntimePolicy:
    max_cycles: int = DEFAULT_MAX_CYCLES
    max_retries_per_state: int = DEFAULT_MAX_RETRIES_PER_STATE
    max_total_tokens: int = 0           # 0 = unlimited
    max_step_seconds: int = 300
    no_progress_limit: int = DEFAULT_NO_PROGRESS_LIMIT
    fail_closed_on_unknown_event: bool = True


@dataclass
class Workflow:
    name: str
    description: str
    inputs: dict[str, dict[str, Any]]
    instructions: str
    tools: list[str] | None
    max_turns: int | None
    effort: str | None
    steps: list[Step]
    path: Path
    skills: str = ""                    # verbatim skill texts (used by studio single-step agents)
    entry: str = ""
    states: dict[str, Step] = field(default_factory=dict)
    runtime: RuntimePolicy = field(default_factory=RuntimePolicy)
    skills_dir: Path | None = None

    def __post_init__(self) -> None:
        if not self.states and self.steps:
            self.states = {s.id: s for s in self.steps}
            for i, s in enumerate(self.steps):
                if "routes" not in s.spec:
                    nxt = self.steps[i + 1].id if i + 1 < len(self.steps) else "DONE"
                    s.spec = {**s.spec, "routes": {"default": nxt}}
        if not self.steps and self.states:
            self.steps = list(self.states.values())
        if not self.entry and self.steps:
            self.entry = self.steps[0].id


# ---------------------------------------------------------------------- loading and validation
def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def _check_tools(where: str, tools: Any) -> None:
    if tools is None:
        return
    if not isinstance(tools, list):
        raise WorkflowError(f"{where}: tools must be a list")
    unknown = [t for t in tools if t not in CORE_TOOLS]
    if unknown:
        raise WorkflowError(f"{where}: unknown tool(s) {', '.join(unknown)}; available: {', '.join(CORE_TOOLS)}")


def _check_validators(where: str, validators: Any) -> None:
    if validators is None:
        return
    if not isinstance(validators, list):
        raise WorkflowError(f"{where}: validators must be a list")
    allowed = {"command", "file_exists", "git_diff", "expr", "timeout", "name"}
    for i, v in enumerate(validators):
        if not isinstance(v, dict):
            raise WorkflowError(f"{where}.validators[{i}]: must be a mapping")
        unknown = set(v) - allowed
        if unknown:
            raise WorkflowError(f"{where}.validators[{i}]: unknown key(s): {', '.join(sorted(unknown))}")
        checks = [k for k in ("command", "file_exists", "git_diff", "expr") if k in v]
        if len(checks) != 1:
            raise WorkflowError(f"{where}.validators[{i}]: needs exactly one of command, file_exists, git_diff or expr")


def _parse_runtime(raw: Any) -> RuntimePolicy:
    if raw is None:
        return RuntimePolicy()
    if not isinstance(raw, dict):
        raise WorkflowError("runtime must be a mapping")
    unknown = set(raw) - RUNTIME_KEYS
    if unknown:
        raise WorkflowError(f"runtime: unknown key(s): {', '.join(sorted(unknown))}")
    policy = RuntimePolicy()
    for key in ("max_cycles", "max_retries_per_state", "max_total_tokens", "max_step_seconds", "no_progress_limit"):
        if key in raw:
            val = raw[key]
            if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                raise WorkflowError(f"runtime.{key}: must be a whole number >= 0")
            setattr(policy, key, val)
    if "fail_closed_on_unknown_event" in raw:
        if not isinstance(raw["fail_closed_on_unknown_event"], bool):
            raise WorkflowError("runtime.fail_closed_on_unknown_event: must be true or false")
        policy.fail_closed_on_unknown_event = raw["fail_closed_on_unknown_event"]
    return policy


def _validate_state(sid: str, s: dict[str, Any]) -> Step:
    if not ID_RE.match(sid) or sid in TERMINAL_SET:
        raise WorkflowError(f"state id {sid!r} must be a valid identifier and not one of {TERMINAL_STATES}")
    kinds = [k for k in ("prompt", "gate", "ask", "web") if k in s]
    if len(kinds) != 1:
        raise WorkflowError(f"{sid}: needs exactly one of prompt, ask or web (or gate)")
    kind = kinds[0]
    bad = set(s) - STATE_KEYS | (set(s) & NOT_FOR[kind])
    if bad:
        raise WorkflowError(f"{sid}: key(s) not valid for a {kind} step: {', '.join(sorted(bad))}")
    if kind == "web" and str(s["web"]).strip() == "plan" and "foreach" in s:
        raise WorkflowError(f"{sid}: web: plan works out its own tasks; drop foreach")
    if "foreach" in s and not isinstance(s["foreach"], str):
        raise WorkflowError(f"{sid}: foreach must be an expression giving a list, e.g. data.web_tasks")
    if "approve" in s and not isinstance(s["approve"], bool):
        raise WorkflowError(f"{sid}: approve must be true or false")
    _check_tools(sid, s.get("tools"))
    _check_turns(sid, s.get("max_turns"))
    if "skills" in s and (not isinstance(s["skills"], list) or not all(isinstance(x, str) for x in s["skills"])):
        raise WorkflowError(f"{sid}: skills must be a list of skill names")
    if s.get("format", "text") not in ("text", "json"):
        raise WorkflowError(f"{sid}: format must be text or json")
    if "schema" in s and not isinstance(s["schema"], dict):
        raise WorkflowError(f"{sid}: schema must be a mapping of key -> shape")
    if "options" in s and not isinstance(s["options"], list):
        raise WorkflowError(f"{sid}: options must be a list")
    _check_validators(sid, s.get("validators"))
    if "routes" in s:
        if not isinstance(s["routes"], dict) or not s["routes"]:
            raise WorkflowError(f"{sid}: routes must be a non-empty mapping of event -> target state")
        for ev, target in s["routes"].items():
            if not isinstance(ev, str) or not isinstance(target, str):
                raise WorkflowError(f"{sid}.routes: keys and targets must be strings")
    return Step(sid, kind, dict(s))


def load(path: Path) -> Workflow:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise WorkflowError(f"{path}: invalid YAML: {e}") from None
    if not isinstance(raw, dict):
        raise WorkflowError(f"{path}: workflow must be a YAML mapping")
    unknown = set(raw) - TOP_KEYS
    if unknown:
        raise WorkflowError(f"{path}: unknown top-level key(s): {', '.join(sorted(unknown))}")
    has_states = "states" in raw
    has_steps = "steps" in raw
    if has_states == has_steps:
        raise WorkflowError(f"{path}: declare either `states` (FSM) or `steps` (linear), not both/neither")

    _check_tools("tools", raw.get("tools"))
    _check_turns("max_turns", raw.get("max_turns"))
    runtime = _parse_runtime(raw.get("runtime"))
    inputs = {k: v if isinstance(v, dict) else {"default": v} for k, v in (raw.get("inputs") or {}).items()}
    skills_dir = (path.parent / raw["skills_dir"]).resolve() if isinstance(raw.get("skills_dir"), str) else None

    steps: list[Step] = []
    states: dict[str, Step] = {}
    if has_states:
        raw_states = raw.get("states")
        if not isinstance(raw_states, dict) or not raw_states:
            raise WorkflowError(f"{path}: `states` must be a non-empty mapping")
        for sid, spec in raw_states.items():
            if not isinstance(spec, dict):
                raise WorkflowError(f"states.{sid}: must be a mapping")
            st = _validate_state(str(sid), spec)
            steps.append(st)
            states[st.id] = st
        entry = str(raw.get("entry") or steps[0].id)
        if entry not in states:
            raise WorkflowError(f"{path}: entry state {entry!r} is not declared in states")
        # Default sequential route if omitted on a state
        for i, st in enumerate(steps):
            if "routes" not in st.spec:
                nxt = steps[i + 1].id if i + 1 < len(steps) else "DONE"
                st.spec["routes"] = {"default": nxt}
    else:
        raw_steps = raw.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise WorkflowError(f"{path}: needs a non-empty `steps` list")
        seen: set[str] = set()
        for i, s in enumerate(raw_steps):
            if not isinstance(s, dict):
                raise WorkflowError(f"steps[{i}]: must be a mapping")
            sid = s.get("id") or f"step{i + 1}"
            if sid in seen:
                raise WorkflowError(f"steps[{i}]: duplicate id {sid!r}")
            st = _validate_state(sid, s)
            later = {a or b for a, b in REF_RE.findall("\n".join(_strings(s)))} - seen
            if later:
                raise WorkflowError(f"{sid}: refers to steps that have not run yet: {', '.join(sorted(later))}")
            seen.add(sid)
            steps.append(st)
            states[st.id] = st
        for i, st in enumerate(steps):
            if "routes" not in st.spec:
                nxt = steps[i + 1].id if i + 1 < len(steps) else "DONE"
                st.spec["routes"] = {"default": nxt}
        entry = steps[0].id

    # Validate route targets and PromptLoop exit-gate invariant
    has_gate = any(st.kind == "gate" for st in steps)
    for st in steps:
        for ev, target in (st.spec.get("routes") or {}).items():
            if target not in states and target not in TERMINAL_SET:
                raise WorkflowError(f"{st.id}.routes[{ev!r}]: unknown target state {target!r}")
            if has_gate and st.kind == "prompt" and target == "DONE":
                raise WorkflowError(
                    f"{st.id}.routes[{ev!r}]: prompt state cannot route directly to DONE when a deterministic gate exists; route through a gate state"
                )

    return Workflow(
        name=raw.get("name") or path.stem,
        description=raw.get("description") or "",
        inputs=inputs,
        instructions=raw.get("instructions") or "",
        tools=raw.get("tools"),
        max_turns=raw.get("max_turns"),
        effort=raw.get("effort"),
        steps=steps,
        path=path,
        entry=entry,
        states=states,
        runtime=runtime,
        skills_dir=skills_dir,
    )


def resolve_inputs(wf: Workflow, given: dict[str, str]) -> dict[str, Any]:
    unknown = set(given) - set(wf.inputs)
    if unknown:
        raise WorkflowError(f"unknown input(s): {', '.join(sorted(unknown))}; declared: {', '.join(wf.inputs) or '-'}")
    out = {}
    for k, spec in wf.inputs.items():
        if k in given:
            out[k] = given[k]
        elif "default" in spec:
            out[k] = spec["default"]
        elif spec.get("required", True):
            raise WorkflowError(f"missing input {k!r}" + (f" ({spec['description']})" if spec.get("description") else ""))
        else:
            out[k] = None
    return out


def parse_json_object(text: str) -> dict[str, Any]:
    """Accept a complete JSON object, optionally in one whole code fence; never repair missing evidence."""
    text = text.strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON object key")
            result[key] = value
        return result

    def invalid_constant(value: str) -> Any:
        raise ValueError(f"invalid JSON constant {value}")

    data = json.loads(text, object_pairs_hook=object_pairs, parse_constant=invalid_constant)
    if not isinstance(data, dict):
        raise ValueError("the reply is not a JSON object")
    return data


# ---------------------------------------------------------------------- output shape
SCALARS: dict[str, Any] = {"string": str, "number": (int, float), "integer": int, "boolean": bool}
MAX_SHAPE_ERRORS = 8


def check_shape(data: Any, shape: Any) -> list[str]:
    """Validate `data` against a step's `schema`, returning error strings ([] when valid)."""
    errors: list[str] = []
    _check(data, shape, "", errors)
    return errors


def _kind(value: Any) -> str:
    return "null" if value is None else "boolean" if isinstance(value, bool) else \
        "number" if isinstance(value, int | float) else "string" if isinstance(value, str) else \
        "array" if isinstance(value, list) else "object" if isinstance(value, dict) else type(value).__name__


def _check(value: Any, shape: Any, where: str, errors: list[str]) -> Any:
    label = repr(where) if where else "the reply"
    if isinstance(shape, dict):
        if not isinstance(value, dict):
            errors.append(f"{label} must be an object, got {_kind(value)}")
            return value
        for key, sub in shape.items():
            path = f"{where}.{key}" if where else str(key)
            if key in value:
                value[key] = _check(value[key], sub, path, errors)
            else:
                errors.append(f"missing key {path!r}")
        return value
    if isinstance(shape, list):
        if not isinstance(value, list):
            errors.append(f"{label} must be an array, got {_kind(value)}")
        elif shape:
            for i, item in enumerate(value):
                value[i] = _check(item, shape[0], f"{where}[{i}]", errors)
        return value
    if isinstance(shape, bool):
        expected: Any = bool
        name = "boolean"
    elif isinstance(shape, int | float):
        expected, name = (int, float), "number"
    elif isinstance(shape, str) and shape.strip().lower() in SCALARS:
        name = shape.strip().lower()
        expected = SCALARS[name]
    elif isinstance(shape, str) and "|" in shape:
        options = [o.strip() for o in shape.split("|")]
        match = [o for o in options if isinstance(value, str) and o.lower() == value.strip().lower()]
        if match:
            return match[0]
        errors.append(f"{label} must be one of {' | '.join(options)}, got {_kind(value)}")
        return value
    elif isinstance(shape, str):
        expected, name = str, "string"
    else:
        return value
    if not isinstance(value, expected) or isinstance(value, bool) and name != "boolean":
        errors.append(f"{label} must be a {name}, got {_kind(value)}")
    return value


# ---------------------------------------------------------------------- templating
class _Env(SandboxedEnvironment):
    """Mapping keys win over attributes: `data.items`, `steps.values` mean the keys, not dict methods."""

    def getattr(self, obj: Any, attribute: str) -> Any:
        if isinstance(obj, dict) and attribute in obj:
            return obj[attribute]
        return super().getattr(obj, attribute)


def _pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=1, default=str)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------------- execution
class Runner:
    """Deterministic PromptLoop FSM controller running one fresh Agent per prompt state."""

    def __init__(self, wf: Workflow, ctx: ToolContext, inputs: dict[str, Any], run_dir: Path, *,
                 prompt: str = "", ask_user: AskUser | None = None, answers: dict[str, str] | None = None) -> None:
        self.wf, self.ctx, self.inputs, self.dir = wf, ctx, inputs, run_dir
        self.ask_user, self.answers = ask_user, answers or {}
        self.state: dict[str, Any] = {
            "workflow": str(wf.path),
            "name": wf.name,
            "prompt": prompt,
            "inputs": inputs,
            "status": "running",
            "current_state": wf.entry,
            "cycles": 0,
            "execution_seq": 0,
            "event_seq": 0,
            "total_tokens": 0,
            "in_flight": None,
            "state_failures": {},
            "last_failure_sig": None,
            "no_progress_count": 0,
            "handoff_notes": [],
            "steps": {},
            "trace": [],
            "history": [],
        }
        state_file = run_dir / "state.json"
        if state_file.is_file():
            loaded = json.loads(state_file.read_text(encoding="utf-8"))
            self.state.update(loaded)
            self.state["inputs"] = inputs
            if prompt:
                self.state["prompt"] = prompt
        self.env = _Env(undefined=StrictUndefined, keep_trailing_newline=True)
        self.env.globals.update(glob=self._glob, read_file=self._read_file, documents=self._documents)
        self.env.filters.update(fromjson=json.loads, json=_pretty_json, slug=_slug)
        self.agent: Agent | None = None
        self._skills_root = self._resolve_skills_dir()

    def _resolve_skills_dir(self) -> Path:
        if self.wf.skills_dir and self.wf.skills_dir.is_dir():
            return self.wf.skills_dir
        ws_skills = self.ctx.workspace / "skills"
        if ws_skills.is_dir():
            return ws_skills
        return Path(__file__).resolve().parents[2] / "skills"

    def close(self) -> None:
        if self.agent is not None:
            self.agent.close()

    # -------------------------------------------------------------- template helpers
    def _glob(self, pattern: str) -> list[str]:
        ws = self.ctx.workspace.resolve()
        return sorted(str(p.relative_to(self.ctx.workspace)) for p in self.ctx.workspace.glob(pattern)
                      if p.is_file() and (not self.ctx.confine_reads or p.resolve().is_relative_to(ws)))

    def _read_file(self, path: str, max_chars: int = 0) -> str:
        p = inside(self.ctx, path, "reads") if self.ctx.confine_reads else resolve(self.ctx, path)
        text = p.read_text(encoding="utf-8")
        if max_chars > 0 and len(text) > max_chars:
            shown = rel(self.ctx, p)
            return (text[:max_chars]
                    + f"\n\n[... {len(text) - max_chars:,} chars truncated; read {shown} with offset/limit for the rest ...]")
        return text

    def _documents(self, folder: str) -> list[str]:
        root = inside(self.ctx, folder, "reads") if self.ctx.confine_reads else resolve(self.ctx, folder)
        if not root.is_dir():
            raise WorkflowError(f"documents({folder!r}): no such folder in {self.ctx.workspace}; fix the workflow "
                                "input that names it (with --resume latest -i KEY=VALUE to continue)")
        out = []
        for p in sorted(root.iterdir()):
            if not p.is_file() or p.name.startswith("."):
                continue
            try:
                reject_unsupported(p)
            except ToolError as e:
                self.ctx.events.status("workflow", f"skipping {e}")
                continue
            out.append(rel(self.ctx, p))
        return out

    def vars(self, **extra: Any) -> dict[str, Any]:
        steps = {
            sid: {
                "output": s.get("output", ""),
                "data": s.get("data"),
                "status": s.get("status", ""),
                "evidence": s.get("evidence", []),
            }
            for sid, s in self.state["steps"].items()
        }
        data: dict[str, Any] = {}
        for s in self.state["steps"].values():
            if isinstance(s.get("data"), dict):
                data.update(s["data"])
        return {
            "prompt": self.state.get("prompt", ""),
            "inputs": self.inputs,
            "steps": steps,
            "data": data,
            "run_dir": str(self.dir),
            "trace": self.state["trace"],
            "workspace": str(self.ctx.workspace),
            "cycles": self.state["cycles"],
            **extra,
        }

    def render(self, text: Any, **extra: Any) -> str:
        if not isinstance(text, str):
            return "" if text is None else str(text)
        try:
            return self.env.from_string(text).render(self.vars(**extra))
        except TemplateError as e:
            raise WorkflowError(f"template error: {e}") from None

    def expr(self, text: str, **extra: Any) -> Any:
        try:
            return self.env.compile_expression(text)(self.vars(**extra))
        except TemplateError as e:
            raise WorkflowError(f"expression {text!r}: {e}") from None

    # -------------------------------------------------------------- persistence & audit
    def save(self) -> None:
        _atomic_write(self.dir / "state.json", json.dumps(self.state, indent=2, ensure_ascii=False, default=str))

    def _append_event(self, event: dict[str, Any]) -> None:
        self.state["event_seq"] = int(self.state.get("event_seq") or 0) + 1
        row = {"seq": self.state["event_seq"], "ts": time.time(), **event}
        self.dir.mkdir(parents=True, exist_ok=True)
        with (self.dir / "events.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    def trace(self, actor: str, step: str, event: str) -> None:
        self.state["trace"].append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "actor": actor, "step": step,
                                    "event": event})

    # -------------------------------------------------------------- objective validators
    def _run_validators(self, step: Step, *, data: Any = None) -> tuple[bool, list[dict[str, Any]]]:
        """Run independent runtime validators; never trust self-reported agent claims."""
        validators = step.spec.get("validators") or []
        evidence: list[dict[str, Any]] = []
        all_ok = True
        for i, v in enumerate(validators):
            name = str(v.get("name") or f"validator_{i + 1}")
            if "command" in v:
                cmd = self.render(v["command"])
                timeout = int(v.get("timeout") or self.wf.runtime.max_step_seconds or 300)
                try:
                    proc = subprocess.run(
                        cmd,
                        shell=True,
                        cwd=str(self.ctx.workspace),
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                    passed = proc.returncode == 0
                    evidence.append({
                        "name": name,
                        "type": "command",
                        "command": cmd,
                        "exit_code": proc.returncode,
                        "passed": passed,
                        "stdout": (proc.stdout or "")[-2000:],
                        "stderr": (proc.stderr or "")[-2000:],
                    })
                except subprocess.TimeoutExpired:
                    passed = False
                    evidence.append({
                        "name": name,
                        "type": "command",
                        "command": cmd,
                        "exit_code": -1,
                        "passed": False,
                        "error": f"timed out after {timeout}s",
                    })
            elif "file_exists" in v:
                target_rel = self.render(v["file_exists"])
                try:
                    p = inside(self.ctx, target_rel, "reads")
                    passed = p.is_file() and p.stat().st_size > 0
                    evidence.append({"name": name, "type": "file_exists", "path": target_rel, "passed": passed})
                except ToolError as exc:
                    passed = False
                    evidence.append({"name": name, "type": "file_exists", "path": target_rel, "passed": False, "error": str(exc)})
            elif "git_diff" in v:
                proc = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=str(self.ctx.workspace),
                    capture_output=True,
                    text=True,
                )
                has_diff = proc.returncode == 0 and bool(proc.stdout.strip())
                passed = has_diff if bool(v["git_diff"]) else not has_diff
                evidence.append({
                    "name": name,
                    "type": "git_diff",
                    "passed": passed,
                    "summary": proc.stdout.strip()[:1000],
                })
            elif "expr" in v:
                try:
                    passed = bool(self.expr(str(v["expr"]), step_data=data, evidence=evidence))
                    evidence.append({"name": name, "type": "expr", "expr": str(v["expr"]), "passed": passed})
                except WorkflowError as exc:
                    passed = False
                    evidence.append({"name": name, "type": "expr", "expr": str(v["expr"]), "passed": False, "error": str(exc)})
            else:
                passed = False
            if not passed:
                all_ok = False
        return all_ok, evidence

    def _failure_signature(self, state_id: str, evidence: list[dict[str, Any]]) -> str:
        failed_parts = [
            f"{e.get('name')}:{e.get('exit_code', '')}:{e.get('error', '')}:{str(e.get('stderr', ''))[-200:]}"
            for e in evidence if not e.get("passed")
        ]
        raw = f"{state_id}|{'|'.join(failed_parts)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _choose_next_state(self, step: Step, event: str) -> str:
        routes: dict[str, str] = step.spec.get("routes") or {}
        if event in routes:
            return routes[event]
        # Case-insensitive match for human options / string events
        for k, target in routes.items():
            if k.lower() == event.lower():
                return target
        if "default" in routes:
            return routes["default"]
        if self.wf.runtime.fail_closed_on_unknown_event:
            self.trace("SYS", step.id, f"unknown route event {event!r} -> ESCALATE (fail-closed)")
            return "ESCALATE"
        raise WorkflowError(f"{step.id}: no route for event {event!r}; declared: {sorted(routes)}")

    # -------------------------------------------------------------- main FSM loop
    def run(self) -> dict[str, Any]:
        # Crash reconciliation: if previous run died mid-state, log and re-execute current_state cleanly.
        if self.state.get("in_flight"):
            crashed = self.state["in_flight"]
            self._append_event({"type": "reconciled_crash", "in_flight": crashed})
            self.trace("SYS", str(crashed.get("state") or "?"), "reconciled crashed in-flight state on resume")
            self.state["current_state"] = crashed.get("state") or self.state["current_state"]
            self.state["in_flight"] = None
            self.state["status"] = "running"

        if self.state.get("status") in TERMINAL_SET:
            return self.state
        if self.state["current_state"] in TERMINAL_SET:
            self._commit_terminal(self.state["current_state"], "reconciled previously committed terminal transition")
            return self.state

        self.state["status"] = "running"
        self.save()

        policy = self.wf.runtime
        while self.state["current_state"] not in TERMINAL_SET:
            cur_id = self.state["current_state"]
            if cur_id not in self.wf.states:
                self._commit_terminal("ESCALATE", f"unknown current_state {cur_id!r}")
                break

            # Global budget guards before starting a new cycle
            if policy.max_cycles and self.state["cycles"] >= policy.max_cycles:
                self._commit_terminal("PAUSE", f"max_cycles ({policy.max_cycles}) reached")
                break
            if policy.max_total_tokens and self.state["total_tokens"] >= policy.max_total_tokens:
                self._commit_terminal("PAUSE", f"max_total_tokens ({policy.max_total_tokens}) exhausted")
                break

            step = self.wf.states[cur_id]
            self.state["execution_seq"] = int(self.state.get("execution_seq") or 0) + 1
            exec_id = f"exec-{self.state['execution_seq']:04d}"
            self.state["in_flight"] = {"execution_id": exec_id, "state": cur_id, "started": time.time()}
            rec = self.state["steps"][cur_id] = {"status": "running", "started": time.time(), "execution_id": exec_id}
            self.state.pop("waiting", None)
            self.save()

            try:
                # Optional `when` guard (skips state cleanly and follows default route)
                if "when" in step.spec and not self.expr(str(step.spec["when"])):
                    rec.update(status="skipped", output="", finished=time.time())
                    self.ctx.events.status(cur_id, "skipped (when is false)")
                    next_state = self._choose_next_state(step, "default")
                    self._finish_transition(cur_id, exec_id, "skipped", next_state, [])
                    continue

                self.state["cycles"] += 1
                self.ctx.events.status(cur_id, f"state {cur_id} (cycle {self.state['cycles']})")

                tokens_used = 0
                if step.kind == "prompt":
                    out, data, tokens_used = self._prompt_exec(step, exec_id)
                    rec["output"], rec["data"] = out, data
                elif step.kind == "web":
                    rec["output"], rec["data"] = self._web(step)
                elif step.kind == "ask":
                    rec["output"] = self._ask(step)
                elif step.kind == "gate":
                    rec["output"], rec["data"] = "", None

                self.state["total_tokens"] = int(self.state.get("total_tokens") or 0) + tokens_used

                # Write declared output artifact before running validators (so file_exists sees it)
                if step.spec.get("output") and step.kind not in ("web", "gate"):
                    target = inside(self.ctx, self.render(step.spec["output"]))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(rec["output"], encoding="utf-8")

                # Independent objective validators
                val_ok, evidence = self._run_validators(step, data=rec.get("data"))
                rec["evidence"] = evidence

                # Determine routing event
                if step.kind == "ask":
                    event = rec["output"]
                elif not val_ok:
                    event = "failed"
                elif step.spec.get("route_on"):
                    event = str(self.expr(str(step.spec["route_on"]), step_data=rec.get("data"), evidence=evidence))
                else:
                    event = "passed" if (step.spec.get("validators") or step.kind == "gate") else "default"

                rec.update(status="done" if val_ok else "failed_validation", finished=time.time())

                # Retry cap & no-progress detection on failed validations
                if not val_ok:
                    fails = self.state.setdefault("state_failures", {})
                    fails[cur_id] = int(fails.get(cur_id) or 0) + 1
                    sig = self._failure_signature(cur_id, evidence)
                    if sig == self.state.get("last_failure_sig"):
                        self.state["no_progress_count"] = int(self.state.get("no_progress_count") or 0) + 1
                    else:
                        self.state["last_failure_sig"] = sig
                        self.state["no_progress_count"] = 1

                    if policy.max_retries_per_state and fails[cur_id] >= policy.max_retries_per_state:
                        self._finish_transition(
                            cur_id, exec_id, "retry_limit", "ESCALATE", evidence,
                            terminal_reason=f"{cur_id}: max_retries_per_state ({policy.max_retries_per_state}) reached",
                        )
                        break
                    if policy.no_progress_limit and self.state["no_progress_count"] >= policy.no_progress_limit:
                        self._finish_transition(
                            cur_id, exec_id, "no_progress", "PAUSE", evidence,
                            terminal_reason=f"{cur_id}: no progress across {policy.no_progress_limit} attempts",
                        )
                        break
                else:
                    self.state.setdefault("state_failures", {})[cur_id] = 0
                    self.state["last_failure_sig"] = None
                    self.state["no_progress_count"] = 0

                next_state = self._choose_next_state(step, event)
                self._finish_transition(cur_id, exec_id, event, next_state, evidence)

            except NeedsAnswer as e:
                rec.update(status="waiting")
                self.state["waiting"] = e.gate
                self.state["status"] = "waiting"
                self.state["in_flight"] = None
                self.save()
                raise
            except Aborted:
                rec.update(status="failed", error="aborted by the user")
                self.state["status"] = "failed"
                self.state["in_flight"] = None
                self.save()
                raise
            except Exception as e:
                rec.update(status="failed", error=f"{type(e).__name__}: {e}")
                self.state["status"] = "failed"
                self.state["in_flight"] = None
                self.trace("SYS", cur_id, f"failed: {e}")
                self._append_event({"type": "error", "execution_id": exec_id, "state": cur_id, "error": str(e)})
                self.save()
                raise WorkflowError(f"step {cur_id!r} failed: {e}\nResume with: --resume {self.dir}") from e

        return self.state

    def _finish_transition(
        self, from_state: str, exec_id: str, event: str, to_state: str, evidence: list[dict[str, Any]],
        *, terminal_reason: str | None = None,
    ) -> None:
        self.state["in_flight"] = None
        self.state["current_state"] = to_state
        self.state["history"].append({
            "execution_id": exec_id,
            "from": from_state,
            "event": event,
            "to": to_state,
        })
        self._append_event({
            "type": "transition",
            "execution_id": exec_id,
            "from_state": from_state,
            "event": event,
            "to_state": to_state,
            "evidence": evidence,
            "total_tokens": self.state["total_tokens"],
        })
        if to_state in TERMINAL_SET:
            self._commit_terminal(to_state, terminal_reason or f"transitioned from {from_state} on {event!r}")
        else:
            self.save()

    def _commit_terminal(self, terminal: str, reason: str) -> None:
        self.state["status"] = terminal
        self.state["current_state"] = terminal
        self.state["in_flight"] = None
        self.trace("SYS", terminal, reason)
        self._append_event({"type": "terminal", "status": terminal, "reason": reason})
        self.save()

    # -------------------------------------------------------------- state executors (100% fresh Agent)
    def _build_fresh_agent(self, step: Step, exec_id: str) -> Agent:
        """Create a brand-new isolated Agent + Session for this state execution (zero cross-state chat bleed)."""
        spec, wf = step.spec, self.wf
        parts = [self.render(wf.instructions)]
        if wf.skills:
            parts.append(wf.skills)
        skill_names = spec.get("skills") or []
        if skill_names:
            try:
                parts.append(load_skills(self._skills_root, skill_names))
            except SkillError as exc:
                raise WorkflowError(f"{step.id}: {exc}") from None
        instructions = "\n\n".join(p for p in parts if p)
        names = spec.get("tools", wf.tools)
        tools = build_tools(names)
        budget = _first(spec.get("max_turns"), wf.max_turns, self.ctx.settings.max_turns)
        effort = spec.get("effort", wf.effort)
        sess_path = self.dir / "sessions" / f"{exec_id}-{step.id}.jsonl"
        agent = Agent(
            self.ctx,
            tools=tools,
            session=Session(sess_path),
            instructions=instructions,
            name=step.id,
            effort=effort,
            max_turns=budget,
        )
        if self.agent is not None:
            self.agent.close()
        self.agent = agent
        return agent

    def _prompt(self, step: Step, n: int = 1, total: int = 1) -> tuple[str, Any]:
        """Execute a prompt state with a fresh Agent (kept compatible with unit tests)."""
        out, data, _ = self._prompt_exec(step, f"step-{n:04d}")
        return out, data

    def _prompt_exec(self, step: Step, exec_id: str) -> tuple[str, Any, int]:
        spec = step.spec
        agent = self._build_fresh_agent(step, exec_id)
        allowed = ", ".join(agent.tools) or "none - answer from what you already know"
        saved = (
            f"\nYour final reply is saved to {self.render(spec['output'])} for later steps; you do not write it yourself."
            if spec.get("output") else ""
        )
        handoff_notes = self.state.get("handoff_notes") or []
        handoff_block = ("\n\n".join(handoff_notes) + "\n\n") if handoff_notes else ""
        message = (
            f"## State: {step.id} ({exec_id})\nTools for this state: {allowed}.{saved}\n\n"
            f"{handoff_block}{self.render(spec['prompt'])}"
        )
        rules = spec.get("checks") or []
        if spec.get("format") == "json":
            shape = f"\nShape:\n{_pretty_json(spec['schema'])}" if spec.get("schema") else ""
            message += (
                "\n\nEnd this step with ONLY one JSON object as your reply (no prose, no code fence)."
                + (' Every key of the shape is required, with the type it shows; "A|B" means one of A or B.' + shape if shape else "")
            )
            if rules:
                message += "\nYour answer must also pass these checks:\n" + "\n".join(f"- {r.path}: {r.text}" for r in rules)

        accepted: dict[str, Any] | None = None

        def validate(text: str) -> None:
            nonlocal accepted
            data = parse_json_object(text)
            errors = (check_shape(data, spec.get("schema")) if spec.get("schema") else []) or check_rules(data, rules)
            if errors:
                raise ValueError("; ".join(errors[:MAX_SHAPE_ERRORS]))
            accepted = data

        agent.validate_reply = validate if spec.get("format") == "json" else None
        agent.output_retries = self.ctx.settings.output_retries
        output = agent.run(message)
        if agent.stopped == "max_turns":
            raise WorkflowError(
                f"{step.id}: no final answer within max_turns ({agent.max_turns}); "
                "resume to continue, or raise max_turns (0 = no limit)"
            )
        tokens_used = sum(u.total for u in agent.session.usage.values()) or agent.context_tokens()
        self.trace("AGT", step.id, f"state answered ({exec_id})")
        return output, accepted, tokens_used

    def _ask(self, step: Step) -> str:
        default = self.render(step.spec["default"]) if step.spec.get("default") is not None else None
        return self._gate(step.id, self.render(step.spec["ask"]), step.spec.get("options"), default)

    def _gate(self, sid: str, message: str, options: list[str] | None, default: str | None) -> str:
        if sid in self.answers:
            answer, how = self.answers[sid], "--answer"
        elif self.ask_user is not None:
            answer, how = self.ask_user(sid, message, options, default), "interactive"
        elif default is not None:
            answer, how = default, "default"
        else:
            raise NeedsAnswer(sid, message, options, default)
        if options and answer not in options:
            match = [o for o in options if o.lower() == answer.strip().lower()]
            if not match:
                raise WorkflowError(f"{sid}: answer {answer!r} is not one of {options}")
            answer = match[0]
        self.trace("HUM", sid, f"{answer} ({how})")
        self.state.setdefault("handoff_notes", []).append(f"[Human review · {sid}]\n{message}\n\nAnswer: {answer}")
        return answer

    def _web_tasks(self, step: Step) -> list[tuple[str, Path, dict[str, Any]]]:
        spec = step.spec
        if "foreach" not in spec and str(spec["web"]).strip() != "plan":
            output = self.render(spec["output"]) if spec.get("output") else f"research/{_slug(step.id)}.md"
            return [(self.render(spec["web"]), inside(self.ctx, output), {})]
        raw = self.render(str(spec["max_items"])) if spec.get("max_items") else str(WEB_MAX_ITEMS)
        try:
            cap = int(raw)
        except ValueError:
            raise WorkflowError(f"{step.id}: max_items must be a whole number, got {raw!r}") from None
        if "foreach" in spec:
            items = self.expr(str(spec["foreach"]))
            if items is None:
                self.ctx.events.status(step.id, f"nothing to research: {spec['foreach']} is not set")
                items = []
            if not isinstance(items, list):
                raise WorkflowError(f"{step.id}: foreach must give a list, got {type(items).__name__}")
        else:
            items = self._plan(step, cap)
        if len(items) > cap:
            self.trace("SYS", step.id, f"{len(items)} tasks; researching the first {cap} (max_items)")
            items = items[:cap]
        tasks = []
        for i, item in enumerate(items, 1):
            extra = {"item": item, "index": i}
            task = str(item["task"]) if "foreach" not in spec else self.render(spec["web"], **extra)
            name = item.get("topic") or task if isinstance(item, dict) else task
            output = self.render(spec["output"], **extra) if spec.get("output") else f"research/{i}-{_slug(name)}.md"
            tasks.append((task, inside(self.ctx, output), extra))
        return tasks

    def _plan(self, step: Step, cap: int) -> list[dict[str, Any]]:
        plans = self.state.setdefault("web_plan", {})
        if step.id not in plans:
            # Include prior completed step outputs concisely so the fresh planner knows what evidence exists
            prior_summary = "\n\n".join(
                f"### Prior state `{sid}`\n{s.get('output', '')[:4000]}"
                for sid, s in self.state["steps"].items()
                if s.get("status") == "done" and s.get("output")
            )
            prompt = PLAN_PROMPT.format(cap=cap) + (f"\n\n{prior_summary}" if prior_summary else "")
            planner = Step(step.id, "prompt", {"prompt": prompt, "tools": [], "format": "json",
                                               "schema": PLAN_SCHEMA, "effort": step.spec.get("effort")})
            _, data, _ = self._prompt_exec(planner, f"webplan-{step.id}")
            plans[step.id] = data["web_tasks"]
            self.save()
        return plans[step.id]

    def _approved(self, step: Step, tasks: list[tuple[str, Path, dict[str, Any]]]) -> bool:
        approved = self.state.setdefault("web_approved", {})
        if step.id not in approved:
            listing = "\n".join(f"- {task}" for task, _, _ in tasks)
            answer = self._gate(step.id, f"Planned web research - these queries leave this machine:\n{listing}\n"
                                         "Run them?", ["go", "skip"], "go")
            approved[step.id] = answer == "go"
            self.save()
        return approved[step.id]

    def _web(self, step: Step) -> tuple[str, dict[str, Any]]:
        spec = step.spec
        tasks = self._web_tasks(step)
        if tasks and spec.get("approve") and not self._approved(step, tasks):
            self.state.setdefault("handoff_notes", []).append(
                f"[Web research · {step.id}]\nThe reviewer skipped the web research; there are no briefs."
            )
            return "Web research skipped by the reviewer.", {"items": []}
        progress = self.state.setdefault("web_progress", {}).setdefault(step.id, {})
        done: list[dict[str, Any]] = []
        for task, target, _ in tasks:
            path = rel(self.ctx, target)
            if any(d["file"] == path for d in done):
                raise WorkflowError(f"{step.id}: two tasks write to {path}; make `output` differ per item")
            if path in progress and target.is_file():
                done.append(progress[path])
                continue
            self.ctx.events.status(step.id, f"web research {len(done) + 1}/{len(tasks)}: {task[:80]}")
            brief = run_web_agent(self.ctx, task, max_turns=_first(spec.get("max_turns"), WEB_MAX_TURNS),
                                  max_searches=spec.get("max_searches") or WEB_MAX_SEARCHES, effort=spec.get("effort"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(brief.text + "\n", encoding="utf-8")
            record = {"task": task, "file": path, "searches": brief.searches, "sources": brief.sources,
                      "removed_links": brief.removed_links, "removed_results": brief.removed_results,
                      "safety": brief.safety}
            progress[path] = record
            self.save()
            done.append(record)
            self.trace("AGT", step.id, f"web agent: {_web_stats(record)} -> {path}")
        self.state["web_progress"].pop(step.id, None)
        listing = "\n".join(f"- {d['file']}: {d['task']} ({_web_stats(d)})" for d in done)
        note = (
            f"Web agents researched these tasks; each brief is saved to its file:\n{listing}\n"
            "Read a brief when a later step needs it."
        ) if done else "There were no web research tasks."
        self.state.setdefault("handoff_notes", []).append(f"[Web research · {step.id}]\n{note}")
        if len(done) == 1 and "foreach" not in spec and str(spec["web"]).strip() != "plan":
            return target.read_text(encoding="utf-8"), done[0]
        return listing or "No web research tasks.", {"items": done}


def _first(*values: Any) -> Any:
    return next(v for v in values if v is not None)


def _check_turns(where: str, value: Any) -> None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        raise WorkflowError(f"{where}: max_turns must be a whole number >= 0 (0 = no limit)")


def _web_stats(d: dict[str, Any]) -> str:
    extra = [f"{len(d['removed_links'])} unverified link(s) removed"] if d["removed_links"] else []
    if d["removed_results"]:
        extra.append(f"content removed from {d['removed_results']} result(s) by screening")
    return f"{len(d['searches'])} search(es), {len(d['sources'])} source(s)" + "".join(f", {x}" for x in extra)


def _slug(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", str(value)).strip("-").lower()[:60] or "item"


BUNDLED = Path(__file__).resolve().parents[2] / "config" / "cli" / "workflows"


def workflow_dirs(workspace: Path) -> list[Path]:
    return [workspace / STATE_DIR / "workflows", workspace / "workflows", BUNDLED]


def find_workflow(workspace: Path, name: str) -> Path:
    p = Path(name).expanduser()
    if not p.is_absolute():
        p = workspace / p if (workspace / p).is_file() else p
    if p.is_file():
        return p.resolve()
    for d in workflow_dirs(workspace):
        for ext in (".yaml", ".yml"):
            if (d / f"{name}{ext}").is_file():
                return (d / f"{name}{ext}").resolve()
    raise WorkflowError(f"workflow {name!r} not found (a path, or a name in {STATE_DIR}/workflows/, workflows/ or "
                        f"the bundled config/cli/workflows/)")
