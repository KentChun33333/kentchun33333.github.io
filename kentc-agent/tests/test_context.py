from __future__ import annotations

import io
import json
import urllib.error

from kentc_agent.agent import Agent
from kentc_agent.context.compaction import find_cut
from kentc_agent.config import STATE_DIR
from kentc_agent.adapters.llm import ContextOverflow, LLMClient, Reply, Usage
from kentc_agent.adapters.session import Session, estimate_tokens
from kentc_agent.adapters.tools import CORE_TOOLS

from .conftest import FakeLLM, call


def history(turns: int, size: int = 400) -> list[dict]:
    """user -> assistant(tool call) -> tool -> assistant, repeated."""
    msgs = []
    for i in range(turns):
        msgs += [{"role": "user", "content": f"task {i} " + "u" * size},
                 {"role": "assistant", "content": "", "tool_calls": [call("read", '{"path": "a"}', f"c{i}")]},
                 {"role": "tool", "tool_call_id": f"c{i}", "content": "t" * size},
                 {"role": "assistant", "content": f"done {i} " + "a" * size}]
    return msgs


def test_cut_is_first_valid_point_inside_budget_and_never_orphans_a_tool_result():
    msgs = history(10)
    for keep in (50, 200, 500, 1000):
        cut = find_cut(msgs, keep)
        assert 0 < cut < len(msgs)
        assert msgs[cut]["role"] in ("user", "assistant")
        prev = max(i for i in range(cut) if msgs[i]["role"] in ("user", "assistant"))
        assert sum(estimate_tokens(m) for m in msgs[prev:]) >= keep   # one cut earlier would keep the budget
        assert sum(estimate_tokens(m) for m in msgs[cut + 1:]) < keep
        kept_ids = {c["id"] for m in msgs[cut:] for c in m.get("tool_calls") or []}
        assert all(m["tool_call_id"] in kept_ids for m in msgs[cut:] if m["role"] == "tool")


def test_cut_is_zero_when_everything_fits():
    assert find_cut(history(2), 100_000) == 0


def test_session_reload_rebuilds_context_after_compaction(tmp_path):
    path = tmp_path / "s.jsonl"
    s = Session(path)
    for m in history(3):
        s.append(m, Usage(1000, 50) if m["role"] == "assistant" else None)
    s.compact("SUMMARY", 4, tokens_before=999)
    s.append({"role": "user", "content": "after"})
    loaded = Session.load(path)
    assert loaded.context() == s.context()
    assert loaded.context()[0]["content"].count("SUMMARY") == 1
    assert loaded.messages[0] == history(3)[4]


def test_token_count_ignores_usage_from_before_a_compaction():
    s = Session()
    for m in history(3):
        s.append(m, Usage(50_000, 100) if m["role"] == "assistant" else None)
    assert s.context_tokens(0) >= 50_100
    s.compact("short", 8, tokens_before=50_100)
    assert s.context_tokens(0) < 5_000


def test_token_count_is_server_usage_plus_trailing_estimates():
    s = Session()
    s.append({"role": "user", "content": "x"})
    s.append({"role": "assistant", "content": "y"}, Usage(700, 30))
    tail = {"role": "user", "content": "z" * 400}
    s.append(tail)
    assert s.context_tokens(10_000) == 730 + estimate_tokens(tail)


def test_agent_runs_tools_until_answer(make_ctx, tmp_path):
    (tmp_path / "a.txt").write_text("hello world")
    replies = iter([Reply(tool_calls=[call("read", '{"path": "a.txt"}')], finish="tool_calls"),
                    Reply(content="it says hello world", finish="stop")])
    llm = FakeLLM(lambda m, t: next(replies))
    agent = Agent(make_ctx(llm), tools=[CORE_TOOLS["read"]])
    assert agent.run("read a.txt") == "it says hello world"
    tool_msg = llm.requests[1]["messages"][-1]
    assert tool_msg == {"role": "tool", "tool_call_id": "c1", "content": "hello world"}


def test_agent_compacts_when_over_budget_and_keeps_pairs(make_ctx):
    def script(messages, tools):
        if "context checkpoint" in str(messages[-1]["content"]) or "<previous-summary>" in str(messages[-1]["content"]):
            return Reply(content="## Goal\nsummarized", finish="stop")
        return Reply(content="ok " + "r" * 800, finish="stop")
    llm = FakeLLM(script, window=4000)
    agent = Agent(make_ctx(llm, reserve_tokens=1000, keep_recent_tokens=800), tools=[])
    for i in range(12):
        agent.run(f"question {i} " + "q" * 800)
    assert agent.session.summary and "summarized" in agent.session.summary
    assert agent.context_tokens() <= agent.window - agent.reserve + 600
    assert all(r["max_tokens"] > 0 for r in llm.requests)
    roles = [m["role"] for m in agent.session.messages]
    assert roles[0] != "tool"


def overflowing(n: int, summary: Reply):
    """A model whose 'final' request overflows `n` times; the summarizer replies `summary`."""
    state = {"overflows": 0}

    def script(messages, tools):
        last = str(messages[-1]["content"])
        if "context checkpoint" in last:
            return summary
        if last.startswith("final") and state["overflows"] < n:
            state["overflows"] += 1
            raise ContextOverflow("request exceeds the context window")
        return Reply(content="fine", finish="stop")
    return script


def test_server_overflow_first_shrinks_the_reply_then_compacts(make_ctx):
    llm = FakeLLM(overflowing(2, Reply(content="## Goal\nS", finish="stop")), window=100_000)
    agent = Agent(make_ctx(llm), tools=[])
    for i in range(4):
        agent.run(f"q{i}")
    assert agent.run("final") == "fine"
    budgets = [r["max_tokens"] for r in llm.requests if str(r["messages"][-1]["content"]).startswith("final")]
    assert budgets[1] == budgets[0] // 2               # 1st overflow: a smaller reply, no compaction yet
    assert agent.session.summary == "## Goal\nS"       # 2nd overflow: compacted, then answered


def test_failed_compaction_after_an_overflow_does_not_end_the_run(make_ctx):
    llm = FakeLLM(overflowing(2, Reply(content="", finish="length")), window=100_000)   # every summary cut off
    agent = Agent(make_ctx(llm), tools=[])
    for i in range(4):
        agent.run(f"q{i}")
    assert agent.run("final") == "fine" and agent.session.summary is None


def test_server_overflow_hint_sets_the_retry_budget(make_ctx):
    state = {"first": True}

    def script(messages, tools):
        if state["first"]:
            state["first"] = False
            raise ContextOverflow("request exceeds the context window: prompt (900 tokens) + max tokens (9000) "
                                  "exceeds the context (4000); send a smaller max_tokens (at most 2800 here)")
        return Reply(content="ok", finish="stop")
    llm = FakeLLM(script, window=100_000)
    assert Agent(make_ctx(llm), tools=[]).run("hi") == "ok"
    assert llm.requests[1]["max_tokens"] == 2800 - 16            # the server's own limit, not a guess


def test_estimates_learn_the_servers_token_density(make_ctx):
    def counted(messages):                                        # this server counts 1.5x chars/4
        return int(sum(len(str(m.get("content"))) for m in messages) / 4 * 1.5)
    llm = FakeLLM(lambda m, t: Reply(content="ok", finish="stop", usage=Usage(counted(m), 10)), window=100_000)
    agent = Agent(make_ctx(llm), tools=[])
    agent.run("x" * 8000)
    agent.session.usage.clear()                                   # as after a compaction: nothing counted
    actual = counted([{"content": agent.system}] + agent.session.context())
    assert abs(agent.context_tokens() - actual) / actual < 0.1


def test_overflow_is_recognised_in_litellm_vllm_wording():
    message = ("litellm.ContextWindowExceededError: litellm.BadRequestError: OpenAIException - This model's maximum "
               "context length is 15536 tokens. However, you requested 17508 tokens (10955 in the messages, 6553 in "
               "the completion). Please reduce the length of the messages or completion.")
    body = io.BytesIO(json.dumps({"error": {"message": message, "code": "400"}}).encode())
    err = LLMClient._http_error(urllib.error.HTTPError("http://proxy/v1/chat/completions", 400, "Bad Request",
                                                          {}, body))  # type: ignore[arg-type]
    assert isinstance(err, ContextOverflow)
    assert (err.prompt_tokens, err.window, err.fit) == (10955, 15536, 15536 - 10955)


def test_turn_over_budget_routes_largest_results_first_and_keeps_small_ones(make_ctx, tmp_path):
    sizes = {"a.txt": 400, "b.txt": 240, "c.txt": 40}           # 100 + 60 + 10 tokens: no single result is big
    for name, n in sizes.items():
        (tmp_path / name).write_text("x" * n)
    calls = [call("read", f'{{"path": "{n}"}}', f"c{i}") for i, n in enumerate(sizes)]
    replies = iter([Reply(tool_calls=calls), Reply(content="done")])
    llm = FakeLLM(lambda m, t: next(replies), window=100_000)
    agent = Agent(make_ctx(llm, big_result_tokens=150, big_turn_tokens=120, big_digest_tokens=25),
                  tools=[CORE_TOOLS["read"]])
    assert agent.run("read them") == "done"
    results = {m["tool_call_id"]: m["content"] for m in agent.session.messages if m["role"] == "tool"}
    assert results["c0"].startswith("[Big result: read(path=a.txt)")     # 170 > 120: the largest goes first ...
    assert results["c1"] == "x" * 240 and results["c2"] == "x" * 40     # ... and then the turn fits
    assert (tmp_path / STATE_DIR / "operations" / agent.session.id / "1" / "c0" / "digest.json").is_file()
