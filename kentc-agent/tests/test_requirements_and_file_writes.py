"""Pinned requirements, incremental file writes and the request preflight (ported from the codex runtime)."""

from __future__ import annotations

import json
import re

import pytest

from kentc_agent.adapters.llm import ContextOverflow, Reply, Usage
from kentc_agent.adapters.session import Session
from kentc_agent.adapters.tools import CORE_TOOLS
from kentc_agent.agent import Agent

from .conftest import FakeLLM, call


def test_pinned_requirement_survives_compactions_and_resume_verbatim(make_ctx, tmp_path):
    original = "  引用原文，不可改寫。  "
    path = tmp_path / "session.jsonl"

    def respond(messages, tools):
        if "<historical-data>" in str(messages[-1]["content"]):   # summarizer: pins are kept outside its output
            return Reply(content=json.dumps({"checkpoint": "## Goal\nContinue.", "topics": {}}), finish="stop")
        assert any(original in str(m["content"]) for m in messages)   # every agent request
        return Reply(content="done " + "x" * 400, finish="stop")

    ctx = make_ctx(FakeLLM(respond, window=8192), keep_recent_tokens=100)
    session = Session(path)
    session.set_requirement(original)
    agent = Agent(ctx, tools=[], session=session)
    for prompt in ("first", "second"):
        agent.run(prompt + " " + "q" * 400)
        assert agent.compact(force=True)
    agent.close()

    loaded = Session.load(path)
    assert loaded.requirements == [original] and loaded.summary == "## Goal\nContinue."
    Agent(ctx, tools=[], session=loaded).run("resume")
    loaded.set_requirement(original, active=False)
    assert Session.load(path).requirements == []
    with pytest.raises(ValueError, match="limited"):
        Session().set_requirement("x" * 4001)


@pytest.mark.parametrize("output_allowance", [512, 16384])
def test_cut_off_file_edit_retries_smaller_and_keeps_saved_sections(make_ctx, tmp_path, output_allowance):
    path = tmp_path / "report.html"
    skeleton = "<main><!--summary--><!--results--></main>"
    first, second = "<section>Summary</section>", "<section>Results</section>"
    truncated = '{"path":"report.html","old_text":"<!--results-->","new_text":"UNFINISHED'
    replies = iter([
        Reply(tool_calls=[call("write", json.dumps({"path": path.name, "content": skeleton}), "skeleton")]),
        Reply(tool_calls=[call("edit", json.dumps({"path": path.name, "old_text": "<!--summary-->",
                                                   "new_text": first}), "summary")]),
        Reply(tool_calls=[call("edit", truncated, "rejected")], finish="tool_calls", usage=Usage(2048, 64)),
        Reply(tool_calls=[call("edit", truncated, "rejected-again")], finish="length", usage=Usage(2048, 64)),
        Reply(tool_calls=[call("edit", json.dumps({"path": path.name, "old_text": "<!--results-->",
                                                   "new_text": second}), "results")]),
        Reply(content="Report saved.", finish="stop"),
    ])

    def respond(messages, tools):
        if len(llm.requests) in (4, 5):                      # the clean retries after each rejected edit
            assert path.read_text() == skeleton.replace("<!--summary-->", first)
            assert "keep the sections already saved" in messages[-1]["content"]
            assert "UNFINISHED" not in json.dumps(messages)
        return next(replies)

    llm = FakeLLM(respond, window=65_536)
    agent = Agent(make_ctx(llm, max_output_tokens=output_allowance),
                  tools=[CORE_TOOLS[name] for name in ("read", "write", "edit")])
    assert agent.run("Write a long HTML report") == "Report saved."
    assert path.read_text() == f"<main>{first}{second}</main>"
    for attempt, request in enumerate(llm.requests):
        target = re.search(r"target at most (\d+) estimated tokens", request["messages"][-1]["content"])
        divisor = {3: 8, 4: 16}.get(attempt, 4)              # halves per cut-off write; a new turn starts over
        assert target and int(target[1]) == request["max_tokens"] // divisor
    assert [m["tool_call_id"] for m in agent.session.messages if m["role"] == "tool"] == \
        ["skeleton", "summary", "results"]


def test_file_hint_only_with_the_core_write_and_edit_tools(make_ctx):
    llm = FakeLLM(lambda m, t: Reply(content="ok", finish="stop"), window=65_536)
    Agent(make_ctx(llm), tools=[CORE_TOOLS["read"], CORE_TOOLS["write"]]).run("answer")
    assert "target at most" not in json.dumps(llm.requests[0]["messages"])


def test_request_without_reply_room_is_rejected_before_the_network_call(make_ctx):
    llm = FakeLLM(lambda _m, _t: pytest.fail("oversized request reached the model"))
    agent = Agent(make_ctx(llm), tools=[], system="fixed instructions " * 3000)
    with pytest.raises(ContextOverflow, match="too little reply room"):
        agent.run("Go")
    assert llm.requests == []
