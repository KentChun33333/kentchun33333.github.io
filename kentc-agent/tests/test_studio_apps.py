"""Studio apps: what a manifest may declare, and how its report view renders."""

from __future__ import annotations

import json

import pytest

from kentc_studio.config import load_config
from kentc_studio.models import Case
from kentc_studio.providers import AgentError
from kentc_studio.report import to_markdown
from kentc_studio.store import CaseStore

READER = """\
      skills: [reading]
      output:
        summary: string
        key_values: [{field: string, value: string, location: string, confidence: number}]
"""

REPORT = """\
  skills: [reporting]
  tools: [read]
  output:
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
fields:
  - {name: subject, required: true, column: true}
  - {name: note, label: Analyst note}
lanes:
  - name: files
    required: true
    view: [{facts: key_values}, {text: summary}]
    agent:
{reader}report:
  name: Test report
  verdicts: {Go: ok, Hold: warn}
  view:
    - {title: Summary, text: summary}
    - {title: Risks, cards: risks, head: title, score: score, body: reason}
{report}"""


def studio(tmp_path, app=APP, reader=READER, report=REPORT, extra=""):
    (tmp_path / "skills").mkdir(exist_ok=True)
    (tmp_path / "skills" / "reading.md").write_text("Read the file.")
    (tmp_path / "skills" / "reporting.md").write_text("Write the report.")
    (tmp_path / "app.yaml").write_text(app.replace("{reader}", reader).replace("{report}", report))
    (tmp_path / "studio.yaml").write_text("apps:\n  test: app.yaml\nskills: skills\n" + extra)
    return tmp_path / "studio.yaml"


# ---------------------------------------------------------------------- untrusted documents: no shell
def test_studio_refuses_agents_with_a_shell(tmp_path):
    with pytest.raises(AgentError, match="app test: agent report: offers bash; studio agents read untrusted"):
        load_config(studio(tmp_path, report=REPORT.replace("tools: [read]", "tools: [read, bash]")))


# ---------------------------------------------------------------------- manifest checks at load
@pytest.mark.parametrize("app, reader, report, refused", [
    (APP.replace("{text: summary}]", "{text: summry}]"), READER, REPORT,
     r"lane files: view\[1\]: text 'summry' is not in the agent's schema"),
    (APP.replace("head: title", "head: name"), READER, REPORT, r"report: view\[1\]: name not in the items of 'risks'"),
    (APP.replace("{title: Summary, text: summary}", "{title: Summary, facts: risks}"), READER, REPORT,
     "facts \\(flaggable rows\\) belong to the insight agents"),
    (APP.replace("{Go: ok, Hold: warn}", "{Go: ok, Stop: bad}"), READER, REPORT,
     "verdicts must give a tone .* for each verdict: Go, Hold"),
    (APP.replace("    agent:\n{reader}", ""), READER, REPORT, "lane files: view / hide need an agent"),
    (APP, READER.replace("[reading]", "[reading, triage]"), REPORT,
     r"lane files: agent files: skill 'triage': .*triage\.md not found"),
    (APP, READER, REPORT.replace("[reporting]", "[]"), "agent report: needs at least one skill"),
    (APP, READER.split("      output:")[0], REPORT, "agent files: output must give the JSON answer's shape"),
    (APP, READER + "      checks:\n        key_values[].confidance: 0..100\n", REPORT,
     r"checks: key_values\[\]\.confidance: not in the output"),
    (APP, READER + "      checks: {summary: 0..100}\n", REPORT, "summary: 0..100: a range needs a number"),
    (APP, READER + "      checks: {summary: shortish}\n", REPORT, "summary: unknown rule 'shortish'"),
    (APP, "      url: http://agent:9000\n" + READER, REPORT, "an external \\(url\\) agent takes no skills, output"),
])
def test_app_manifest_mistakes_are_refused_when_the_studio_loads(tmp_path, app, reader, report, refused):
    with pytest.raises(AgentError, match=refused):
        load_config(studio(tmp_path, app=app, reader=reader, report=report))


def test_report_without_the_framework_keys_is_refused(tmp_path):
    report = REPORT.replace("    reply: string\n", "").replace("    questions: [string]\n", "")
    with pytest.raises(AgentError, match=r"report-framework keys .* \(missing reply, questions\)"):
        load_config(studio(tmp_path, report=report))


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


# ---------------------------------------------------------------------- defaults: views from the schema, brief from fields
def test_keys_without_a_custom_block_are_shown_by_shape_in_schema_order_unless_hidden(tmp_path):
    reader = READER.replace("        summary: string\n", "        summary: string\n        risk: number\n").replace(
        "        key_values:", "        parties: [{name: string, role: string}]\n        owner: {name: string}\n"
                              "        gaps: [string]\n        key_values:")
    app = APP.replace("view: [{facts: key_values}, {text: summary}]", "view: [{title: Gaps, list: gaps}]\n"
                                                                       "    hide: [risk]")
    view = load_config(studio(tmp_path, app=app, reader=reader)).apps["test"].agents["files"].view
    assert view == [{"title": "Gaps", "list": "gaps"}, {"title": "Summary", "text": "summary"},
                    {"title": "Parties", "table": "parties"}, {"title": "Owner", "kv": "owner"},
                    {"facts": "key_values"}]


def test_hiding_a_key_the_agent_does_not_return_is_refused(tmp_path):
    with pytest.raises(AgentError, match="lane files: hide risk: not in the agent's schema"):
        load_config(studio(tmp_path, app=APP.replace("view: [{facts: key_values}, {text: summary}]", "hide: [risk]")))


def test_brief_lists_the_filled_fields_by_label(tmp_path):
    app = load_config(studio(tmp_path)).apps["test"]
    assert app.brief("C-1", {"subject": "Acme  trade\nimports", "note": ""}) == \
        "Case C-1 (Test app). Subject: Acme trade imports."
    assert app.brief("C-1", {"subject": "Why?", "note": "check"}) == \
        "Case C-1 (Test app). Subject: Why?; Analyst note: check."


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


def test_read_uploads_rejects_oversized_file(monkeypatch):
    import asyncio
    import io
    from fastapi import HTTPException, UploadFile
    import kentc_studio.api.app as app_mod

    monkeypatch.setattr(app_mod, "MAX_UPLOAD_BYTES", 10)
    small = UploadFile(filename="ok.txt", file=io.BytesIO(b"hello"))
    assert asyncio.run(app_mod.read_uploads([small], ["files"])) == [("ok.txt", "files", b"hello")]

    big = UploadFile(filename="huge.txt", file=io.BytesIO(b"x" * 20))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(app_mod.read_uploads([big], ["files"]))
    assert exc.value.status_code == 413
