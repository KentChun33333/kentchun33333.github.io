from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor

import pytest

from kentc_agent.agent import Agent
from kentc_agent.adapters.llm import ContextOverflow, Reply
from kentc_agent.adapters.session import Session, estimate_tokens
from kentc_agent.adapters.tools import CORE_TOOLS, Tool, ToolError, params
from kentc_agent.context.bigcontext import limits
from kentc_agent.context.memory import WorkspaceMemory
from kentc_agent.context.compaction import SYSTEM, summarize

from .conftest import FakeLLM, call


def assert_requests_fit(llm):
    for request in llm.requests:
        prompt = sum(estimate_tokens(message) for message in request["messages"])
        prompt += estimate_tokens({"content": json.dumps(request["tools"] or [])})
        assert prompt + request["max_tokens"] <= llm.info().context_window


def test_large_file_is_indexed_and_its_snapshot_survives_source_changes(make_ctx, tmp_path):
    original = "Evidence\n" * 10_000 + "unique value 91827\n"
    source = tmp_path / "evidence.txt"
    source.write_text(original)
    replies = iter([Reply(tool_calls=[call("read", '{"path":"evidence.txt"}')]), Reply(content="done")])
    llm = FakeLLM(lambda _m, _t: next(replies))
    agent = Agent(make_ctx(llm), tools=[CORE_TOOLS["read"]], session=Session(tmp_path / "session.jsonl"))
    assert agent.run("Inspect evidence.txt") == "done"
    entry, = agent.memory.records()
    assert entry["kind"] == "result"
    assert entry["id"] in agent.memory.index.read_text()
    assert entry["id"] in llm.requests[1]["messages"][1]["content"]
    assert original not in json.dumps(llm.requests)
    source.write_text("updated source")
    assert (tmp_path / entry["path"]).read_text() == original
    # Resume from the ordinary session log and retrieve the exact tail through the ordinary read tool.
    loaded = Session.load(agent.session.path)
    resumed = Agent(agent.ctx, tools=[CORE_TOOLS["read"]], session=loaded)
    assert resumed.memory.records() == agent.memory.records()
    tail = CORE_TOOLS["read"].run(agent.ctx, {"path": entry["path"], "offset": 10_001, "limit": 1})
    assert "unique value 91827" in tail
    assert_requests_fit(llm)


def test_oversized_errors_are_stored_and_remain_errors(make_ctx, tmp_path):
    message = "backend failure\n" * 10_000

    def fail(_ctx, _args):
        raise ToolError(message)

    replies = iter([Reply(tool_calls=[call("fail", "{}")]), Reply(content="handled")])
    llm = FakeLLM(lambda _m, _t: next(replies))
    agent = Agent(make_ctx(llm), tools=[Tool("fail", "", params([]), fail)])
    assert agent.run("Check backend") == "handled"
    result = next(m for m in agent.session.messages if m["role"] == "tool")
    assert result["content"].startswith("Error")
    entry, = agent.memory.records()
    assert (tmp_path / entry["path"]).read_text() == "Error: " + message
    assert_requests_fit(llm)


def test_large_user_input_is_retrievable_and_runtime_status_does_not_accumulate(make_ctx, tmp_path):
    text = "Review the following evidence.\n" + "record 17\n" * 20_000
    llm = FakeLLM(lambda _m, _t: Reply(content="done"))
    agent = Agent(make_ctx(llm), tools=[CORE_TOOLS["read"]])
    agent.run(text)
    agent.run("Continue")
    entry, = agent.memory.records()
    assert entry["kind"] == "input"
    assert (tmp_path / entry["path"]).read_text() == text
    for request in llm.requests:
        assert sum(m["content"].startswith("[Runtime context status") for m in request["messages"]
                   if isinstance(m.get("content"), str)) == 1
    assert all("[Runtime context status" not in str(m["content"]) for m in agent.session.messages)
    assert_requests_fit(llm)


def test_compaction_archives_complete_history_and_restores_its_count(make_ctx, tmp_path):
    llm = FakeLLM(lambda _m, _t: Reply(content="## Goal\nContinue checking evidence", finish="stop"), window=8192)
    agent = Agent(make_ctx(llm, keep_recent_tokens=100), tools=[], session=Session(tmp_path / "session.jsonl"))
    original = "old evidence\n" * 500 + "fact beyond the summarizer preview"
    agent.session.append({"role": "user", "content": "Check all facts"})
    agent.session.append({"role": "assistant", "content": "", "tool_calls": [call("read", "{}", "old")]})
    agent.session.append({"role": "tool", "tool_call_id": "old", "content": original})
    agent.session.append({"role": "assistant", "content": "checked"})
    agent.session.append({"role": "user", "content": "Continue"})
    assert agent.compact(force=True)
    entry, = agent.memory.records()
    saved = json.loads((tmp_path / entry["path"]).read_text())
    assert any(m.get("content") == original for m in saved["messages"])
    loaded = Session.load(agent.session.path)
    assert loaded.compactions == 1
    assert loaded.context() == agent.session.context()
    assert_requests_fit(llm)


def test_failed_compaction_spills_results_without_losing_reload_state(make_ctx, tmp_path):
    def respond(messages, _tools):
        if "context checkpoint" in str(messages[-1]["content"]):
            return Reply(content="", finish="length")
        return Reply(content="recovered", finish="stop")

    llm = FakeLLM(respond, window=8192)
    agent = Agent(make_ctx(llm, keep_recent_tokens=1000), tools=[CORE_TOOLS["read"]],
                  session=Session(tmp_path / "session.jsonl"))
    original = "valuable result\n" * 2000
    agent.session.append({"role": "user", "content": "Inspect source"})
    agent.session.append({"role": "assistant", "content": "", "tool_calls": [call("read", "{}", "old")]})
    agent.session.append({"role": "tool", "tool_call_id": "old", "content": original})
    assert agent.run("Continue") == "recovered"
    stored = [r for r in agent.memory.records() if r["kind"] == "result"]
    assert any((tmp_path / entry["path"]).read_text() == original for entry in stored)
    assert Session.load(agent.session.path).context() == agent.session.context()
    assert_requests_fit(llm)


def test_index_records_are_retry_safe_and_sessions_are_isolated(tmp_path):
    memory = WorkspaceMemory(tmp_path, "one")

    def archive(number):
        return memory.archive(f"result {number}", kind="result", tokens=4)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(archive, range(12)))
    memory.refresh()
    assert len(memory.records()) == 12
    first = archive(0)
    assert archive(0) == first
    assert len(memory.records()) == 12
    assert WorkspaceMemory(tmp_path, "two").records() == []
    assert all(record["id"] in memory.index.read_text() for record in memory.records())


def test_impossible_fixed_prompt_is_rejected_before_network_call(make_ctx):
    llm = FakeLLM(lambda _m, _t: pytest.fail("oversized request reached model"))
    agent = Agent(make_ctx(llm), tools=[], system="fixed instructions " * 3000)
    with pytest.raises(ContextOverflow, match="insufficient reply room"):
        agent.run("Go")
    assert llm.requests == []


def test_working_budget_and_tool_limits_follow_available_capacity(make_ctx):
    llm = FakeLLM(lambda _m, _t: Reply(content="done"), window=100_000)
    agent = Agent(make_ctx(llm, context_budget_tokens=8192), tools=[CORE_TOOLS["read"]])
    agent.run("Inspect")
    assert agent.window == 8192
    assert "Window=8192" in llm.requests[0]["messages"][1]["content"]
    before = limits(agent.ctx)
    agent.ctx.available_context_tokens = 128
    after = limits(agent.ctx)
    assert after.result < before.result
    assert after.turn <= 128
    assert after.digest < before.digest
    request, = llm.requests
    size = math.ceil(sum(estimate_tokens(m) for m in request["messages"]) * agent.density)
    assert size + request["max_tokens"] <= 8192


def test_many_large_results_in_one_turn_fit_and_remain_retrievable(make_ctx, tmp_path):
    batch_sent = False
    original = "large result payload\n" * 1000

    def respond(messages, _tools):
        nonlocal batch_sent
        if messages[0]["content"] == SYSTEM:
            return Reply(content="## Goal\nReview the indexed results.\n## Next Steps\nVerify evidence.", finish="stop")
        if not batch_sent:
            batch_sent = True
            return Reply(tool_calls=[call("dump", "{}", f"r{i}") for i in range(30)])
        return Reply(content="done", finish="stop")

    llm = FakeLLM(respond)
    agent = Agent(make_ctx(llm), tools=[Tool("dump", "", params([]), lambda _c, _a: original)])
    assert agent.run("Inspect the results") == "done"
    results = [entry for entry in agent.memory.records() if entry["kind"] == "result"]
    assert len(results) >= 30
    assert sum((tmp_path / entry["path"]).read_text() == original for entry in results) == 30
    assert agent.session.compactions > 0
    assert_requests_fit(llm)


def test_summary_rebudgets_each_fold_for_a_growing_checkpoint():
    llm = FakeLLM(lambda _m, _t: Reply(content="important fact " * 100, finish="stop"))
    summarize(llm, [{"role": "user", "content": "source evidence\n" * 12_000}], "previous facts",
              window=4096, reserve_tokens=1024, max_output_tokens=800, effort="none", density=1.75)
    assert len(llm.requests) > 2
    for request in llm.requests:
        prompt = math.ceil(sum(estimate_tokens(m) for m in request["messages"]) * 1.75)
        assert prompt + request["max_tokens"] <= 4096


def test_character_windows_retrieve_the_middle_of_a_giant_single_line(make_ctx, tmp_path):
    ctx = make_ctx(FakeLLM(lambda _m, _t: pytest.fail("paging does not need a model")))
    ctx.density = 2.0
    ctx.available_context_tokens = 1024
    text = "a" * 50_000 + "重要的值=91827" + "b" * 50_000
    (tmp_path / "minified.json").write_text(text)
    result = CORE_TOOLS["read"].run(ctx, {"path": "minified.json", "start_char": 50_000, "max_chars": 100_000})
    assert result.startswith("重要的值=91827")
    assert "Chars 50000:" in result
    assert math.ceil(len(result) / 4 * ctx.density) <= limits(ctx).result


def test_same_batch_source_edit_does_not_change_the_saved_read_result(make_ctx, tmp_path):
    original = "old value\n" * 50
    (tmp_path / "source.txt").write_text(original)
    replies = iter([Reply(tool_calls=[call("read", '{"path":"source.txt"}', "read-old"),
                                      call("write", '{"path":"source.txt","content":"new value"}', "write-new")]),
                    Reply(content="done")])
    agent = Agent(make_ctx(FakeLLM(lambda _m, _t: next(replies)), big_turn_tokens=100, big_digest_tokens=50),
                  tools=[CORE_TOOLS["read"], CORE_TOOLS["write"]])
    agent.run("Read then update source.txt")
    assert (tmp_path / "source.txt").read_text() == "new value"
    assert any((tmp_path / entry["path"]).read_text() == original for entry in agent.memory.records())


def test_successful_large_write_and_edit_shorten_live_arguments(make_ctx, tmp_path):
    draft = "Original draft paragraph\n" * 160
    revised = "Revised draft paragraph\n" * 160
    failed = "Failed edit paragraph\n" * 160
    write = call("write", json.dumps({"path": "draft.md", "content": draft}), "write")
    missing = call("edit", json.dumps({"path": "missing.md", "old_text": failed, "new_text": "unused"}), "missing")
    edit = call("edit", json.dumps({"path": "draft.md", "old_text": draft, "new_text": revised}), "edit")
    replies = iter([Reply(tool_calls=[write, missing]), Reply(tool_calls=[edit]), Reply(content="done")])

    def respond(messages, _tools):
        if messages[0]["content"] == SYSTEM:
            return Reply(content="## Goal\nRevise the draft", finish="stop")
        return next(replies)

    llm = FakeLLM(respond, window=32_768)
    agent = Agent(make_ctx(llm, big_result_tokens=512, keep_recent_tokens=100),
                  tools=[CORE_TOOLS["write"], CORE_TOOLS["edit"]], session=Session(tmp_path / "session.jsonl"))
    assert agent.run("Write and revise the draft") == "done"
    assert (tmp_path / "draft.md").read_text() == revised

    records = [record for record in agent.memory.records() if record["kind"] == "arguments"]
    assert len(records) == 2
    for request, original in [(llm.requests[1], write), (llm.requests[2], edit)]:
        messages = request["messages"]
        shortened = next(c for m in messages for c in m.get("tool_calls", []) if c["id"] == original["id"])
        payload = json.loads(shortened["function"]["arguments"])
        assert payload["path"] == "draft.md"
        assert shortened["function"]["name"] == original["function"]["name"]
        assert len(shortened["function"]["arguments"]) < 1024
        assert any(m.get("tool_call_id") == original["id"] for m in messages)
        record, = [record for record in records if record["id"] in shortened["function"]["arguments"]]
        assert (tmp_path / record["path"]).read_text() == original["function"]["arguments"]
        assert record["id"] in agent.memory.index.read_text()
        assert missing in [c for m in messages for c in m.get("tool_calls", [])]
    assert Session.load(agent.session.path).context() == agent.session.context()

    assert agent.compact(force=True)
    checkpoint_prompt = llm.requests[-1]["messages"][-1]["content"]
    assert "Original arguments:" in checkpoint_prompt
    assert "Original draft paragraph" not in checkpoint_prompt
    assert "Revised draft paragraph" not in checkpoint_prompt
    assert Session.load(agent.session.path).context() == agent.session.context()


def test_large_write_keeps_original_arguments_if_archive_fails(make_ctx, tmp_path, monkeypatch):
    draft = "Draft paragraph\n" * 200
    write = call("write", json.dumps({"path": "draft.md", "content": draft}))
    replies = iter([Reply(tool_calls=[write]), Reply(content="done")])
    agent = Agent(make_ctx(FakeLLM(lambda _m, _t: next(replies), window=32_768), big_result_tokens=512),
                  tools=[CORE_TOOLS["write"]], session=Session(tmp_path / "session.jsonl"))

    def fail(*_args, **_kwargs):
        raise OSError("archive unavailable")

    monkeypatch.setattr(agent.memory, "archive", fail)
    assert agent.run("Write the draft") == "done"
    assert (tmp_path / "draft.md").read_text() == draft
    assert agent.session.messages[1]["tool_calls"] == [write]
    assert Session.load(agent.session.path).context() == agent.session.context()
