from __future__ import annotations

import json
import signal

import pytest

import kentc_agent.agent.executor as executor_module
from kentc_agent.agent import Aborted, Agent
from kentc_agent.context.bigcontext import route_text
from kentc_agent.adapters.llm import Reply
from kentc_agent.adapters.session import Session
from kentc_agent.adapters.tools import CORE_TOOLS, Tool, params

from .conftest import FakeLLM, call


def persisted_results(agent):
    loaded = Session.load(agent.session.path)
    results = [m for m in loaded.messages if m["role"] == "tool"]
    assert results == [m for m in agent.session.messages if m["role"] == "tool"]
    return results


def trace_operation(agent):
    entries = [json.loads(line) for line in agent.trace.path.read_text().splitlines()]
    return next(e for e in reversed(entries) if e["type"] == "operation")


@pytest.mark.parametrize("name,args,bad_key", [
    ("write", {"path": "target.txt", "content": 123}, "content"),
    ("write", {"path": [], "content": "hello"}, "path"),
    ("write", {"path": "target.txt"}, "content"),
    ("read", {"path": "target.txt", "offset": True}, "offset"),
    ("edit", {"path": "target.txt", "old_text": "old", "new_text": "new", "replace_all": 1}, "replace_all"),
    ("bash", {"command": "touch target.txt", "timeout": False}, "timeout"),
])
def test_malformed_arguments_are_correctable_without_invoking_tool(make_ctx, tmp_path, name, args, bad_key):
    calls = [call(name, json.dumps(args))]
    replies = iter([Reply(tool_calls=calls), Reply(content="corrected", finish="stop")])
    agent = Agent(make_ctx(FakeLLM(lambda m, t: next(replies))), tools=[CORE_TOOLS[name]],
                  session=Session(tmp_path / "session.jsonl"))
    assert agent.run("perform the operation") == "corrected"
    result, = persisted_results(agent)
    assert result["content"].startswith("Error:") and bad_key in result["content"]
    assert not (tmp_path / "target.txt").exists()


def test_programming_type_error_propagates_but_resolves_every_call(make_ctx, tmp_path):
    def broken(ctx, args):
        raise TypeError("implementation bug")

    calls = [call("broken", "{}", "first"), call("broken", "{}", "second")]
    agent = Agent(make_ctx(FakeLLM(lambda m, t: Reply(tool_calls=calls))),
                  tools=[Tool("broken", "", params([]), broken)], session=Session(tmp_path / "session.jsonl"))
    with pytest.raises(TypeError, match="implementation bug"):
        agent.run("run the tool")
    results = persisted_results(agent)
    assert [r["tool_call_id"] for r in results] == ["first", "second"]
    assert all("implementation bug" in r["content"] for r in results)
    record = trace_operation(agent)
    assert record["end"] == "error"
    assert [r["id"] for r in record["output_context"]["tool_results"]] == ["first", "second"]


@pytest.mark.parametrize("stage", ["execution", "routing", "partial_append", "big_result", "turn_end"])
def test_interrupted_turn_resolves_all_calls_once(make_ctx, tmp_path, monkeypatch, stage):
    calls = [call("work", "{}", cid) for cid in ("first", "second", "third")]
    executed = []

    def work(ctx, args):
        cid = calls[len(executed)]["id"]
        executed.append(cid)
        if stage == "execution" and cid == "second":
            raise KeyboardInterrupt
        return f"completed {cid}"

    ctx = make_ctx(FakeLLM(lambda m, t: Reply(tool_calls=calls)))
    agent = Agent(ctx, tools=[Tool("work", "", params([]), work)], session=Session(tmp_path / "session.jsonl"))

    if stage == "routing":
        def interrupted_route(ctx, results):
            results[0].text = route_text(ctx, results[0].text, "work", {})
            raise KeyboardInterrupt
        monkeypatch.setattr(executor_module, "route_turn", interrupted_route)
    elif stage == "partial_append":
        original = agent.session.append
        def interrupted_append(message, usage=None):
            original(message, usage)
            if message.get("tool_call_id") == "first":
                raise KeyboardInterrupt
        monkeypatch.setattr(agent.session, "append", interrupted_append)
    elif stage == "big_result":
        original_route = executor_module.route_turn
        def routed(ctx, results):
            results[0].ref.routed = {"by": "rules", "folder": "stored", "tokens": 20}
            original_route(ctx, results)
        monkeypatch.setattr(executor_module, "route_turn", routed)
        def interrupted_event(*args):
            raise KeyboardInterrupt
        monkeypatch.setattr(ctx.events, "big_result", interrupted_event)
    elif stage == "turn_end":
        def interrupted_event(*args):
            raise KeyboardInterrupt
        monkeypatch.setattr(ctx.events, "turn_end", interrupted_event)

    with pytest.raises(Aborted):
        agent.run("perform three operations")
    results = persisted_results(agent)
    assert [r["tool_call_id"] for r in results] == ["first", "second", "third"]
    if stage == "execution":
        assert executed == ["first", "second"]
        assert [r["content"] for r in results] == ["completed first", "Aborted by the user.", "Aborted by the user."]
    elif stage == "turn_end":
        assert executed == []
        assert all(r["content"] == "Aborted by the user." for r in results)
    elif stage != "routing":
        assert [r["content"] for r in results] == [f"completed {cid}" for cid in ("first", "second", "third")]
    record = trace_operation(agent)
    assert record["end"] == "aborted"
    assert [r["id"] for r in record["output_context"]["tool_results"]] == ["first", "second", "third"]
    assert ctx.operation is None


def test_ctrl_c_between_memory_append_and_disk_write_is_deferred(make_ctx, tmp_path, monkeypatch):
    calls = [call("work", "{}", cid) for cid in ("first", "second")]
    agent = Agent(make_ctx(FakeLLM(lambda m, t: Reply(tool_calls=calls))),
                  tools=[Tool("work", "", params([]), lambda ctx, args: "completed")],
                  session=Session(tmp_path / "session.jsonl"))
    original = agent.session._write
    interrupted = False
    def interrupt_write(entry):
        nonlocal interrupted
        if entry.get("message", {}).get("tool_call_id") == "first" and not interrupted:
            interrupted = True
            signal.raise_signal(signal.SIGINT)
        original(entry)
    monkeypatch.setattr(agent.session, "_write", interrupt_write)
    with pytest.raises(Aborted):
        agent.run("perform two operations")
    assert [r["tool_call_id"] for r in persisted_results(agent)] == ["first", "second"]
    record = trace_operation(agent)
    assert record["end"] == "aborted"
    assert [r["id"] for r in record["output_context"]["tool_results"]] == ["first", "second"]


def test_reused_call_ids_in_later_turn_still_receive_their_own_result(make_ctx, tmp_path):
    replies = iter([Reply(tool_calls=[call("work", "{}")]), Reply(tool_calls=[call("work", "{}")]),
                    Reply(content="done", finish="stop")])
    values = iter(["first result", "second result"])
    agent = Agent(make_ctx(FakeLLM(lambda m, t: next(replies))),
                  tools=[Tool("work", "", params([]), lambda ctx, args: next(values))],
                  session=Session(tmp_path / "session.jsonl"))
    assert agent.run("perform two operations") == "done"
    assert [r["content"] for r in persisted_results(agent)] == ["first result", "second result"]


def test_compaction_before_partial_settlement_does_not_duplicate_results(make_ctx, tmp_path, monkeypatch):
    calls = [call("work", "{}", cid) for cid in ("first", "second")]
    session = Session(tmp_path / "session.jsonl")
    for i in range(6):
        session.append({"role": "user", "content": f"old question {i}"})
        session.append({"role": "assistant", "content": f"old answer {i}"})
    agent = Agent(make_ctx(FakeLLM(lambda m, t: Reply(tool_calls=calls))),
                  tools=[Tool("work", "", params([]), lambda ctx, args: "completed")], session=session)
    original_call = agent._call

    def compact_then_call():
        session.compact("earlier conversation", len(session.messages) - 1, tokens_before=1000)
        return original_call()

    monkeypatch.setattr(agent, "_call", compact_then_call)
    original_append = session.append

    def interrupt_after_append(message, usage=None):
        original_append(message, usage)
        if message.get("tool_call_id") == "first":
            raise KeyboardInterrupt

    monkeypatch.setattr(session, "append", interrupt_after_append)
    with pytest.raises(Aborted):
        agent.run("perform two operations after compaction")
    results = persisted_results(agent)
    assert [r["tool_call_id"] for r in results] == ["first", "second"]
    assert [r["content"] for r in results] == ["completed", "completed"]
    record = trace_operation(agent)
    assert record["end"] == "aborted"
    assert [r["id"] for r in record["output_context"]["tool_results"]] == ["first", "second"]
