"""Guardrails for agents that read untrusted documents (confined reads) and for structured step outputs."""

from __future__ import annotations

import json

import pytest

from kentc_agent.adapters.llm import Reply
from kentc_agent.adapters.tools import CORE_TOOLS, ToolError
from kentc_agent.workflow import Runner, WorkflowError, load

from .conftest import FakeLLM


def no_llm(messages, tools):
    raise AssertionError("no model call expected")


# ---------------------------------------------------------------------- confined reads
def test_confined_read_refuses_outside_paths_and_symlink_escapes(make_ctx, tmp_path):
    secret = tmp_path.parent / f"{tmp_path.name}-secret.txt"
    secret.write_text("api key")
    (tmp_path / "doc.txt").write_text("case note")
    (tmp_path / "link.txt").symlink_to(secret)
    read = CORE_TOOLS["read"].run

    open_ctx = make_ctx(FakeLLM(no_llm))
    assert read(open_ctx, {"path": str(secret)}) == "api key"           # the CLI default: reads go anywhere

    ctx = make_ctx(FakeLLM(no_llm))
    ctx.confine_reads = True
    assert read(ctx, {"path": "doc.txt"}) == "case note"
    for path in (str(secret), f"../{secret.name}", "link.txt"):
        with pytest.raises(ToolError, match="reads are limited to the workspace"):
            read(ctx, {"path": path})


# ---------------------------------------------------------------------- JSON step output shape
REPORT_WF = """
steps:
  - id: report
    tools: []
    prompt: Write the report.
    format: json
    schema:
      key_risks: [{id: "KR-01", score: number, title: string}]
      recommendation: {next_step: "Agree|Further investigation", scope: string}
      confidence: number
"""

GOOD = {"key_risks": [{"id": "KR-01", "score": 80, "title": "Layering"}],
        "recommendation": {"next_step": "further INVESTIGATION", "scope": "trace onward payments"}, "confidence": 0.7}


def run_report(make_ctx, tmp_path, replies: list[dict]) -> tuple[dict, FakeLLM]:
    (tmp_path / "wf.yaml").write_text(REPORT_WF)
    it = iter(replies)
    llm = FakeLLM(lambda messages, tools: Reply(content=json.dumps(next(it)), finish="stop"), window=32000)
    ctx = make_ctx(llm, reserve_tokens=2000, keep_recent_tokens=2000, max_output_tokens=2000)
    state = Runner(load(tmp_path / "wf.yaml"), ctx, {}, tmp_path / "run").run()
    return state, llm


def test_wrong_types_and_enum_values_are_rejected_then_canonicalized(make_ctx, tmp_path):
    bad = {"key_risks": [{"id": "KR-01", "score": "high", "title": "Layering"}],
           "recommendation": {"next_step": "Exit the client"}, "confidence": None}
    state, llm = run_report(make_ctx, tmp_path, [bad, GOOD])
    assert all("Exit the client" not in json.dumps(r["messages"]) for r in llm.requests[1:])
    assert state["steps"]["report"]["data"]["recommendation"]["next_step"] == "Further investigation"


def test_step_fails_instead_of_storing_a_report_that_never_fits(make_ctx, tmp_path):
    bad = {**GOOD, "key_risks": [{"id": "KR-01", "score": True, "title": "Layering"}]}
    with pytest.raises(WorkflowError, match=r"'key_risks\[0\]\.score' must be a number, got boolean"):
        run_report(make_ctx, tmp_path, [bad, bad, bad])
    state = json.loads((tmp_path / "run" / "state.json").read_text())
    assert state["steps"]["report"]["status"] == "failed"


# ---------------------------------------------------------------------- a wrong folder input, fixed on resume
def test_missing_docs_folder_fails_clearly_and_resume_can_override_the_input(make_ctx, tmp_path, monkeypatch):
    import sys

    from kentc_agent import cli

    (tmp_path / "statement.txt").write_text("card spend 120.50")
    (tmp_path / "wf.yaml").write_text("inputs:\n  docs_dir: {default: docs}\nsteps:\n"
                                      "  - id: review\n    prompt: \"Read {{ documents(inputs.docs_dir) | join(', ') }}\"\n")
    seen = []
    monkeypatch.setattr(cli, "make_context", lambda args, ui: make_ctx(FakeLLM(
        lambda m, t: seen.append(m[-1]["content"]) or Reply(content="ok", finish="stop"))))
    run = ["kentc-agent", "-w", str(tmp_path), "--workflow", str(tmp_path / "wf.yaml")]
    monkeypatch.setattr(sys, "argv", run)
    with pytest.raises(WorkflowError, match=r"documents\('docs'\): no such folder in .*--resume latest -i KEY=VALUE"):
        cli.run_workflow(cli.parser().parse_args(run[1:]))
    assert not seen                                                   # failed before any model call
    monkeypatch.setattr(sys, "argv", ["kentc-agent", "-w", str(tmp_path), "--resume", "latest", "-i", "docs_dir=."])
    cli.run_workflow(cli.parser().parse_args(sys.argv[1:]))
    assert "statement.txt" in seen[-1]
    with pytest.raises(SystemExit, match="unknown input"):
        cli.run_workflow(cli.parser().parse_args(["-w", str(tmp_path), "--resume", "latest", "-i", "nope=1"]))


# ---------------------------------------------------------------------- out of turns is a failure, not a result
def test_step_out_of_turns_fails_without_writing_its_output(make_ctx, tmp_path):
    from .conftest import call

    (tmp_path / "wf.yaml").write_text("steps:\n  - id: insight\n    tools: [bash]\n    max_turns: 2\n"
                                      "    prompt: Write the report.\n    output: reports/insight.md\n")
    llm = FakeLLM(lambda m, t: Reply(tool_calls=[call("bash", json.dumps({"command": "true"}))], finish="tool_calls"),
                  window=32000)
    runner = Runner(load(tmp_path / "wf.yaml"), make_ctx(llm, reserve_tokens=2000, keep_recent_tokens=2000), {},
                    tmp_path / "run")
    with pytest.raises(WorkflowError, match=r"insight: no final answer within max_turns \(2\)"):
        runner.run()
    assert runner.state["steps"]["insight"]["status"] == "failed"
    assert not (tmp_path / "reports" / "insight.md").exists()


# ---------------------------------------------------------------------- max_turns: 0 = no limit, until the answer
def unlimited_runner(make_ctx, tmp_path, script):
    (tmp_path / "wf.yaml").write_text("steps:\n  - id: deliver\n    tools: [bash]\n    max_turns: 0\n"
                                      "    prompt: Deliver it.\n    output: reports/summary.md\n")
    llm = FakeLLM(script, window=64000)
    return Runner(load(tmp_path / "wf.yaml"), make_ctx(llm, reserve_tokens=2000, keep_recent_tokens=2000), {},
                  tmp_path / "run")


def test_no_turn_limit_runs_past_the_default_until_the_answer(make_ctx, tmp_path):
    from .conftest import call

    turns = []

    def script(messages, tools):
        turns.append(1)
        if len(turns) <= 70:                                   # more than the default 60, each call different
            return Reply(tool_calls=[call("bash", json.dumps({"command": f"echo {len(turns)}"}), f"c{len(turns)}")],
                         finish="tool_calls")
        return Reply(content="delivered", finish="stop")

    state = unlimited_runner(make_ctx, tmp_path, script).run()
    assert len(turns) == 71 and state["steps"]["deliver"]["status"] == "done"
    assert (tmp_path / "reports" / "summary.md").read_text() == "delivered"


def test_negative_max_turns_is_refused_when_the_workflow_loads(tmp_path):
    (tmp_path / "wf.yaml").write_text("steps:\n  - id: s\n    max_turns: -1\n    prompt: hi\n")
    with pytest.raises(WorkflowError, match="max_turns must be a whole number >= 0"):
        load(tmp_path / "wf.yaml")


# ---------------------------------------------------------------------- studio agents: skills + contract, checked loop
def studio_agent(make_ctx, tmp_path, answers: list[dict], max_turns: int, **settings):
    from kentc_studio.apps import AGENT_INPUTS
    from kentc_studio.providers import make_provider

    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "extraction.md").write_text("---\ndescription: x\n---\nCite {{ the page }} for every value.")
    spec = {"skills": ["extraction"], "max_turns": max_turns,
            "output": {"key_values": [{"field": "string", "location": "string", "confidence": "number"}]},
            "checks": {"key_values": "min 1", "key_values[].location": "required",
                       "key_values[].confidence": "0..100"}}
    agent = make_provider("evidence", spec, tmp_path / "skills", AGENT_INPUTS["file"], tmp_path / "app.yaml")
    it = iter(answers)
    llm = FakeLLM(lambda messages, tools: Reply(content=json.dumps(next(it)), finish="stop"), window=32000)
    ctx = make_ctx(llm, reserve_tokens=2000, keep_recent_tokens=2000, max_output_tokens=2000, **settings)

    def run():
        return agent.run(case_dir=tmp_path, job_dir=tmp_path / "job", inputs={"file": "docs/a.pdf", "case_brief": "C-1"},
                         events=ctx.events, settings=ctx.settings, llm=llm, request={})
    return run, llm


def test_studio_agent_works_until_its_answer_passes_the_checks(make_ctx, tmp_path):
    no_values = {"key_values": []}
    no_location = {"key_values": [{"field": "amount", "location": " ", "confidence": 90}]}
    percent = {"key_values": [{"field": "amount", "location": "p1", "confidence": 900}]}
    good = {"key_values": [{"field": "amount", "location": "p1", "confidence": 90}]}
    run, llm = studio_agent(make_ctx, tmp_path, [no_values, no_location, percent, good],
                            max_turns=10, output_retries=3)
    assert run() == good
    accepted = [m for r in llm.requests[1:] for m in r["messages"] if m["role"] == "assistant"]
    assert accepted == []
    assert "'key_values' needs min 1 items, has 0" in llm.requests[1]["messages"][-1]["content"]
    assert "'key_values[0].location' is required (empty)" in llm.requests[2]["messages"][-1]["content"]
    assert "'key_values[0].confidence' must be within 0..100, got 900" in llm.requests[3]["messages"][-1]["content"]


def test_studio_agent_stops_after_bounded_invalid_output_retries(make_ctx, tmp_path):
    bad = {"key_values": []}
    run, llm = studio_agent(make_ctx, tmp_path, [bad] * 5, max_turns=10, output_retries=2)
    with pytest.raises(WorkflowError):
        run()
    assert len(llm.requests) == 3
    state = json.loads((tmp_path / "job" / "state.json").read_text())
    assert state["steps"]["evidence"]["status"] == "failed"
    assert "data" not in state["steps"]["evidence"]


def test_workflow_template_helpers_respect_confine_reads_and_max_chars(make_ctx, tmp_path):
    secret = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    secret.write_text("outside secret")
    (tmp_path / "inside.txt").write_text("A" * 200)
    (tmp_path / "link.txt").symlink_to(secret)
    (tmp_path / "wf.yaml").write_text("steps:\n  - id: s\n    prompt: hi\n")

    ctx = make_ctx(FakeLLM(no_llm))
    ctx.confine_reads = True
    runner = Runner(load(tmp_path / "wf.yaml"), ctx, {}, tmp_path / "run")

    assert runner._glob("*.txt") == ["inside.txt"]
    for bad in (str(secret), f"../{secret.name}", "link.txt"):
        with pytest.raises(ToolError, match="reads are limited to the workspace"):
            runner._read_file(bad)
    with pytest.raises(ToolError, match="reads are limited to the workspace"):
        runner._documents("..")

    truncated = runner._read_file("inside.txt", 50)
    assert truncated.startswith("A" * 50)
    assert "150 chars truncated; read inside.txt with offset/limit" in truncated


def test_office_media_skips_oversized_embedded_files(make_ctx, tmp_path, monkeypatch):
    import zipfile
    import kentc_agent.adapters.documents.loaders as loaders_mod
    from kentc_agent.adapters.documents.common import Source

    monkeypatch.setattr(loaders_mod, "MAX_MEDIA_BYTES", 100)
    docx_path = tmp_path / "sample.docx"
    with zipfile.ZipFile(docx_path, "w") as z:
        z.writestr("word/media/small.png", b"x" * 50)
        z.writestr("word/media/huge.png", b"y" * 250)

    src = Source(docx_path, "docx", "sample.docx")
    loaders_mod.office_media(make_ctx(FakeLLM(no_llm)), docx_path, src)
    assert [p.name for p in src.attachments] == ["small.png"]
    assert "1 embedded image(s) saved as attachments" in src.notes
    assert "1 embedded image(s) skipped (exceeded size limit)" in src.notes
