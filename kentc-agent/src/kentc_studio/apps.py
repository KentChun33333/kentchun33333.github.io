"""Studio apps: one YAML manifest per use case (TER review, RM insight, ...), served by one studio.

An app declares the three pages of the async loop:

    Page 1  intake   case fields, file lanes, data pulls          -> the case table (queue)
    Page 2  agents   insight agents that read each lane's files    -> the analyst verifies, flags, adds files
    Page 3  report   the report agent, in the report framework     -> the analyst prompts (one prompt = one version)

Agents answer with JSON of their workflow's `schema`; a `view` says how the front end shows it, using a fixed set
of blocks. Agents never write HTML. Every view path is checked against the schema when the app loads.

Report framework: every report agent's result carries `title`, `verdict` (one of the app's `verdicts`), `reply`
(its answer to the analyst's latest prompt), `requests` ([{document, reason}]) and `questions` ([string]); the
rest of the result is the app's own, shown through `report.view`.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import jinja2
import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .data import DataPull
from .providers import AgentError, Provider, make_provider

# block type -> its options besides `title`
BLOCKS: dict[str, set[str]] = {
    "text": set(), "kv": {"labels"}, "table": {"columns"}, "list": set(), "chips": set(),
    "cards": {"head", "kicker", "score", "body", "notes"}, "facts": set(),
}
LIST_BLOCKS = {"table", "list", "chips", "cards", "facts"}
FACT_KEYS = ("field", "value", "location", "confidence")       # a `facts` row the analyst can flag
ENVELOPE = ("title", "verdict", "reply", "requests", "questions")
TONES = ("ok", "warn", "bad", "info")
RESERVED_FIELDS = {"id", "app", "case_id"}

# What the studio passes each kind of agent (a workflow must declare exactly these inputs).
AGENT_INPUTS = {
    "file": {"file", "case_brief", "feedback", "previous"},     # one job per file of the lane
    "lane": {"lane_file", "case_brief", "feedback"},            # one job over the lane's files, given as text
}
REPORT_INPUTS = {"materials_file", "case_brief", "instruction", "previous_report_file"}
EXTRA_INPUTS = {"materials_file", "case_brief"}
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
MISSING = object()


class _Raw(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FieldSpec(_Raw):
    name: str
    label: str = ""
    type: Literal["text", "textarea", "date", "select"] = "text"
    required: bool = False
    column: bool = False            # shown in the case table
    default: str = ""               # pre-filled on Page 1
    options: list[str] = Field(default_factory=list)
    wide: bool = False


class LaneSpec(_Raw):
    name: str
    label: str = ""
    hint: str = ""
    required: bool = False
    agent: str = ""                 # the insight agent for this lane's files; "" = only the report agent reads them
    sample: list[str] = Field(default_factory=list)     # globs: sample-bundle files that go to this lane


class _AgentRef(_Raw):
    workflow: str = ""
    url: str = ""
    label: str = ""
    timeout: float = 1800

    def provider_spec(self) -> dict[str, Any]:
        return {"workflow": self.workflow, "url": self.url, "label": self.label, "timeout": self.timeout}


class AgentSpec(_AgentRef):
    per: Literal["file", "lane"] = "file"
    view: list[dict[str, Any]] = Field(default_factory=list)


class ReportSpec(_AgentRef):
    name: str = "Report"
    verdicts: dict[str, Literal["ok", "warn", "bad", "info"]]
    view: list[dict[str, Any]] = Field(default_factory=list)


class ExtraSpec(_AgentRef):
    default: bool = False


class CaseIdSpec(_Raw):
    label: str = "Case ID"
    prefix: str = "CASE-"


class AppSpec(_Raw):
    title: str
    description: str = ""
    case: CaseIdSpec = Field(default_factory=CaseIdSpec)
    brief: str
    fields: list[FieldSpec]
    lanes: list[LaneSpec]
    sample: str = ""
    pulls: list[str] = Field(default_factory=list)
    agents: dict[str, AgentSpec] = Field(default_factory=dict)
    report: ReportSpec
    extras: dict[str, ExtraSpec] = Field(default_factory=dict)


@dataclass
class Agent:
    provider: Provider
    per: str                        # file | lane
    view: list[dict[str, Any]]

    @property
    def label(self) -> str:
        return self.provider.label


@dataclass
class Report:
    provider: Provider
    name: str
    verdicts: dict[str, str]
    view: list[dict[str, Any]]

    def tone(self, verdict: Any) -> str:
        v = str(verdict or "").strip().lower()
        return next((t for k, t in self.verdicts.items() if k.lower() == v), "info")


@dataclass
class App:
    name: str
    spec: AppSpec
    agents: dict[str, Agent]
    report: Report
    extras: dict[str, Provider]
    pulls: list[str]
    sample: Path | None
    brief_template: jinja2.Template

    @property
    def title(self) -> str:
        return self.spec.title

    @property
    def lanes(self) -> list[LaneSpec]:
        return self.spec.lanes

    def lane(self, name: str) -> LaneSpec | None:
        return next((ln for ln in self.spec.lanes if ln.name == name), None)

    def agent_of(self, lane: str) -> Agent | None:
        ln = self.lane(lane)
        return self.agents[ln.agent] if ln and ln.agent else None

    def brief(self, case_id: str, fields: dict[str, str]) -> str:
        return " ".join(self.brief_template.render(id=case_id, **fields).split())

    def clean_fields(self, given: dict[str, Any]) -> dict[str, str]:
        unknown = sorted(set(given) - {f.name for f in self.spec.fields})
        if unknown:
            raise ValueError(f"unknown field(s) for {self.title}: {', '.join(unknown)}")
        out = {}
        for f in self.spec.fields:
            v = str(given.get(f.name) or "").strip()
            if f.required and not v:
                raise ValueError(f"{f.label or f.name} is required")
            if f.type == "select" and v and v not in f.options:
                raise ValueError(f"{f.label or f.name} must be one of {', '.join(f.options)}")
            out[f.name] = v
        return out

    def sample_files(self) -> list[tuple[str, str, bytes]]:
        """The sample bundle as (name, lane, bytes): each file goes to the first lane whose globs match it."""
        out = []
        for f in sorted(self.sample.iterdir()) if self.sample else []:
            if not f.is_file() or f.name.startswith("."):
                continue
            lane = next((ln.name for ln in self.spec.lanes
                         if any(fnmatch.fnmatch(f.name.lower(), g.lower()) for g in ln.sample)), None)
            if lane:
                out.append((f.name, lane, f.read_bytes()))
        return out

    def describe(self, pulls: dict[str, DataPull]) -> dict[str, Any]:
        """The app as the front end needs it: Page 1 form, lanes and pulls; Page 2 / 3 views."""
        return {
            "name": self.name, "title": self.title, "description": self.spec.description,
            "case": self.spec.case.model_dump(), "fields": [f.model_dump() for f in self.spec.fields],
            "lanes": [{**ln.model_dump(exclude={"sample"}),
                       "agent_label": self.agents[ln.agent].label if ln.agent else "",
                       "per": self.agents[ln.agent].per if ln.agent else ""} for ln in self.spec.lanes],
            "sample": self.sample is not None,
            "pulls": [{"name": n, "label": p.label, "description": p.description, "database": p.database.label,
                       "default": p.default, "triggers": p.triggers, "binds": [b for b in p.binds if b != "case_id"]}
                      for n in self.pulls for p in [pulls[n]]],
            "agents": {k: {"label": a.label, "per": a.per, "view": a.view} for k, a in self.agents.items()},
            "extras": [{"name": k, "label": p.label, "default": p.default, "remote": not p.local}
                       for k, p in self.extras.items()],
            "report": {"name": self.report.name, "label": self.report.provider.label,
                       "verdicts": self.report.verdicts, "view": self.report.view},
        }


# ---------------------------------------------------------------------- views
def shape_at(shape: Any, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(shape, dict) or part not in shape:
            return MISSING
        shape = shape[part]
    return shape


def block_kind(block: dict[str, Any]) -> str:
    return next(k for k in block if k in BLOCKS)


def check_view(view: list[dict[str, Any]], schema: dict[str, Any] | None, where: str, facts: bool) -> None:
    """A view is a list of blocks, each `{<type>: <path into the result>, title?, <options>}`. With a schema (a local
    workflow), every path and option must exist in it; an external agent's result is only known at run time."""
    for i, block in enumerate(view):
        at = f"{where}: view[{i}]"
        kinds = [k for k in block if k in BLOCKS]
        if len(kinds) != 1:
            raise AgentError(f"{at}: give exactly one block type: {', '.join(BLOCKS)}")
        kind = kinds[0]
        unknown = sorted(set(block) - {kind, "title"} - BLOCKS[kind])
        if unknown:
            raise AgentError(f"{at}: unknown option(s) {', '.join(unknown)} for {kind}"
                             f" (allowed: {', '.join(sorted(BLOCKS[kind] | {'title'}))})")
        if kind == "facts" and not facts:
            raise AgentError(f"{at}: facts (flaggable rows) belong to the insight agents of Page 2")
        paths = block[kind]
        many = kind == "kv" and isinstance(paths, list)
        if not (many and all(isinstance(p, str) for p in paths)) and not isinstance(paths, str):
            raise AgentError(f"{at}: {kind} takes a path into the result" + (" or a list of paths" if kind == "kv"
                                                                                else ""))
        if schema is None:
            continue
        for p in paths if many else [paths]:
            if shape_at(schema, p) is MISSING:
                raise AgentError(f"{at}: {kind} {p!r} is not in the agent's schema")
        if many:
            continue
        shape = shape_at(schema, paths)
        if kind == "kv" and not isinstance(shape, dict):
            raise AgentError(f"{at}: kv {paths!r} must be an object in the schema (or give a list of paths)")
        if kind in LIST_BLOCKS and not isinstance(shape, list):
            raise AgentError(f"{at}: {kind} {paths!r} must be a list in the schema")
        if kind in ("table", "cards", "facts"):
            item = shape[0] if shape else None
            if not isinstance(item, dict):
                raise AgentError(f"{at}: {kind} {paths!r} must be a list of objects in the schema")
            cols = block.get("columns") or []
            needed = list(FACT_KEYS) if kind == "facts" else list(cols) if kind == "table" else \
                [block[o] for o in ("head", "kicker", "score", "body") if o in block] + list(block.get("notes") or [])
            missing = [k for k in needed if k not in item]
            if missing:
                raise AgentError(f"{at}: {', '.join(missing)} not in the items of {paths!r}")


def check_envelope(schema: dict[str, Any], verdicts: dict[str, str], where: str) -> None:
    missing = [k for k in ENVELOPE if k not in schema]
    if missing:
        raise AgentError(f"{where}: the report schema needs the report-framework keys {', '.join(ENVELOPE)} "
                         f"(missing {', '.join(missing)})")
    v = schema["verdict"]
    options = [o.strip() for o in v.split("|")] if isinstance(v, str) and "|" in v else []
    if not options:
        raise AgentError(f'{where}: verdict must be one of several values, e.g. "Agree|Further investigation"')
    if {o.lower() for o in options} != {k.lower() for k in verdicts}:
        raise AgentError(f"{where}: verdicts must give a tone ({', '.join(TONES)}) for each verdict: "
                         f"{', '.join(options)}")
    req = schema["requests"]
    if not (isinstance(req, list) and req and isinstance(req[0], dict) and {"document", "reason"} <= set(req[0])):
        raise AgentError(f"{where}: requests must be [{{document: string, reason: string}}]")
    if not isinstance(schema["questions"], list):
        raise AgentError(f"{where}: questions must be a list of strings")


# ---------------------------------------------------------------------- loading
def load_app(name: str, path: Path, pulls: dict[str, DataPull]) -> App:
    if not NAME_RE.match(name):
        raise AgentError(f"app {name!r}: use lower-case letters, digits and _")
    if not path.is_file():
        raise AgentError(f"app {name}: {path} not found")
    try:
        spec = AppSpec.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    except (ValidationError, yaml.YAMLError) as e:
        raise AgentError(f"app {name}: invalid {path.name}: {e}") from None
    base, where = path.parent, f"app {name}"

    names = [f.name for f in spec.fields]
    for f in spec.fields:
        if not NAME_RE.match(f.name) or f.name in RESERVED_FIELDS:
            raise AgentError(f"{where}: field {f.name!r}: lower-case letters, digits and _; not {', '.join(RESERVED_FIELDS)}")
        if f.type == "select" and not f.options:
            raise AgentError(f"{where}: field {f.name}: a select needs options")
    if len(set(names)) != len(names):
        raise AgentError(f"{where}: field names must be unique")
    lane_names = [ln.name for ln in spec.lanes]
    if not spec.lanes or len(set(lane_names)) != len(lane_names) or not all(NAME_RE.match(n) for n in lane_names):
        raise AgentError(f"{where}: lanes need unique lower-case names (at least one lane)")
    for ln in spec.lanes:
        if ln.agent and ln.agent not in spec.agents:
            raise AgentError(f"{where}: lane {ln.name}: agent {ln.agent!r} is not under agents")
    unused = sorted(set(spec.agents) - {ln.agent for ln in spec.lanes})
    if unused:
        raise AgentError(f"{where}: agent(s) {', '.join(unused)} read no lane")

    agents = {}
    for aname, a in spec.agents.items():
        provider = make_provider(aname, a.provider_spec(), base, AGENT_INPUTS[a.per])
        check_view(a.view, provider.schema, f"{where} agent {aname}", facts=True)
        agents[aname] = Agent(provider, a.per, a.view)
    rp = make_provider("report", {**spec.report.provider_spec(), "label": spec.report.label or "Report agent"}, base,
                       REPORT_INPUTS)
    if rp.schema is not None:
        check_envelope(rp.schema, spec.report.verdicts, f"{where} report")
    check_view(spec.report.view, rp.schema, f"{where} report", facts=False)
    extras = {k: make_provider(k, {**e.provider_spec(), "default": e.default}, base, EXTRA_INPUTS)
              for k, e in spec.extras.items()}

    unknown = [p for p in spec.pulls if p not in pulls]
    if unknown:
        raise AgentError(f"{where}: unknown data pull(s) {', '.join(unknown)} (studio.yaml data_pulls)")
    for p in spec.pulls:
        bad = sorted(set(pulls[p].binds) - set(names) - {"case_id"})
        if bad:
            raise AgentError(f"{where}: data pull {p} binds :{', :'.join(bad)}, which are not fields of this app")

    sample = None
    if spec.sample:
        sample = (base / spec.sample).resolve()
        if not sample.is_dir():
            raise AgentError(f"{where}: sample folder {sample} not found")
        if not any(ln.sample for ln in spec.lanes):
            raise AgentError(f"{where}: a sample folder needs lanes with `sample` globs")

    try:
        template = jinja2.Environment(undefined=jinja2.StrictUndefined).from_string(spec.brief)
        template.render(id="X", **{n: "x" for n in names})
    except jinja2.TemplateError as e:
        raise AgentError(f"{where}: brief: {e}") from None
    return App(name, spec, agents, Report(rp, spec.report.name, spec.report.verdicts, spec.report.view), extras,
               spec.pulls, sample, template)
