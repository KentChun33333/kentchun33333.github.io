"""Studio apps: one YAML manifest per use case (TER review, RM insight, ...), served by one studio.

An app declares the three pages of the async loop:

    Page 1  intake   case fields, file lanes, data pulls          -> the case table (queue)
    Page 2  agents   insight agents that read each lane's files    -> the analyst verifies, flags, adds files
    Page 3  report   the report agent, in the report framework     -> the analyst prompts (one prompt = one version)

An agent is declared inline: a contract (the studio's fixed inputs for its role, an `output` shape, `checks`,
`tools`, `max_turns`) equipped with skills (kentc-agent/skills/<name>.md, the prose of how to do the work). Agents
answer with JSON of their `output`; the front end shows it with a fixed set of blocks. An agent's optional `view`
gives custom blocks; every other output key is shown with a default block chosen by its shape, unless it is in
`hide`. Agents never write HTML. Every view path and check is validated against the output when the app loads.
Labels default to readable names, and the one-line case brief every agent gets is built from the fields.

Report framework: every report agent's result carries `title`, `verdict` (one of the app's `verdicts`), `reply`
(its answer to the analyst's latest prompt), `requests` ([{document, reason}]) and `questions` ([string]); the
page shows these itself, and the rest of the result is the app's own, shown through `report.view`.
"""

from __future__ import annotations

import fnmatch
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

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

# What the studio passes each kind of agent (the task message lists them; skills say what to do with them).
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
    label: str = ""                 # default: the name, readable ("start_date" -> "Start date")
    type: Literal["text", "textarea", "date", "select"] = "text"
    required: bool = False
    column: bool = False            # shown in the case table
    default: str = ""               # pre-filled on Page 1
    options: list[str] = Field(default_factory=list)
    wide: bool = False


class AgentSpec(_Raw):
    """An agent: local (skills + contract) or external (`url`)."""
    label: str = ""
    skills: list[str] = Field(default_factory=list)     # kentc-agent/skills/<name>.md, in this order
    tools: list[str] | None = None                      # default [read]; [] = none; never bash
    max_turns: int = Field(100, ge=0)                   # model calls for the whole job, repairs included; 0 = no limit
    effort: str | None = None                           # none | low | medium | high
    output: dict[str, Any] = Field(default_factory=dict)    # the JSON answer's shape, by example
    checks: dict[str, str | list[str]] = Field(default_factory=dict)   # path -> rule(s), kentc_agent/checks.py
    url: str = ""                                       # an external agent instead
    timeout: float = 1800

    def provider_spec(self) -> dict[str, Any]:
        return self.model_dump(exclude={"per", "name", "verdicts", "view", "hide"})


class LaneAgentSpec(AgentSpec):
    per: Literal["file", "lane"] = "file"   # one job per file, or one job over the lane's files given as text


class LaneSpec(_Raw):
    name: str
    label: str = ""                 # default: the name, readable
    hint: str = ""
    required: bool = False
    agent: LaneAgentSpec | None = None  # the insight agent; none = only the report agent reads this lane's files
    view: list[dict[str, Any]] = Field(default_factory=list)    # custom blocks; other output keys are appended
    hide: list[str] = Field(default_factory=list)               # output keys never shown
    sample: list[str] = Field(default_factory=list)     # globs: sample-bundle files that go to this lane


class ReportSpec(AgentSpec):
    name: str = "Report"
    verdicts: dict[str, Literal["ok", "warn", "bad", "info"]]
    view: list[dict[str, Any]] = Field(default_factory=list)
    hide: list[str] = Field(default_factory=list)


class ExtraSpec(AgentSpec):
    default: bool = False


class CaseIdSpec(_Raw):
    label: str = "Case ID"
    prefix: str = ""                # default: "<APP NAME>-<year>-"


class AppSpec(_Raw):
    title: str
    description: str = ""
    case: CaseIdSpec = Field(default_factory=CaseIdSpec)
    fields: list[FieldSpec]
    lanes: list[LaneSpec]
    sample: str = ""
    pulls: list[str] = Field(default_factory=list)
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
    agents: dict[str, Agent]        # by lane name: the insight agent that reads that lane
    report: Report
    extras: dict[str, Provider]
    pulls: list[str]
    sample: Path | None

    @property
    def title(self) -> str:
        return self.spec.title

    @property
    def lanes(self) -> list[LaneSpec]:
        return self.spec.lanes

    def lane(self, name: str) -> LaneSpec | None:
        return next((ln for ln in self.spec.lanes if ln.name == name), None)

    def agent_of(self, lane: str) -> Agent | None:
        return self.agents.get(lane)

    def brief(self, case_id: str, fields: dict[str, str]) -> str:
        """The case in one line for every agent: the case, the app, then each filled field as `Label: value`."""
        filled = "; ".join(f"{f.label}: {' '.join(fields[f.name].split())}" for f in self.spec.fields
                           if fields.get(f.name))
        end = "" if not filled or filled.endswith((".", "?", "!")) else "."
        return f"Case {case_id} ({self.title})." + (f" {filled}{end}" if filled else "")

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
            "lanes": [{"name": ln.name, "label": ln.label, "hint": ln.hint, "required": ln.required,
                       "agent": ln.name if ln.name in self.agents else "",
                       "agent_label": self.agents[ln.name].label if ln.name in self.agents else "",
                       "per": self.agents[ln.name].per if ln.name in self.agents else ""} for ln in self.spec.lanes],
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
    agent's `output`), every path and option must exist in it; an external agent's result is only known at run time."""
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


def humanize(key: str) -> str:
    """A schema key or field name as a label: "start_date" -> "Start date"."""
    key = key.rsplit(".", 1)[-1].replace("_", " ").strip()
    return key[:1].upper() + key[1:]


def default_view(schema: dict[str, Any], facts: bool) -> list[dict[str, Any]]:
    """Blocks for schema keys that have no custom block, by shape, in schema order: an object -> kv; a list of
    {field, value, location, confidence} -> facts (Page 2 only); another list of objects -> table; a list of
    strings -> list; consecutive plain values -> one kv (a single one -> text)."""
    out: list[dict[str, Any]] = []
    plain: list[str] = []

    def flush() -> None:
        if len(plain) == 1:
            out.append({"title": humanize(plain[0]), "text": plain[0]})
        elif plain:
            out.append({"kv": list(plain)})
        plain.clear()

    for key, shape in schema.items():
        if not isinstance(shape, dict | list):
            plain.append(key)
            continue
        flush()
        item = shape[0] if isinstance(shape, list) and shape else None
        if isinstance(shape, dict):
            out.append({"title": humanize(key), "kv": key})
        elif isinstance(item, dict) and facts and set(FACT_KEYS) <= set(item):
            out.append({"facts": key})
        elif isinstance(item, dict):
            out.append({"title": humanize(key), "table": key})
        else:
            out.append({"title": humanize(key), "list": key})
    flush()
    return out


def resolve_view(view: list[dict[str, Any]], hide: list[str], schema: dict[str, Any] | None, skip: tuple[str, ...],
                 where: str, facts: bool) -> list[dict[str, Any]]:
    """The agent's full view: its custom blocks, then a default block for every other schema key that is not hidden
    (or, for a report, one of the report-framework keys shown by the page itself). An external agent's result is
    only known at run time, so it needs a complete view."""
    if schema is None:
        if not view:
            raise AgentError(f"{where}: an external agent needs a view (its result shape is unknown until it runs)")
        check_view(view, None, where, facts)
        return view
    unknown = [k for k in hide if k not in schema]
    if unknown:
        raise AgentError(f"{where}: hide {', '.join(unknown)}: not in the agent's schema")
    check_view(view, schema, where, facts)
    shown = {p.split(".")[0] for b in view for p in block_paths(b)}
    rest = {k: s for k, s in schema.items() if k not in shown and k not in hide and k not in skip}
    return view + default_view(rest, facts)


def block_paths(block: dict[str, Any]) -> list[str]:
    paths = block[block_kind(block)]
    return list(paths) if isinstance(paths, list) else [paths]


def provider(name: str, spec: AgentSpec, label: str, skills: Path, inputs: set[str], source: Path,
             where: str) -> Provider:
    try:
        return make_provider(name, {**spec.provider_spec(), "label": label}, skills, inputs, source)
    except AgentError as e:
        raise AgentError(f"{where}: {e}") from None


def lane_agent(ln: LaneSpec, skills: Path, source: Path, where: str) -> Agent:
    """A lane's insight agent: one job per file (`per: file`) or one job over the lane's files as text (`lane`)."""
    spec, at = ln.agent, f"{where} lane {ln.name}"
    assert spec is not None
    p = provider(ln.name, spec, spec.label or f"{humanize(ln.name)} agent", skills, AGENT_INPUTS[spec.per], source,
                 at)
    return Agent(p, spec.per, resolve_view(ln.view, ln.hide, p.schema, (), at, facts=True))


# ---------------------------------------------------------------------- loading
def load_app(name: str, path: Path, pulls: dict[str, DataPull], skills: Path) -> App:
    """`skills`: the skill library every app's agents draw on (studio.yaml `skills`)."""
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
        if not ln.agent and (ln.view or ln.hide):
            raise AgentError(f"{where}: lane {ln.name}: view / hide need an agent")

    for f in spec.fields:
        f.label = f.label or humanize(f.name)
    for ln in spec.lanes:
        ln.label = ln.label or humanize(ln.name)
    spec.case.prefix = spec.case.prefix or f"{name.upper()}-{time.strftime('%Y')}-"

    agents = {ln.name: lane_agent(ln, skills, path, where) for ln in spec.lanes if ln.agent}
    rp = provider("report", spec.report, spec.report.label or "Report agent", skills, REPORT_INPUTS, path, where)
    if rp.schema is not None:
        check_envelope(rp.schema, spec.report.verdicts, f"{where} report")
    report_view = resolve_view(spec.report.view, spec.report.hide, rp.schema, ENVELOPE, f"{where} report",
                               facts=False)
    extras = {k: provider(k, e, e.label or humanize(k), skills, EXTRA_INPUTS, path, where)
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

    return App(name, spec, agents, Report(rp, spec.report.name, spec.report.verdicts, report_view), extras,
               spec.pulls, sample)
