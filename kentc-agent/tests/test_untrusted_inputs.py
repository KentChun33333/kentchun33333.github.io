"""Guardrails for agents that read untrusted documents (confined reads) and for structured step outputs."""

from __future__ import annotations

import json
import zipfile

import pytest

from kentc_agent.adapters.documents.common import Source
from kentc_agent.adapters.llm import Reply
from kentc_agent.adapters.tools import CORE_TOOLS, ToolError
from kentc_agent.fsm_workflow import Runner, WorkflowError, load

from .conftest import FakeLLM, call


# ---------------------------------------------------------------------- confined reads & template helpers
def test_confined_read_refuses_outside_paths_and_symlink_escapes(make_ctx, tmp_path):
    secret = tmp_path.parent / f"{tmp_path.name}-secret.txt"
    secret.write_text("api key")
    (tmp_path / "doc.txt").write_text("case note" * 20)
    (tmp_path / "link.txt").symlink_to(secret)
    (tmp_path / "wf.yaml").write_text("steps:\n  - id: s\n    prompt: hi\n")
    read = CORE_TOOLS["read"].run

    assert read(make_ctx(), {"path": str(secret)}) == "api key"         # CLI default: reads go anywhere

    ctx = make_ctx()
    ctx.confine_reads = True
    runner = Runner(load(tmp_path / "wf.yaml"), ctx, {}, tmp_path / "run")
    assert read(ctx, {"path": "doc.txt"}).startswith("case note")
    assert runner._glob("*.txt") == ["doc.txt"]
    for path in (str(secret), f"../{secret.name}", "link.txt"):
        with pytest.raises(ToolError, match="reads are limited to the workspace"):
            read(ctx, {"path": path})
        with pytest.raises(ToolError, match="reads are limited to the workspace"):
            runner._read_file(path)
    with pytest.raises(ToolError, match="reads are limited to the workspace"):
        runner._documents("..")
    assert "chars truncated; read doc.txt with offset/limit" in runner._read_file("doc.txt", 30)


def test_office_media_skips_oversized_embedded_files(make_ctx, tmp_path, monkeypatch):
    import kentc_agent.adapters.documents.loaders as loaders_mod

    monkeypatch.setattr(loaders_mod, "MAX_MEDIA_BYTES", 100)
    docx = tmp_path / "sample.docx"
    with zipfile.ZipFile(docx, "w") as z:
        z.writestr("word/media/small.png", b"x" * 50)
        z.writestr("word/media/huge.png", b"y" * 250)
    src = Source(docx, "docx", "sample.docx")
    loaders_mod.office_media(make_ctx(), docx, src)
    assert [p.name for p in src.attachments] == ["small.png"]
    assert "1 embedded image(s) skipped (exceeded size limit)" in src.notes


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
    llm = FakeLLM(lambda m, t: Reply(content=json.dumps(next(it)), finish="stop"), window=32000)
    ctx = make_ctx(llm, reserve_tokens=2000, keep_recent_tokens=2000, max_output_tokens=2000)
    return Runner(load(tmp_path / "wf.yaml"), ctx, {}, tmp_path / "run").run(), llm


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
    assert json.loads((tmp_path / "run" / "state.json").read_text())["steps"]["report"]["status"] == "failed"


# ---------------------------------------------------------------------- a wrong folder input, fixed on resume
def test_missing_docs_folder_fails_clearly_and_resume_can_override_the_input(make_ctx, tmp_path, monkeypatch):
    import sys
    from kentc_agent import cli

    (tmp_path / "statement.txt").write_text("card spend 120.50")
    (tmp_path / "wf.yaml").write_text("inputs:\n  docs_dir: {default: docs}\nsteps:\n"
                                      "  - id: review\n    prompt: \"Read {{ documents(inputs.docs_dir) | join(', ') }}\"\n")
    seen = []
    monkeypatch.setattr(cli, "make_context", lambda args, ui: make_ctx(FakeLLM(
        lambda m, t: seen.append(m[-2]["content"]) or Reply(content="ok", finish="stop"))))  # [-1]: budget notice
    run = ["kentc-agent", "-w", str(tmp_path), "--workflow", str(tmp_path / "wf.yaml")]
    monkeypatch.setattr(sys, "argv", run)
    with pytest.raises(WorkflowError, match=r"documents\('docs'\): no such folder in .*--resume latest -i KEY=VALUE"):
        cli.run_workflow(cli.parser().parse_args(run[1:]))
    assert not seen
    monkeypatch.setattr(sys, "argv", ["kentc-agent", "-w", str(tmp_path), "--resume", "latest", "-i", "docs_dir=."])
    cli.run_workflow(cli.parser().parse_args(sys.argv[1:]))
    assert "statement.txt" in seen[-1]
    with pytest.raises(SystemExit, match="unknown input"):
        cli.run_workflow(cli.parser().parse_args(["-w", str(tmp_path), "--resume", "latest", "-i", "nope=1"]))


# ---------------------------------------------------------------------- turn limits
def test_step_out_of_turns_fails_without_writing_its_output(make_ctx, tmp_path):
    (tmp_path / "wf.yaml").write_text("steps:\n  - id: insight\n    tools: [bash]\n    max_turns: 2\n"
                                      "    prompt: Write the report.\n    output: reports/insight.md\n")
    llm = FakeLLM(lambda m, t: Reply(tool_calls=[call("bash", '{"command": "true"}')], finish="tool_calls"), window=32000)
    runner = Runner(load(tmp_path / "wf.yaml"), make_ctx(llm, reserve_tokens=2000, keep_recent_tokens=2000), {},
                    tmp_path / "run")
    with pytest.raises(WorkflowError, match=r"insight: no final answer within max_turns \(2\)"):
        runner.run()
    assert runner.state["steps"]["insight"]["status"] == "failed" and not (tmp_path / "reports/insight.md").exists()


def test_no_turn_limit_runs_past_the_default_until_the_answer_and_rejects_negative_turns(make_ctx, tmp_path):
    (tmp_path / "bad.yaml").write_text("steps:\n  - id: s\n    max_turns: -1\n    prompt: hi\n")
    with pytest.raises(WorkflowError, match="max_turns must be a whole number >= 0"):
        load(tmp_path / "bad.yaml")

    (tmp_path / "wf.yaml").write_text("steps:\n  - id: deliver\n    tools: [bash]\n    max_turns: 0\n"
                                      "    prompt: Deliver it.\n    output: reports/summary.md\n")
    turns = []
    def script(messages, tools):
        turns.append(1)
        if len(turns) <= 70:
            return Reply(tool_calls=[call("bash", json.dumps({"command": f"echo {len(turns)}"}), f"c{len(turns)}")],
                         finish="tool_calls")
        return Reply(content="delivered", finish="stop")
    state = Runner(load(tmp_path / "wf.yaml"), make_ctx(FakeLLM(script, window=64000), reserve_tokens=2000,
                   keep_recent_tokens=2000), {}, tmp_path / "run").run()
    assert len(turns) == 71 and state["steps"]["deliver"]["status"] == "done"
    assert (tmp_path / "reports" / "summary.md").read_text() == "delivered"


# ---------------------------------------------------------------------- studio agents: skills + contract, checked loop
def studio_agent(make_ctx, tmp_path, answers: list[dict], max_turns: int, **settings):
    from kentc_studio.apps import AGENT_INPUTS
    from kentc_studio.providers import make_provider

    (tmp_path / "skills").mkdir(exist_ok=True)
    (tmp_path / "skills" / "extraction.md").write_text("---\ndescription: x\n---\nCite {{ the page }} for every value.")
    spec = {"skills": ["extraction"], "max_turns": max_turns,
            "output": {"key_values": [{"field": "string", "location": "string", "confidence": "number"}]},
            "checks": {"key_values": "min 1", "key_values[].location": "required",
                       "key_values[].confidence": "0..100"}}
    agent = make_provider("evidence", spec, tmp_path / "skills", AGENT_INPUTS["file"], tmp_path / "app.yaml")
    it = iter(answers)
    llm = FakeLLM(lambda m, t: Reply(content=json.dumps(next(it)), finish="stop"), window=32000)
    ctx = make_ctx(llm, reserve_tokens=2000, keep_recent_tokens=2000, max_output_tokens=2000, **settings)
    return (lambda: agent.run(case_dir=tmp_path, job_dir=tmp_path / "job",
                              inputs={"file": "docs/a.pdf", "case_brief": "C-1"},
                              events=ctx.events, settings=ctx.settings, llm=llm, request={})), llm


def test_studio_agent_works_until_its_answer_passes_the_checks(make_ctx, tmp_path):
    no_values = {"key_values": []}
    no_location = {"key_values": [{"field": "amount", "location": " ", "confidence": 90}]}
    percent = {"key_values": [{"field": "amount", "location": "p1", "confidence": 900}]}
    good = {"key_values": [{"field": "amount", "location": "p1", "confidence": 90}]}
    run, llm = studio_agent(make_ctx, tmp_path, [no_values, no_location, percent, good], max_turns=10, output_retries=3)
    assert run() == good
    assert [m for r in llm.requests[1:] for m in r["messages"] if m["role"] == "assistant"] == []
    assert "'key_values' needs min 1 items, has 0" in llm.requests[1]["messages"][-1]["content"]
    assert "'key_values[0].location' is required (empty)" in llm.requests[2]["messages"][-1]["content"]
    assert "'key_values[0].confidence' must be within 0..100, got 900" in llm.requests[3]["messages"][-1]["content"]


def test_studio_agent_stops_after_bounded_invalid_output_retries(make_ctx, tmp_path):
    run, llm = studio_agent(make_ctx, tmp_path, [{"key_values": []}] * 5, max_turns=10, output_retries=2)
    with pytest.raises(WorkflowError):
        run()
    assert len(llm.requests) == 3
    step = json.loads((tmp_path / "job" / "state.json").read_text())["steps"]["evidence"]
    assert step["status"] == "failed" and "data" not in step
