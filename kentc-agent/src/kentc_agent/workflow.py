"""Workflows: one main agent works through YAML steps in order, keeping one context for the whole run.

A workflow is a plan for the main agent, not a team of agents. Each step narrows the tools the agent may use for
that step and gives it the step's instructions; the conversation (with compaction) carries every earlier finding
forward. Human gates sit between steps. Web research is a step of its own: a web agent (adapters/web_research.py)
researches the task in a fresh session and saves a cited brief as a file the main agent reads like any other.

    name: case-review
    inputs:
      case_id: {required: true}         # the documents are the files in the workspace: no folder input
    instructions: |                      # added to the agent's system prompt for this run (Jinja)
      You review bank cases. Cite file and location for every fact.
    tools: [read, bash]                  # default allowlist for steps (omit: all tools)
    max_turns: 20                        # default per step
    steps:
      - id: regulation
        web: "2026 changes to MAS Notice 626 for bank customer due diligence; cite sources"
        output: "research/regulation.md"          # required: the brief, an artifact for later steps
      - id: extract
        prompt: "Read every file: {{ documents('.') | join(', ') }} and list the key values with sources."
        tools: [read, bash]
      - id: findings
        prompt: "Cross-check the values and rank the risks."
        tools: [bash]                    # e.g. python3 -c for exact arithmetic
        format: json                     # the step's answer must be a JSON object -> steps.findings.data
        schema: {risks: [{title: string, score: number}], next_step: string}
      - id: decision
        ask: "Next step? Top risk: {{ steps.findings.data.risks[0].title }}"
        options: [Agree, Further investigation]
      - id: refine
        when: "steps.decision.output == 'Further investigation'"
        prompt: "Investigate further: ..."
      - id: report
        prompt: "Write the report."
        tools: [write]
        output: "reports/{{ inputs.case_id }}.md"   # the step's final answer is also saved here

Step keys: prompt | ask | web (exactly one), tools, max_turns, effort, format (text|json), schema, output, when;
ask steps: options, default. Web steps: `web: "<task>"` researches that task; `web: plan` asks the main agent, in
its current context, for the outside facts the work still needs (at most max_items, default 4), one web agent per
task; approve (go / skip before the queries leave the machine), max_turns, max_searches, output (optional, default
under research/), effort, when; advanced: foreach (an expression giving a list, e.g. `data.suppliers`; `item`,
`index` in `web` and `output`; missing or empty = nothing to do).
Templates are Jinja2 over `inputs`, `data` (every earlier JSON result, merged by key: refer to what was produced,
not to which step produced it, so steps can be reordered or removed), `steps.<id>.output | data | status`,
`trace`, `run_dir`, with `documents('folder')`, `glob('*.pdf')`, `read_file('x.md')`, `| json`, `| fromjson`,
`| slug` (file-name-safe text).

Every run keeps state.json (step outputs, decision trace) and the agent's session.jsonl in .kentc-agent/runs/<run>/;
`--resume` reloads both and continues at the first unfinished step, e.g. a human gate that had no answer."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jinja2 import StrictUndefined, TemplateError
from jinja2.sandbox import SandboxedEnvironment
from json_repair import repair_json

from .adapters.session import Session
from .adapters.tools import CORE_TOOLS, ToolContext, ToolError, inside, reject_unsupported, rel, resolve
from .adapters.web_research import run_web_agent
from .agent import CUT_OFF_NOTE, Aborted, Agent, build_tools
from .config import STATE_DIR

TOP_KEYS = {"name", "description", "inputs", "instructions", "tools", "max_turns", "effort", "steps"}
STEP_KEYS = {"id", "prompt", "ask", "web", "tools", "max_turns", "max_searches", "foreach", "max_items", "approve",
             "effort", "format", "schema", "output", "when", "options", "default"}
PROMPT_ONLY = {"tools", "max_turns", "effort", "format", "schema"}
ASK_ONLY = {"options", "default"}
WEB_ONLY = {"max_searches", "foreach", "max_items", "approve"}
NOT_FOR = {"prompt": ASK_ONLY | WEB_ONLY, "ask": PROMPT_ONLY | WEB_ONLY,
           "web": ASK_ONLY | {"tools", "format", "schema"}}
WEB_MAX_TURNS = 8
WEB_MAX_SEARCHES = 6
WEB_MAX_ITEMS = 4                    # web tasks per step unless max_items says otherwise
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

# (step id, rendered message, options or None, default or None) -> the human's answer
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
    kind: str                  # "prompt" | "ask"
    spec: dict[str, Any]


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


def load(path: Path) -> Workflow:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise WorkflowError(f"{path}: invalid YAML: {e}") from None
    if not isinstance(raw, dict) or not isinstance(raw.get("steps"), list) or not raw["steps"]:
        raise WorkflowError(f"{path}: needs a non-empty `steps` list")
    unknown = set(raw) - TOP_KEYS
    if unknown:
        raise WorkflowError(f"{path}: unknown top-level key(s): {', '.join(sorted(unknown))}")
    _check_tools("tools", raw.get("tools"))
    _check_turns("max_turns", raw.get("max_turns"))
    inputs = {k: v if isinstance(v, dict) else {"default": v} for k, v in (raw.get("inputs") or {}).items()}

    steps: list[Step] = []
    seen: set[str] = set()
    for i, s in enumerate(raw["steps"]):
        if not isinstance(s, dict):
            raise WorkflowError(f"steps[{i}]: must be a mapping")
        sid = s.get("id") or f"step{i + 1}"
        if not ID_RE.match(sid):
            raise WorkflowError(f"steps[{i}]: id {sid!r} must be a letter/underscore followed by letters, digits, _")
        if sid in seen:
            raise WorkflowError(f"steps[{i}]: duplicate id {sid!r}")
        kinds = [k for k in ("prompt", "ask", "web") if k in s]
        if len(kinds) != 1:
            raise WorkflowError(f"{sid}: needs exactly one of prompt, ask or web")
        kind = kinds[0]
        bad = set(s) - STEP_KEYS | (set(s) & NOT_FOR[kind])
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
        if s.get("format", "text") not in ("text", "json"):
            raise WorkflowError(f"{sid}: format must be text or json")
        if "schema" in s and not isinstance(s["schema"], dict):
            raise WorkflowError(f"{sid}: schema must be a mapping of key -> shape")
        if "options" in s and not isinstance(s["options"], list):
            raise WorkflowError(f"{sid}: options must be a list")
        later = {a or b for a, b in REF_RE.findall("\n".join(_strings(s)))} - seen
        if later:
            raise WorkflowError(f"{sid}: refers to steps that have not run yet: {', '.join(sorted(later))}")
        seen.add(sid)
        steps.append(Step(sid, kind, s))
    return Workflow(raw.get("name") or path.stem, raw.get("description") or "", inputs,
                    raw.get("instructions") or "", raw.get("tools"), raw.get("max_turns"), raw.get("effort"),
                    steps, path)


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
    """The JSON object in a model reply: tolerates prose, code fences, trailing commas and a reply cut off at the
    output limit (json-repair closes it; the caller decides whether a cut-off reply is acceptable)."""
    text = text.replace(CUT_OFF_NOTE, "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0:
        raise ValueError("no JSON object in the reply")
    try:
        data = json.loads(text[start:end + 1]) if end > start else None
    except json.JSONDecodeError:
        data = None
    if data is None:
        data = repair_json(text[start:], return_objects=True)
    if not isinstance(data, dict) or not data:
        raise ValueError("the reply is not a JSON object")
    return data


# ---------------------------------------------------------------------- output shape
SCALARS: dict[str, Any] = {"string": str, "number": (int, float), "integer": int, "boolean": bool}
MAX_SHAPE_ERRORS = 8                             # shown to the model per retry; the rest are counted


def check_shape(data: Any, shape: Any) -> list[str]:
    """What is wrong with `data` against a step's `schema`, a shape by example; [] when it fits. Enum values are
    canonicalized in place.

    {key: shape}: an object, every key required (more keys allowed); [shape]: a list of items of that shape;
    "string" | "number" | "integer" | "boolean"; "A|B|C": one of these (case-insensitive); a number: any number;
    any other string describes a string value (e.g. "two sentences")."""
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
        errors.append(f"{label} must be one of {' | '.join(options)}, got {json.dumps(value, ensure_ascii=False)}")
        return value
    elif isinstance(shape, str):
        expected, name = str, "string"
    else:                                        # null or anything else: no constraint
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


# ---------------------------------------------------------------------- running
class Runner:
    def __init__(self, wf: Workflow, ctx: ToolContext, inputs: dict[str, Any], run_dir: Path, *,
                 ask_user: AskUser | None = None, answers: dict[str, str] | None = None) -> None:
        self.wf, self.ctx, self.inputs, self.dir = wf, ctx, inputs, run_dir
        self.ask_user, self.answers = ask_user, answers or {}
        self.state: dict[str, Any] = {"workflow": str(wf.path), "name": wf.name, "inputs": inputs, "steps": {},
                                      "trace": []}
        if (run_dir / "state.json").is_file():   # resume: the caller passes the saved inputs, with any overrides
            self.state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
            self.state["inputs"] = inputs
        self.env = _Env(undefined=StrictUndefined, keep_trailing_newline=True)
        self.env.globals.update(glob=self._glob, read_file=self._read_file, documents=self._documents)
        self.env.filters.update(fromjson=json.loads, json=_pretty_json, slug=_slug)
        log = run_dir / "session.jsonl"
        self.agent = Agent(ctx, tools=[], session=Session.load(log) if log.is_file() else Session(log),
                           instructions=self.render(wf.instructions), name=wf.name)

    # -------------------------------------------------------------- template helpers
    def _glob(self, pattern: str) -> list[str]:
        ws = self.ctx.workspace
        return sorted(str(p.relative_to(ws)) for p in ws.glob(pattern) if p.is_file())

    def _read_file(self, path: str) -> str:
        return resolve(self.ctx, path).read_text(encoding="utf-8")

    def _documents(self, folder: str) -> list[str]:
        """Supported files directly in `folder` (no hidden files, no video/legacy formats), sorted."""
        root = resolve(self.ctx, folder)
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
        steps = {sid: {"output": s.get("output", ""), "data": s.get("data"), "status": s["status"]}
                 for sid, s in self.state["steps"].items()}
        data: dict[str, Any] = {}               # every JSON result so far, by key; later steps win
        for s in self.state["steps"].values():
            if isinstance(s.get("data"), dict):
                data.update(s["data"])
        return {"inputs": self.inputs, "steps": steps, "data": data, "run_dir": str(self.dir),
                "trace": self.state["trace"], "workspace": str(self.ctx.workspace), **extra}

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

    # -------------------------------------------------------------- execution
    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "state.json").write_text(json.dumps(self.state, indent=2, ensure_ascii=False, default=str),
                                             encoding="utf-8")

    def trace(self, actor: str, step: str, event: str) -> None:
        """Decision trace for audit: HUM (human gate), AGT (agent step), SYS."""
        self.state["trace"].append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "actor": actor, "step": step,
                                    "event": event})

    def run(self) -> dict[str, Any]:
        self.save()
        total = len(self.wf.steps)
        for n, step in enumerate(self.wf.steps, 1):
            prev = self.state["steps"].get(step.id)
            if prev and prev["status"] in ("done", "skipped"):
                self.ctx.events.status(step.id, f"{prev['status']} earlier (resumed run)")
                continue
            rec = self.state["steps"][step.id] = {"status": "running", "started": time.time()}
            self.state.pop("waiting", None)
            self.save()                          # a killed process leaves this step marked running, not missing
            try:
                if "when" in step.spec and not self.expr(str(step.spec["when"])):
                    rec.update(status="skipped", output="")
                    self.ctx.events.status(step.id, "skipped (when is false)")
                    self.save()
                    continue
                self.ctx.events.status(step.id, f"step {n}/{total}")
                if step.kind == "prompt":
                    rec["output"], rec["data"] = self._prompt(step, n, total)
                elif step.kind == "web":
                    rec["output"], rec["data"] = self._web(step)
                else:
                    rec["output"] = self._ask(step)
                if step.spec.get("output") and step.kind != "web":   # a web step writes its own brief file(s)
                    target = inside(self.ctx, self.render(step.spec["output"]))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(rec["output"], encoding="utf-8")
                rec.update(status="done", finished=time.time())
            except NeedsAnswer as e:
                rec.update(status="waiting")
                self.state["waiting"] = e.gate
                self.save()
                raise
            except Aborted:
                rec.update(status="failed", error="aborted by the user")
                self.save()
                raise
            except Exception as e:
                rec.update(status="failed", error=f"{type(e).__name__}: {e}")
                self.trace("SYS", step.id, f"failed: {e}")
                self.save()
                raise WorkflowError(f"step {step.id!r} failed: {e}\nResume with: --resume {self.dir}") from e
            self.save()
        return self.state

    def _prompt(self, step: Step, n: int, total: int) -> tuple[str, Any]:
        """One step of the main agent: its tools narrowed to the step's list, its context kept."""
        spec, wf = step.spec, self.wf
        names = spec.get("tools", wf.tools)
        self.agent.set_tools(build_tools(names))
        self.agent.name = step.id
        self.agent.max_turns = _first(spec.get("max_turns"), wf.max_turns, self.ctx.settings.max_turns)
        self.agent.effort = spec.get("effort", wf.effort)
        allowed = ", ".join(self.agent.tools) or "none - answer from what you already know"
        saved = f"\nYour final reply is saved to {self.render(spec['output'])} for later steps; you do not write it " \
            "yourself." if spec.get("output") else ""
        message = f"## Step {n}/{total}: {step.id}\nTools for this step: {allowed}.{saved}\n\n" + \
            self.render(spec["prompt"])
        if spec.get("format") == "json":
            shape = f"\nShape:\n{_pretty_json(spec['schema'])}" if spec.get("schema") else ""
            message += "\n\nEnd this step with ONLY one JSON object as your reply (no prose, no code fence)." + \
                (" Every key of the shape is required, with the type it shows; \"A|B\" means one of A or B." +
                 shape if shape else "")
        output = self._run_agent(step, message)
        self.trace("AGT", step.id, "step answered")
        if spec.get("format") != "json":
            return output, None
        schema = spec.get("schema")
        for attempt in range(3):
            last = attempt == 2
            try:
                data = parse_json_object(output)
                errors = check_shape(data, schema) if schema else []
                cut = CUT_OFF_NOTE in output
                if not errors and (not cut or last):
                    if cut:
                        self.trace("SYS", step.id, "JSON reply was cut off at the output limit and repaired")
                    return output, data
                shown = "; ".join(errors[:MAX_SHAPE_ERRORS]) + \
                    (f"; and {len(errors) - MAX_SHAPE_ERRORS} more" if len(errors) > MAX_SHAPE_ERRORS else "")
                problem = f"it does not fit the shape: {shown}" if errors else \
                    "it was cut off at the output limit; give a shorter JSON object (fewer items, strings under 200 " \
                    "characters)"
            except ValueError as e:
                problem = f"it is not one valid JSON object ({e})"
            if last:
                raise WorkflowError(f"{step.id}: the agent did not return the expected JSON: {problem}")
            output = self._run_agent(step, f"Your reply cannot be used: {problem}. Reply with only the complete JSON "
                                           "object.")
        raise AssertionError("unreachable")

    def _run_agent(self, step: Step, message: str) -> str:
        """The step's agent turn. Running out of model calls is a failure, not an answer: nothing is saved as the
        step's result, and --resume continues in the same context with a fresh turn budget."""
        output = self.agent.run(message)
        if self.agent.stopped == "max_turns":
            raise WorkflowError(f"{step.id}: no final answer within max_turns ({self.agent.max_turns}); the work so far "
                                "is in the session - resume to continue, or raise max_turns (0 = no limit)")
        return output

    def _ask(self, step: Step) -> str:
        """A human gate step."""
        default = self.render(step.spec["default"]) if step.spec.get("default") is not None else None
        return self._gate(step.id, self.render(step.spec["ask"]), step.spec.get("options"), default)

    def _gate(self, sid: str, message: str, options: list[str] | None, default: str | None) -> str:
        """Ask a human: --answer, then the terminal, then the default; else stop the run until resumed with an
        answer. The answer is recorded in the trace and told to the agent before its next step."""
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
        self.agent.session.append({"role": "user", "content": f"[Human review · {sid}]\n{message}\n\nAnswer: "
                                                                f"{answer}"})
        return answer

    def _web_tasks(self, step: Step) -> list[tuple[str, Path, dict[str, Any]]]:
        """The step's tasks as (task, brief file, template extras): one fixed task, the tasks `web: plan` asks the
        main agent for, or one per item of `foreach`."""
        spec = step.spec
        if "foreach" not in spec and str(spec["web"]).strip() != "plan":
            output = self.render(spec["output"]) if spec.get("output") else f"research/{_slug(step.id)}.md"
            return [(self.render(spec["web"]), inside(self.ctx, output), {})]
        raw = self.render(str(spec["max_items"])) if spec.get("max_items") else str(WEB_MAX_ITEMS)
        try:
            cap = int(raw)                      # a number, or a template such as "{{ inputs.n }}"
        except ValueError:
            raise WorkflowError(f"{step.id}: max_items must be a whole number, got {raw!r}") from None
        if "foreach" in spec:
            items = self.expr(str(spec["foreach"]))
            if items is None:                    # no earlier step produced it (e.g. that step was removed)
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
        """`web: plan`: the main agent, in its current context, lists what the work still needs from the web. Kept,
        so a resumed run does not plan again."""
        plans = self.state.setdefault("web_plan", {})
        if step.id not in plans:
            planner = Step(step.id, "prompt", {"prompt": PLAN_PROMPT.format(cap=cap), "tools": [], "format": "json",
                                               "schema": PLAN_SCHEMA, "effort": step.spec.get("effort")})
            plans[step.id] = self._prompt(planner, self.wf.steps.index(step) + 1, len(self.wf.steps))[1]["web_tasks"]
            self.save()
        return plans[step.id]

    def _approved(self, step: Step, tasks: list[tuple[str, Path, dict[str, Any]]]) -> bool:
        """`approve: true` on a web step: show its queries and ask go / skip before any leaves the machine. The
        answer is kept, so a resumed run does not ask again."""
        approved = self.state.setdefault("web_approved", {})
        if step.id not in approved:
            listing = "\n".join(f"- {task}" for task, _, _ in tasks)
            answer = self._gate(step.id, f"Planned web research - these queries leave this machine:\n{listing}\n"
                                         "Run them?", ["go", "skip"], "go")
            approved[step.id] = answer == "go"
            self.save()
        return approved[step.id]

    def _web(self, step: Step) -> tuple[str, dict[str, Any]]:
        """Web research as a step: one web agent per task, each in its own session, each brief saved to a file
        (`output`, default under research/). The main agent only learns where the briefs are, and reads them when a
        later step needs them. Briefs already written survive a failed task, so --resume continues with the rest."""
        spec = step.spec
        tasks = self._web_tasks(step)
        if tasks and spec.get("approve") and not self._approved(step, tasks):
            self.agent.session.append({"role": "user", "content": f"[Web research · {step.id}]\nThe reviewer "
                                                                    "skipped the web research; there are no briefs."})
            return "Web research skipped by the reviewer.", {"items": []}
        progress = self.state.setdefault("web_progress", {}).setdefault(step.id, {})
        done: list[dict[str, Any]] = []
        for task, target, _ in tasks:
            path = rel(self.ctx, target)
            if any(d["file"] == path for d in done):
                raise WorkflowError(f"{step.id}: two tasks write to {path}; make `output` differ per item")
            if path in progress and target.is_file():
                done.append(progress[path])                         # written before a resume
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
        note = (f"Web agents researched these tasks; each brief is saved to its file:\n{listing}\n"
                "Read a brief when a later step needs it.") if done else "There were no web research tasks."
        self.agent.session.append({"role": "user", "content": f"[Web research · {step.id}]\n{note}"})
        if len(done) == 1 and "foreach" not in spec and str(spec["web"]).strip() != "plan":
            return target.read_text(encoding="utf-8"), done[0]
        return listing or "No web research tasks.", {"items": done}


def _first(*values: Any) -> Any:
    """The first value that is set; 0 counts (max_turns: 0 means no limit)."""
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
    """A file-name-safe form of a value: `research/{{ item.topic | slug }}.md`."""
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
