from __future__ import annotations

import json

import pytest

from kentc_agent import cli
from kentc_agent.adapters.llm import Reply
from kentc_agent.adapters.session import Session
from kentc_agent.adapters.tools import ToolError
from kentc_agent.context.compaction import SYSTEM
from kentc_agent.workflow import Runner, load

from .conftest import FakeLLM, call


def test_task_memory_survives_two_compactions_and_resume(make_ctx, tmp_path):
    original = "  引用原文，不可改寫。  "
    args = cli.parser().parse_args([])
    path = tmp_path / "session.jsonl"
    source = tmp_path / "checks.txt"
    source.write_text("Check output\nAll checks passed\n3 cases verified\n", encoding="utf-8")
    evidence = {"action": "evidence", "path": "checks.txt", "line": 2, "quote": "checks passed\n3 cases"}
    milestone = {"action": "milestone", "id": "check", "criterion": "All three checks pass",
                 "status": "in_progress"}

    def respond(messages, tools):
        if messages[0]["content"] == SYSTEM:
            return Reply(content="## Goal\nContinue the checks.", finish="stop")
        assert original in "\n".join(str(msg["content"]) for msg in messages)
        last = messages[-1]
        if last["content"] == "Run the checks":
            return Reply(tool_calls=[call("task_state", json.dumps(milestone), "start")])
        if last.get("tool_call_id") == "start":
            return Reply(tool_calls=[call("task_state", json.dumps(evidence), "capture")])
        if last.get("tool_call_id") == "capture":
            completion = {**milestone, "status": "complete", "evidence_ids": [json.loads(last["content"])["id"]]}
            return Reply(tool_calls=[call("task_state", json.dumps(completion), "finish")])
        return Reply(content="Checks complete", finish="stop")

    llm = FakeLLM(respond, window=8192)
    ctx = make_ctx(llm, keep_recent_tokens=100)
    session = Session(path)
    session.set_requirement(original)
    agent = cli.make_agent(args, ctx, session)
    assert agent.run("Run the checks") == "Checks complete"
    assert agent.compact(force=True)
    assert agent.run("Continue") == "Checks complete"
    assert agent.compact(force=True)
    source.write_text("Changed since verification", encoding="utf-8")

    loaded = Session.load(path)
    resumed = cli.make_agent(args, ctx, loaded)
    assert loaded.compactions == 2
    assert loaded.requirements == [original]
    state, = json.loads(resumed.tools["task_state"].run(ctx, {"action": "show"}))
    assert state["status"] == "complete"
    record, = [entry for entry in resumed.memory.records() if entry["id"] in state["evidence_ids"]]
    assert record["source"] == "checks.txt:2-3"
    assert (tmp_path / record["path"]).read_text(encoding="utf-8") == evidence["quote"]
    assert resumed.run("Resume") == "Checks complete"
    assert "Saved milestones:" in llm.requests[-1]["messages"][1]["content"]
    loaded.set_requirement(original, active=False)
    assert Session.load(path).requirements == []


def test_milestone_completion_rejects_missing_or_unverified_evidence(make_ctx, tmp_path):
    ctx = make_ctx(FakeLLM(lambda *_: Reply()))
    agent = cli.make_agent(cli.parser().parse_args([]), ctx, Session())
    tool = agent.tools["task_state"]
    milestone = {"action": "milestone", "id": "check", "criterion": "Checks pass", "status": "pending"}
    tool.run(ctx, milestone)
    (tmp_path / "checks.txt").write_text("Check failed\nAll checks passed\n", encoding="utf-8")
    with pytest.raises(ToolError, match="quote does not match"):
        tool.run(ctx, {"action": "evidence", "path": "checks.txt", "line": 1, "quote": "All checks passed"})
    with pytest.raises(ToolError, match="completion requires"):
        tool.run(ctx, {**milestone, "status": "complete"})
    with pytest.raises(ToolError, match="unknown evidence in this session"):
        tool.run(ctx, {**milestone, "status": "complete", "evidence_ids": ["evidence-" + "0" * 16]})
    assert json.loads(tool.run(ctx, {"action": "show", "id": "check"}))["status"] == "pending"
    assert agent.memory.records() == []


def test_workflow_reports_authoritative_progress_with_existing_tool_allowlist(make_ctx, tmp_path):
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text("tools: [read]\nsteps:\n  - id: first\n    prompt: Check\n"
                        "  - id: second\n    prompt: Verify\n", encoding="utf-8")
    llm = FakeLLM(lambda *_: Reply(content="done", finish="stop"), window=8192)
    run_dir = tmp_path / "run"
    state = Runner(load(workflow), make_ctx(llm), {}, run_dir).run()
    assert [step["status"] for step in state["steps"].values()] == ["done", "done"]
    second = llm.requests[-1]
    assert [tool["function"]["name"] for tool in second["tools"]] == ["read"]
    assert "Workflow step 2/2: second (running). Completed=1; skipped=0." in second["messages"][1]["content"]
    assert "Workflow state: run/state.json." in second["messages"][1]["content"]
