"""Studio apps: what a manifest may declare, and how its report view renders."""

from __future__ import annotations

import json

import pytest

from kentc_studio.config import load_config
from kentc_studio.models import Case
from kentc_studio.providers import AgentError
from kentc_studio.report import to_markdown
from kentc_studio.store import CaseStore

READER = """
inputs:
  file: {required: true}
  case_brief: {required: true}
  feedback: {default: ""}
  previous: {default: ""}
steps:
  - id: read
    tools: [read]
    prompt: Read {{ inputs.file }}.
    format: json
    schema:
      summary: string
      key_values: [{field: string, value: string, location: string, confidence: number}]
"""

REPORT = """
inputs:
  materials_file: {required: true}
  case_brief: {required: true}
  instruction: {default: ""}
  previous_report_file: {default: ""}
steps:
  - id: report
    tools: [read]
    prompt: Write it.
    format: json
    schema:
      title: string
      verdict: "Go|Hold"
      reply: string
      requests: [{document: string, reason: string}]
      questions: [string]
      summary: string
      risks: [{title: string, score: number, reason: string}]
"""

APP = """
title: Test app
brief: "Case {{ id }} about {{ subject }}"
fields:
  - {name: subject, required: true, column: true}
lanes:
  - {name: files, required: true, agent: reader}
agents:
  reader:
    workflow: reader.yaml
    view: [{facts: key_values}, {text: summary}]
report:
  name: Test report
  workflow: report.yaml
  verdicts: {Go: ok, Hold: warn}
  view:
    - {title: Summary, text: summary}
    - {title: Risks, cards: risks, head: title, score: score, body: reason}
"""


def studio(tmp_path, app=APP, reader=READER, report=REPORT, extra=""):
    (tmp_path / "reader.yaml").write_text(reader)
    (tmp_path / "report.yaml").write_text(report)
    (tmp_path / "app.yaml").write_text(app)
    (tmp_path / "studio.yaml").write_text("apps:\n  test: app.yaml\n" + extra)
    return tmp_path / "studio.yaml"


# ---------------------------------------------------------------------- untrusted documents: no shell, no web
@pytest.mark.parametrize("report, refused", [
    (REPORT.replace("tools: [read]", "tools: [read, bash]"), "offers bash "),
    (REPORT.replace("    tools: [read]\n", ""), "offers bash "),                 # omitted tools = all tools
    (REPORT.split("    tools: [read]")[0] + "    web: latest AML news\n", "has web step\\(s\\) report;"),
])
def test_studio_refuses_agents_with_shell_or_web_access(tmp_path, report, refused):
    with pytest.raises(AgentError, match=f"agent report: report.yaml {refused}"):
        load_config(studio(tmp_path, report=report))


# ---------------------------------------------------------------------- manifest checks at load
@pytest.mark.parametrize("app, refused", [
    (APP.replace("{text: summary}]", "{text: summry}]"),
     r"agent reader: view\[1\]: text 'summry' is not in the agent's schema"),
    (APP.replace("head: title", "head: name"), r"report: view\[1\]: name not in the items of 'risks'"),
    (APP.replace("{title: Summary, text: summary}", "{title: Summary, facts: risks}"),
     "facts \\(flaggable rows\\) belong to the insight agents"),
    (APP.replace("{Go: ok, Hold: warn}", "{Go: ok, Stop: bad}"), "verdicts must give a tone .* for each verdict: Go, Hold"),
    (APP.replace("agent: reader}", "agent: nobody}"), "lane files: agent 'nobody' is not under agents"),
])
def test_app_manifest_mistakes_are_refused_when_the_studio_loads(tmp_path, app, refused):
    with pytest.raises(AgentError, match=refused):
        load_config(studio(tmp_path, app=app))


def test_report_without_the_framework_keys_is_refused(tmp_path):
    report = REPORT.replace("      reply: string\n", "").replace("      questions: [string]\n", "")
    with pytest.raises(AgentError, match=r"report-framework keys .* \(missing reply, questions\)"):
        load_config(studio(tmp_path, report=report))


def test_agent_workflow_must_take_the_inputs_the_studio_passes(tmp_path):
    reader = READER.replace('  previous: {default: ""}\n', "").replace("  case_brief: {required: true}\n",
                                                                     "  case_brief: {required: true}\n"
                                                                     "  ticket: {required: true}\n")
    with pytest.raises(AgentError, match="must declare the inputs .* \\(missing previous\\); the studio never passes "
                                         "required ticket"):
        load_config(studio(tmp_path, reader=reader))


def test_data_pull_may_only_bind_fields_of_the_app_offering_it(tmp_path):
    (tmp_path / "q.sql").write_text("SELECT * FROM t WHERE cif = :cif AND id = :case_id AND s = :subject")
    extra = "databases:\n  core: {url: 'sqlite:///db.sqlite'}\ndata_pulls:\n  p: {database: core, sql_file: q.sql}\n"
    with pytest.raises(AgentError, match="data pull p binds :cif, which are not fields of this app"):
        load_config(studio(tmp_path, app=APP + "pulls: [p]\n", extra=extra))


# ---------------------------------------------------------------------- the report view renders the export
def test_report_markdown_follows_the_view_and_the_framework(tmp_path):
    app = load_config(studio(tmp_path)).apps["test"]
    data = {"title": "Acme", "verdict": "Hold", "reply": "Added the second risk.", "summary": "Two risks.",
            "requests": [{"document": "Bank statement", "reason": "to trace the inflow"}], "questions": ["Who signs?"],
            "risks": [{"title": "Low", "score": 20, "reason": "minor"}, {"title": "High", "score": 90, "reason": "major"}]}
    md = to_markdown(app, "C-1", {"subject": "Acme trade"}, data, 2)
    assert md.startswith("# Test report - Acme\n**Case** C-1 · **Subject** Acme trade · **Version** v2")
    assert "**Verdict:** Hold" in md
    assert md.index("### High (score 90)") < md.index("### Low (score 20)")      # cards sorted by score
    assert "- **Bank statement** - to trace the inflow" in md and "- Who signs?" in md
    assert md.rstrip().endswith("*Agent reply: Added the second risk.*")


# ---------------------------------------------------------------------- cases from before studio apps
def test_cases_created_before_apps_are_skipped_not_deleted(tmp_path):
    old = tmp_path / "TER-1" / "case.json"
    old.parent.mkdir()
    old.write_text(json.dumps({"id": "TER-1", "cif": "CIF-1", "documents": [], "jobs": []}))
    new = tmp_path / "C-2" / "case.json"
    new.parent.mkdir()
    new.write_text(json.dumps({"id": "C-2", "app": "test", "fields": {"subject": "x"},
                               "jobs": [{"id": "j", "role": "report", "agent": "report", "status": "running"}]}))
    cases = CaseStore(tmp_path).load_all(Case, {"test"})
    assert list(cases) == ["C-2"] and old.is_file()
    assert cases["C-2"].jobs[0].status == "stopped"                    # interrupted by the restart
