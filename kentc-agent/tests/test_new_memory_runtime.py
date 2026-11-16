from __future__ import annotations

import json
from pathlib import Path

import pytest

from kentc_agent.adapters.llm import ContextOverflow, IncompleteReply, ModelInfo, Reply
from kentc_agent.adapters.session import Session
from kentc_agent.adapters.tools import CORE_TOOLS, ToolContext
from kentc_agent.agent import Agent
from kentc_agent.config import Settings
from kentc_agent.context.compaction import CompactionResult
from kentc_agent.ports import Events

from .conftest import call


class ScriptedLLM:
    def __init__(self, *replies: Reply | Exception):
        self.replies = iter(replies)
        self.requests = []

    def info(self, *, refresh=False):
        return ModelInfo("runtime-regression", 65536, False)

    def chat(self, messages, *, tools=None, max_tokens, effort=None, on_delta=None):
        self.requests.append({"messages": messages, "tools": tools, "max_tokens": max_tokens})
        reply = next(self.replies)
        if isinstance(reply, Exception):
            raise reply
        return reply


def context(path: Path, llm: ScriptedLLM, **settings) -> ToolContext:
    return ToolContext(path, Settings(**settings), llm, Events())


def tool_reply(name: str, arguments: dict, cid: str = "call") -> Reply:
    return Reply(tool_calls=[call(name, json.dumps(arguments), cid)], finish="tool_calls")


def test_tool_allowlist_denies_removed_memory_tools_and_can_be_narrowed(tmp_path):
    llm = ScriptedLLM(
        tool_reply("context_search", {"query": "old evidence"}),
        Reply(content="No memory tool is available", finish="stop"),
        tool_reply("write", {"path": "result.txt", "content": "done"}),
        Reply(content="Saved", finish="stop"),
    )
    with Agent(context(tmp_path, llm), tools=[CORE_TOOLS["read"]]) as agent:
        assert agent.run("Find the evidence") == "No memory tool is available"
        denied = [message["content"] for message in agent.session.messages if message["role"] == "tool"]
        assert "unknown tool 'context_search'" in denied[0]
        agent.set_tools([CORE_TOOLS["write"]])
        assert agent.run("Save the result") == "Saved"
    assert (tmp_path / "result.txt").read_text() == "done"
    assert [[schema["function"]["name"] for schema in request["tools"]] for request in llm.requests] == [
        ["read"], ["read"], ["write"], ["write"]]


def test_ordinary_file_tools_and_shell_results_reach_the_next_turn(tmp_path):
    llm = ScriptedLLM(
        tool_reply("write", {"path": "notes.txt", "content": "old value"}, "write"),
        tool_reply("edit", {"path": "notes.txt", "old_text": "old", "new_text": "new"}, "edit"),
        tool_reply("read", {"path": "notes.txt"}, "read"),
        tool_reply("bash", {"command": "cat notes.txt; exit 3"}, "shell"),
        Reply(content="Updated to new value; command exited 3", finish="stop"),
    )
    with Agent(context(tmp_path, llm), tools=list(CORE_TOOLS.values())) as agent:
        assert agent.run("Update and inspect the notes") == "Updated to new value; command exited 3"
    assert (tmp_path / "notes.txt").read_text() == "new value"
    results = {message["tool_call_id"]: message["content"]
               for message in llm.requests[-1]["messages"] if message["role"] == "tool"}
    assert results["read"] == "new value"
    assert "new value" in results["shell"] and "exit code 3" in results["shell"]


def test_read_tool_is_still_executed_on_the_final_model_call(tmp_path):
    (tmp_path / "evidence.txt").write_text("actual evidence")
    llm = ScriptedLLM(tool_reply("read", {"path": "evidence.txt"}))
    with Agent(context(tmp_path, llm), tools=[CORE_TOOLS["read"]], max_turns=1) as agent:
        assert "Stopped after 1 model calls" in agent.run("Inspect the file")
        assert agent.session.messages[-1]["content"] == "actual evidence"
        assert agent.stopped == "max_turns"


@pytest.mark.parametrize("content", ["", "  \n\t"])
def test_empty_replies_are_rejected_without_exceeding_the_model_call_budget(tmp_path, content):
    llm = ScriptedLLM(Reply(content=content, finish="stop"), Reply(content=content, finish="stop"))
    path = tmp_path / "session.jsonl"
    with Agent(context(tmp_path, llm, output_retries=5), tools=[], session=Session(path), max_turns=2) as agent:
        with pytest.raises(IncompleteReply, match="model-call budget exhausted"):
            agent.run("Answer the question")
        assert agent.turns == 2
    assert len(llm.requests) == 2
    assert Session.load(path).messages == [{"role": "user", "content": "Answer the question"}]


def test_context_overflow_retry_counts_towards_the_run_budget(tmp_path):
    llm = ScriptedLLM(ContextOverflow("maximum context length is 65536; at most 4000"),
                      Reply(content="Complete answer", finish="stop"))
    with Agent(context(tmp_path, llm), tools=[], max_turns=2) as agent:
        assert agent.run("Answer the question") == "Complete answer"
        assert agent.turns == 2
    assert len(llm.requests) == 2
    assert llm.requests[-1]["max_tokens"] == 3984


def test_context_overflow_never_retries_after_the_last_model_call(tmp_path):
    llm = ScriptedLLM(ContextOverflow("maximum context length is 65536; at most 4000"))
    with Agent(context(tmp_path, llm), tools=[], max_turns=1) as agent:
        with pytest.raises(IncompleteReply, match="model-call budget exhausted: context overflow"):
            agent.run("Answer the question")
    assert len(llm.requests) == 1


def test_standalone_text_tool_call_is_rejected_without_executing_it(tmp_path):
    leaked = '<tool_call>{"name":"write","arguments":{"path":"bad.txt","content":"bad"}}</tool_call>'
    llm = ScriptedLLM(Reply(content=leaked, finish="stop"), Reply(content="No write performed", finish="stop"))
    with Agent(context(tmp_path, llm), tools=[CORE_TOOLS["write"]]) as agent:
        assert agent.run("Explain the tool") == "No write performed"
        assert all(message.get("content") != leaked for message in agent.session.messages)
    assert not (tmp_path / "bad.txt").exists()


def test_protocol_documentation_is_valid_final_prose(tmp_path):
    text = 'The protocol can encode calls as `<tool_call>{"name":"read"}</tool_call>`; use structured calls instead.'
    llm = ScriptedLLM(Reply(content=text, finish="stop"))
    with Agent(context(tmp_path, llm), tools=[]) as agent:
        assert agent.run("Explain the protocol") == text


def test_parser_worker_never_archives_its_evidence(tmp_path):
    llm = ScriptedLLM(Reply(content="Document fact", finish="stop"))
    with Agent(context(tmp_path, llm), tools=[], system="Read this document only", max_turns=1) as agent:
        assert not agent.compact(force=True)
        assert agent.run("Source page: document evidence") == "Document fact"
    assert not (tmp_path / ".kentc-agent" / "memory").exists()


def test_topic_details_are_recalled_with_an_ordinary_read_not_automatic_reinjection(tmp_path):
    session = Session(tmp_path / "session.jsonl")
    llm = ScriptedLLM()
    with Agent(context(tmp_path, llm), tools=[CORE_TOOLS["read"]], session=session) as agent:
        session.append({"role": "user", "content": "The launch password is glacier-731."})
        session.append({"role": "assistant", "content": "Recorded the launch details."})
        session.compact(CompactionResult("Launch details are archived.",
                                         {"launch": "# Launch\n\nThe launch password is glacier-731.\n"}), 2, 100)
        checkpoint = session.context()[0]["content"]
        index = Path(checkpoint.split("Local topic index (use ordinary read/bash to inspect): ", 1)[1].splitlines()[0])
        topic = Path(next(line.removeprefix("- launch: ") for line in index.read_text().splitlines()
                          if line.startswith("- launch: ")))
        llm.replies = iter([tool_reply("read", {"path": str(index)}, "index"),
                            tool_reply("read", {"path": str(topic)}, "topic"),
                            Reply(content="The launch password is glacier-731.", finish="stop")])
        assert agent.run("What was the launch password?") == "The launch password is glacier-731."
    initial = json.dumps(llm.requests[0]["messages"])
    assert str(index) in initial and "glacier-731" not in initial
    assert str(topic) in llm.requests[1]["messages"][-2]["content"]   # the budget notice follows the tool result
    assert "glacier-731" in llm.requests[2]["messages"][-2]["content"]


def test_budget_notice_counts_down_to_the_last_call_and_is_never_stored(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    llm = ScriptedLLM(*(tool_reply("read", {"path": "a.txt"}, f"c{i}") for i in range(3)))
    with Agent(context(tmp_path, llm), tools=[CORE_TOOLS["read"]], max_turns=3) as agent:
        assert "Stopped after 3 model calls" in agent.run("read a.txt")
        notices = [r["messages"][-1]["content"] for r in llm.requests]
        assert ["2 left" in notices[0], "1 left" in notices[1], "the last one" in notices[2]] == [True, True, True]
        assert not any("Model-call budget" in str(m.get("content")) for m in agent.session.messages)


def test_identical_repeat_points_to_the_live_result_until_it_changes_or_leaves_context(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    llm = ScriptedLLM(tool_reply("read", {"path": "a.txt"}, "c1"), tool_reply("read", {"path": "a.txt"}, "c2"),
                      tool_reply("read", {"path": "a.txt"}, "c3"), Reply(content="done", finish="stop"))
    statuses: list[str] = []
    with Agent(context(tmp_path, llm), tools=[CORE_TOOLS["read"]]) as agent:
        agent.ctx.events.status = lambda name, text: statuses.append(text)
        original_execute = agent._execute

        def execute(call):                       # the file changes between the 2nd and 3rd call
            if call["id"] == "c3":
                (tmp_path / "a.txt").write_text("changed")
            return original_execute(call)
        agent._execute = execute
        agent.run("read a.txt")
        results = {m["tool_call_id"]: m["content"] for m in agent.session.messages if m["role"] == "tool"}
    assert results["c1"] == "hello"
    assert results["c2"].startswith("[Repeat 2") and "c1" in results["c2"]
    assert results["c3"] == "changed"
    assert sum("repeated read call" in text for text in statuses) == 1

    llm = ScriptedLLM(tool_reply("read", {"path": "a.txt"}, "d1"), tool_reply("read", {"path": "a.txt"}, "d2"),
                      Reply(content="done", finish="stop"))
    with Agent(context(tmp_path, llm), tools=[CORE_TOOLS["read"]]) as agent:
        original_settle = agent._settle

        def settle(results, *, start):           # the first result leaves the live context (as after compaction)
            original_settle(results, start=start)
            if results[0].call_id == "d1":
                agent.session.messages = [m for m in agent.session.messages if m.get("tool_call_id") != "d1"]
        agent._settle = settle
        agent.run("read a.txt")
        assert [m["content"] for m in agent.session.messages if m.get("tool_call_id") == "d2"] == ["changed"]


def test_reply_cut_off_inside_a_tool_call_is_retried_with_chunked_write_guidance(tmp_path):
    llm = ScriptedLLM(Reply(tool_calls=[call("write", '{"path": "r.html", "content": "<html>')], finish="length"),
                      Reply(content="written", finish="stop"))
    with Agent(context(tmp_path, llm), tools=[CORE_TOOLS["write"]]) as agent:
        assert agent.run("write the report") == "written"
    correction = llm.requests[1]["messages"][-1]["content"]
    assert "cut off inside a tool call" in correction and "in parts" in correction
    assert not (tmp_path / "r.html").exists()


def test_long_search_output_keeps_the_first_matches_and_counts_by_file(tmp_path):
    from kentc_agent.adapters.tools import run_shell
    (tmp_path / "a.txt").write_text("".join(f"hit {i}\n" for i in range(30)))
    (tmp_path / "b.txt").write_text("hit only\n")
    ctx = context(tmp_path, ScriptedLLM(), tool_output_max_lines=5)
    search = run_shell(ctx, "grep -n hit a.txt b.txt")
    assert search.output.startswith("[Search output truncated: 31 matching lines in 2 files; showing the first 5")
    assert "a.txt (30), b.txt (1)" in search.output and "a.txt:1:hit 0" in search.output
    other = run_shell(ctx, "seq 1 20")
    assert other.output.startswith("[Output truncated: 20 lines; showing the last 5") and other.output.endswith("20")


def test_failed_topic_compression_retains_all_live_evidence(tmp_path, monkeypatch):
    llm = ScriptedLLM()
    with Agent(context(tmp_path, llm), tools=[]) as agent:
        agent.session.append({"role": "user", "content": "Evidence: " + "important " * 2000})
        agent.session.append({"role": "assistant", "content": "Work remains."})
        original = json.loads(json.dumps(agent.session.messages))

        def failed(*args, **kwargs):
            raise OSError("disk unavailable")

        monkeypatch.setattr("kentc_agent.agent.budget.summarize", failed)
        agent._try_compact(force=True)
        assert agent.session.messages == original
        assert agent.session.summary is None


def test_large_file_result_keeps_a_readable_observation_snapshot(tmp_path):
    text = "\n".join(f"record {index}: original evidence" for index in range(500))
    source = tmp_path / "evidence.txt"
    source.write_text(text)
    llm = ScriptedLLM(tool_reply("read", {"path": "evidence.txt"}, "routed"),
                      Reply(content="The evidence is stored for inspection", finish="stop"))
    with Agent(context(tmp_path, llm, big_result_tokens=300, big_digest_tokens=150),
               tools=[CORE_TOOLS["read"]]) as agent:
        assert agent.run("Inspect the evidence") == "The evidence is stored for inspection"
        snapshot = (tmp_path / ".kentc-agent" / "operations" / agent.session.id / "1" / "routed" / "full.md")
        assert snapshot.read_text() == text
        source.write_text("Changed after observation")
        result = CORE_TOOLS["read"].run(agent.ctx, {"path": str(snapshot), "offset": 1, "limit": 2})
        assert result.startswith("record 0: original evidence\nrecord 1: original evidence")
        shown = llm.requests[-1]["messages"][-2]["content"]
        assert "full.md" in shown and shown != text


def sent_arguments(request: dict, call_id: str) -> str:
    return next(c["function"]["arguments"] for m in request["messages"] for c in m.get("tool_calls") or []
                if c["id"] == call_id)


def test_written_content_leaves_the_context_but_the_journal_keeps_it(tmp_path):
    body = "\n".join(f"section {i}: " + "evidence " * 8 for i in range(400))
    llm = ScriptedLLM(tool_reply("write", {"path": "report.md", "content": body}, "ok"),
                      tool_reply("write", {"path": "../outside.md", "content": body}, "refused"),
                      Reply(content="written", finish="stop"))
    path = tmp_path / "session.jsonl"
    with Agent(context(tmp_path, llm), tools=[CORE_TOOLS["write"]], session=Session(path)) as agent:
        assert agent.run("write the report") == "written"
    assert (tmp_path / "report.md").read_text() == body

    shown = json.loads(sent_arguments(llm.requests[1], "ok"))
    assert shown["path"] == "report.md" and len(shown["content"]) < 1500
    assert "omitted from the context" in shown["content"] and "session.jsonl" in shown["content"]
    assert shown["content"].endswith(body[-400:])           # where a next part continues
    assert json.loads(sent_arguments(llm.requests[2], "refused"))["content"] == body   # failed: left to correct

    rows = [json.loads(line) for line in path.read_text().splitlines()]
    original = next(r for r in rows if r["type"] == "message" and r["message"].get("tool_calls")
                    and r["message"]["tool_calls"][0]["id"] == "ok")
    assert json.loads(original["message"]["tool_calls"][0]["function"]["arguments"])["content"] == body
    resumed = Session.load(path)
    replayed = next(c for m in resumed.messages for c in m.get("tool_calls") or [] if c["id"] == "ok")
    assert json.loads(replayed["function"]["arguments"]) == shown


def test_only_a_successful_long_command_is_shortened(tmp_path):
    heredoc = "cat > notes.txt <<'EOF'\n" + "\n".join(f"note {i}: " + "detail " * 8 for i in range(300)) + "\nEOF\n"
    llm = ScriptedLLM(Reply(tool_calls=[call("bash", json.dumps({"command": heredoc}), "done"),
                                        call("bash", json.dumps({"command": heredoc + "exit 3"}), "failed")],
                            finish="tool_calls"),
                      Reply(content="checked", finish="stop"))
    with Agent(context(tmp_path, llm), tools=[CORE_TOOLS["bash"]]) as agent:
        assert agent.run("save the notes") == "checked"
    assert "omitted from the context" in json.loads(sent_arguments(llm.requests[1], "done"))["command"]
    assert json.loads(sent_arguments(llm.requests[1], "failed"))["command"] == heredoc + "exit 3"
