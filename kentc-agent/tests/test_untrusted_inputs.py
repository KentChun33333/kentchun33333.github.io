"""Guardrails for agents that read untrusted documents (studio) and for structured step outputs."""

from __future__ import annotations

import json

import pytest

from kentc_agent.adapters.llm import Reply
from kentc_agent.adapters.tools import CORE_TOOLS, ToolError
from kentc_agent.workflow import Runner, WorkflowError, load
from kentc_studio.config import AgentError, load_config

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


# ---------------------------------------------------------------------- studio refuses shell and web access
@pytest.mark.parametrize("step, refused", [
    ("    tools: [read, bash]\n    prompt: hi\n", "offers bash "),
    ("    prompt: hi\n", "offers bash "),                                 # omitted tools = all tools
    ("    web: latest AML news\n    output: research/news.md\n", "has web step\\(s\\) s;"),
])
def test_studio_refuses_workflows_with_shell_or_web_access(tmp_path, step, refused):
    (tmp_path / "wf.yaml").write_text(f"steps:\n  - id: s\n{step}")
    (tmp_path / "safe.yaml").write_text("steps:\n  - id: s\n    tools: [read]\n    prompt: hi\n")
    (tmp_path / "studio.yaml").write_text(
        "agents:\n  doc: {workflow: safe.yaml}\n  context: {workflow: safe.yaml}\n  report: {workflow: wf.yaml}\n")
    with pytest.raises(AgentError, match=f"report: wf.yaml {refused}"):
        load_config(tmp_path / "studio.yaml")


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


def test_wrong_types_and_enum_values_are_sent_back_then_canonicalized(make_ctx, tmp_path):
    bad = {"key_risks": [{"id": "KR-01", "score": "high", "title": "Layering"}],
           "recommendation": {"next_step": "Exit the client"}, "confidence": None}
    state, llm = run_report(make_ctx, tmp_path, [bad, GOOD])
    retry = llm.requests[1]["messages"][-1]["content"]
    assert "'key_risks[0].score' must be a number, got string" in retry
    assert "'recommendation.next_step' must be one of Agree | Further investigation, got \"Exit the client\"" in retry
    assert "missing key 'recommendation.scope'" in retry and "'confidence' must be a number, got null" in retry
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
