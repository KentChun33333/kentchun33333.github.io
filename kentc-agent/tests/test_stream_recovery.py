from __future__ import annotations

import json
import re

import pytest

from kentc_agent.adapters.llm import IncompleteReply, Reply, Usage
from kentc_agent.adapters.session import Session
from kentc_agent.adapters.tools import CORE_TOOLS
from kentc_agent.agent import Agent
from kentc_agent.workflow import Runner, load, parse_json_object

from .conftest import FakeLLM, call


def test_truncated_tool_turn_never_executes_or_enters_session(make_ctx, tmp_path):
    replies = iter([
        Reply(content="UNTRUSTED_PARTIAL", finish="length", tool_calls=[
            call("write", '{"path":"bad.txt","content":"bad"}', "rejected")]),
        Reply(tool_calls=[call("write", '{"path":"good.txt","content":"verified"}', "accepted")],
              finish="tool_calls"),
        Reply(content="Done", finish="stop"),
    ])
    llm = FakeLLM(lambda m, t: next(replies), window=65536)
    agent = Agent(make_ctx(llm), tools=[CORE_TOOLS["write"]], session=Session(tmp_path / "session.jsonl"))
    assert agent.run("Write the verified result") == "Done"
    assert not (tmp_path / "bad.txt").exists()
    assert (tmp_path / "good.txt").read_text() == "verified"
    saved = Session.load(agent.session.path)
    assert "UNTRUSTED_PARTIAL" not in json.dumps(saved.messages)
    assert "bad.txt" not in json.dumps(llm.requests[1:])
    assert [m["tool_call_id"] for m in saved.messages if m["role"] == "tool"] == ["accepted"]


def test_malformed_tool_json_retries_without_executing_partial_call(make_ctx, tmp_path):
    replies = iter([
        Reply(tool_calls=[call("write", '{"path":"bad.txt","content":"unfinished', "bad")],
              finish="tool_calls"),
        Reply(content="No write was required", finish="stop"),
    ])
    llm = FakeLLM(lambda m, t: next(replies), window=65536)
    agent = Agent(make_ctx(llm), tools=[CORE_TOOLS["write"]])
    assert agent.run("Inspect the request") == "No write was required"
    assert not (tmp_path / "bad.txt").exists()
    assert all(m["role"] != "tool" for m in agent.session.messages)
    assert "unfinished" not in json.dumps(llm.requests[1]["messages"])


@pytest.mark.parametrize("output_allowance", [512, 16384])
def test_incomplete_file_edit_resumes_after_saved_sections(make_ctx, tmp_path, output_allowance):
    path = tmp_path / "report.html"
    skeleton = "<main><!--summary--><!--results--></main>"
    first_section = "<section>Summary</section>"
    second_section = "<section>Results</section>"
    replies = iter([
        Reply(tool_calls=[call("write", json.dumps({"path": path.name, "content": skeleton}), "skeleton")]),
        Reply(tool_calls=[call("edit", json.dumps({
            "path": path.name, "old_text": "<!--summary-->", "new_text": first_section,
        }), "summary")]),
        Reply(tool_calls=[call("edit", '{"path":"report.html","old_text":"<!--results-->","new_text":"UNFINISHED',
                               "rejected")], finish="tool_calls", usage=Usage(2048, output_allowance)),
        Reply(tool_calls=[call("edit", '{"path":"report.html","old_text":"<!--results-->","new_text":"UNFINISHED',
                               "rejected-again")], finish="tool_calls", usage=Usage(2048, output_allowance)),
        Reply(tool_calls=[call("edit", json.dumps({
            "path": path.name, "old_text": "<!--results-->", "new_text": second_section,
        }), "results")]),
        Reply(content="Report saved.", finish="stop"),
    ])

    def respond(messages, tools):
        if len(llm.requests) in (4, 5):
            assert path.read_text() == skeleton.replace("<!--summary-->", first_section)
            assert "keep the sections already saved" in messages[-1]["content"]
            assert "one smaller, complete write or edit" in messages[-1]["content"]
            assert "UNFINISHED" not in json.dumps(messages)
        return next(replies)

    llm = FakeLLM(respond, window=65_536)
    agent = Agent(make_ctx(llm, max_output_tokens=output_allowance),
                  tools=[CORE_TOOLS[name] for name in ("read", "write", "edit")])
    assert agent.run("Write a long HTML report") == "Report saved."
    assert path.read_text() == f"<main>{first_section}{second_section}</main>"
    for attempt, request in enumerate(llm.requests):
        hint = request["messages"][1]["content"]
        target = re.search(r"target at most\s+(\d+) estimated tokens", hint)
        divisor = 8 if attempt == 3 else 16 if attempt == 4 else 4
        assert target and int(target[1]) == request["max_tokens"] // divisor
    assert [message["tool_call_id"] for message in agent.session.messages if message["role"] == "tool"] == [
        "skeleton", "summary", "results"
    ]


def test_exhausted_retries_leave_only_original_accepted_context(make_ctx, tmp_path):
    llm = FakeLLM(lambda m, t: Reply(content='{"amount":999', finish="length"), window=65536)
    agent = Agent(make_ctx(llm, output_retries=1), tools=[], session=Session(tmp_path / "session.jsonl"))
    with pytest.raises(IncompleteReply):
        agent.run("Extract the exact amount")
    assert len(llm.requests) == 2
    assert Session.load(agent.session.path).messages == [{"role": "user", "content": "Extract the exact amount"}]


def test_clean_retries_respect_the_run_model_call_budget(make_ctx):
    llm = FakeLLM(lambda m, t: Reply(content='{"amount":999', finish="length"), window=65536)
    agent = Agent(make_ctx(llm, output_retries=5), tools=[], max_turns=2)
    with pytest.raises(IncompleteReply):
        agent.run("Extract the exact amount")
    assert len(llm.requests) == 2
    assert all(m["role"] != "assistant" for m in agent.session.messages)


def test_json_workflow_rejects_truncated_and_schema_invalid_evidence_before_commit(make_ctx, tmp_path):
    path = tmp_path / "review.yaml"
    path.write_text('name: review\ntools: []\nsteps:\n  - id: extract\n    prompt: Extract the amount\n'
                    '    format: json\n    schema: {amount: number}\n')
    replies = iter([
        Reply(content='{"amount":999', finish="stop"),
        Reply(content='{"amount":"UNVERIFIED"}', finish="stop"),
        Reply(content='{"amount":125}', finish="stop"),
    ])
    llm = FakeLLM(lambda m, t: next(replies), window=65536)
    workflow = load(path)
    runner = Runner(workflow, make_ctx(llm), {}, tmp_path / "run")
    output, data = runner._prompt(workflow.steps[0], 1, 1)
    assert data == {"amount": 125}
    assert json.loads(output) == data
    saved = Session.load(runner.agent.session.path)
    assert [m["content"] for m in saved.messages if m["role"] == "assistant"] == ['{"amount":125}']
    assert '"amount":999' not in json.dumps(llm.requests[1:])
    assert '"UNVERIFIED"' not in json.dumps(llm.requests[2:])


@pytest.mark.parametrize("text", [
    '{"amount":125', '{"amount":125,}', '{"amount":125,"amount":999}',
    '{"amount":NaN}', '{"amount":Infinity}', 'Explanation: {"amount":125}',
])
def test_json_parser_never_repairs_or_overwrites_evidence(text):
    with pytest.raises(ValueError):
        parse_json_object(text)
