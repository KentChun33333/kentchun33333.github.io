from __future__ import annotations

import json
from pathlib import Path

import pytest

from kentc_agent.adapters.llm import Reply, Usage
from kentc_agent.adapters.session import Session, estimate_tokens
from kentc_agent.context.compaction import CompactionError, CompactionResult, find_cut, summarize


def bound_session(tmp_path: Path, *, journal: bool = True) -> Session:
    session = Session(tmp_path / "session.jsonl" if journal else None)
    session.bind_memory(tmp_path, tmp_path / ".kentc-agent")
    session.append({"role": "user", "content": "remember exact project facts"})
    session.append({"role": "assistant", "content": "recorded"})
    session.append({"role": "user", "content": "current task"})
    return session


def index_path(session: Session) -> Path:
    content = session.context()[0]["content"]
    return Path(content.split("Local topic index (use ordinary read/bash to inspect): ", 1)[1].splitlines()[0])


def topic_paths(session: Session) -> dict[str, Path]:
    result = {}
    for line in index_path(session).read_text().splitlines():
        if line.startswith("- "):
            slug, path = line[2:].split(": ", 1)
            result[slug] = Path(path)
    return result


class ScriptedLLM:
    def __init__(self, *contents: str) -> None:
        self.contents = iter(contents)
        self.requests: list[dict] = []

    def chat(self, messages, *, max_tokens, effort):
        self.requests.append({"messages": messages, "max_tokens": max_tokens, "effort": effort})
        return Reply(content=next(self.contents), finish="stop")


def compress(llm, messages=None, previous=None, **kwargs):
    return summarize(llm, messages or [{"role": "user", "content": "new project details"}], previous,
                     window=16000, reserve_tokens=2000, max_output_tokens=2000, effort="none", **kwargs)


def extraction(checkpoint: str, topics: dict[str, str]) -> str:
    return json.dumps({"checkpoint": checkpoint, "topics": topics})


def test_repeat_consolidation_preserves_old_facts_and_untouched_topics(tmp_path):
    session = bound_session(tmp_path)
    launch = "# Launch\nOwner: Dr. Vega; exact ID ZX-447. Error: E_CONN_RESET. Date uncertain."
    garden = "# Garden\nIrrigation valve model Q-18."
    session.compact(CompactionResult("Continue launch planning", {"launch": launch, "garden": garden}), 2, 100)
    old_paths = topic_paths(session)
    llm = ScriptedLLM(extraction("Await launch approval", {"launch": "Approved budget: $4200."}),
                      launch + "\nApproved budget: $4200.")
    result = compress(llm, previous=session.summary, existing_topics=session.read_topics())
    # The consolidation request includes the complete older note, including the
    # uncertainty/error at its tail, rather than just a directory or digest.
    merge_data = json.loads(llm.requests[1]["messages"][1]["content"].split("<historical-data>\n", 1)[1].split("\n</historical-data>")[0])
    assert merge_data["existing_note"] == launch
    session.compact(result, 0, 50)
    assert session.read_topics() == {"launch": launch + "\nApproved budget: $4200.", "garden": garden}
    new_paths = topic_paths(session)
    assert new_paths["garden"] == old_paths["garden"]
    assert new_paths["launch"] != old_paths["launch"]
    assert old_paths["launch"].read_text() == launch
    assert "ZX-447" not in session.context()[0]["content"]


def test_restart_advertises_readable_index_and_separate_topic_files(tmp_path):
    session = bound_session(tmp_path)
    session.compact(CompactionResult("Continue current task", {"launch": "Launch ID X-17", "garden": "Plant ID Y-92"}), 2, 100)
    before = session.context()
    session.close()
    loaded = Session.load(tmp_path / "session.jsonl")
    loaded.bind_memory(tmp_path, tmp_path / ".kentc-agent")
    assert loaded.context() == before
    paths = topic_paths(loaded)
    assert paths["launch"].read_text() == "Launch ID X-17"
    assert paths["garden"].read_text() == "Plant ID Y-92"
    assert loaded.messages == [{"role": "user", "content": "current task"}]
    assert loaded.summary == "Continue current task"


@pytest.mark.parametrize("stage", ["note", "index", "journal"])
def test_failed_publication_keeps_live_context_and_committed_topic_view(tmp_path, monkeypatch, stage):
    session = bound_session(tmp_path)
    session.compact(CompactionResult("first checkpoint", {"launch": "Exact old ID A-19"}), 1, 100)
    before = session.context()
    old_index = index_path(session)
    old_notes = {path: path.read_bytes() for path in topic_paths(session).values()}
    original_publish = session._publish_file
    original_write = session._write

    def fail_publish(generation, filename, body):
        if (stage == "note" and filename == "launch.md") or (stage == "index" and filename == "_index.md"):
            raise OSError("disk full")
        return original_publish(generation, filename, body)

    def fail_write(entry):
        if stage == "journal" and entry["type"] == "compaction":
            raise OSError("journal unavailable")
        return original_write(entry)

    monkeypatch.setattr(session, "_publish_file", fail_publish)
    monkeypatch.setattr(session, "_write", fail_write)
    with pytest.raises(OSError):
        session.compact(CompactionResult("new checkpoint", {"launch": "New ID B-20"}), 1, 50)
    assert session.context() == before
    assert index_path(session) == old_index
    assert {path: path.read_bytes() for path in old_notes} == old_notes
    assert Session.load(tmp_path / "session.jsonl").context() == before
    session.append({"role": "user", "content": "conversation remains usable"})
    assert session.messages[-1]["content"] == "conversation remains usable"


def test_append_journals_before_mutating_live_state(tmp_path, monkeypatch):
    session = bound_session(tmp_path)
    before = session.context()
    next_id = session.next_id
    write = session._write
    monkeypatch.setattr(session, "_write", lambda entry: (_ for _ in ()).throw(OSError("cannot append")))
    with pytest.raises(OSError):
        session.append({"role": "assistant", "content": "not committed"}, Usage(100, 20))
    assert session.context() == before
    assert session.next_id == next_id
    assert next_id not in session.usage
    monkeypatch.setattr(session, "_write", write)
    session.append({"role": "assistant", "content": "committed"})
    assert Session.load(tmp_path / "session.jsonl").messages[-1]["content"] == "committed"


@pytest.mark.parametrize("slug", ["../escape", "/absolute", "Uppercase", "a/b", "a\\b", ".", "a--b", "a" * 65])
def test_unsafe_topic_names_fail_before_writes_or_context_drop(tmp_path, slug):
    session = bound_session(tmp_path)
    before = session.context()
    with pytest.raises(ValueError, match="slug"):
        session.compact(CompactionResult("checkpoint", {slug: "facts"}), 2, 100)
    assert session.context() == before
    assert not (tmp_path / ".kentc-agent" / "memory").exists()


def test_index_named_topic_does_not_collide_with_directory_index(tmp_path):
    session = bound_session(tmp_path)
    session.compact(CompactionResult("checkpoint", {"index": "Search indexing facts"}), 2, 100)
    assert topic_paths(session)["index"].read_text() == "Search indexing facts"
    assert topic_paths(session)["index"] != index_path(session)


def test_no_session_notes_remain_readable_after_close_and_binding_is_lazy(tmp_path):
    session = bound_session(tmp_path, journal=False)
    assert not (tmp_path / ".kentc-agent").exists()
    session.compact(CompactionResult("checkpoint", {"launch": "Durable ID N-42"}), 2, 100)
    path = topic_paths(session)["launch"]
    session.close()
    assert path.read_text() == "Durable ID N-42"


@pytest.mark.parametrize("damage", ["missing", "edited", "escape"])
def test_replay_rejects_missing_changed_or_escaping_committed_files(tmp_path, damage):
    session = bound_session(tmp_path)
    session.compact(CompactionResult("checkpoint", {"launch": "ID R-30"}), 2, 100)
    path = topic_paths(session)["launch"]
    journal = tmp_path / "session.jsonl"
    if damage == "missing":
        path.unlink()
        expected = FileNotFoundError
    elif damage == "edited":
        path.write_text("different facts")
        expected = ValueError
    else:
        entries = [json.loads(line) for line in journal.read_text().splitlines()]
        entries[-1]["topics"]["launch"]["path"] = "../outside.md"
        journal.write_text("".join(json.dumps(entry) + "\n" for entry in entries))
        expected = ValueError
    original_journal = journal.read_bytes()
    with pytest.raises(expected):
        Session.load(journal)
    assert journal.read_bytes() == original_journal


def test_topic_symlink_cannot_escape_session_directory(tmp_path):
    session = bound_session(tmp_path)
    session.compact(CompactionResult("checkpoint", {"launch": "ID S-50"}), 2, 100)
    path = topic_paths(session)["launch"]
    outside = tmp_path / "outside.md"
    outside.write_text("ID S-50")
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(ValueError, match="escapes"):
        session.read_topics()


def test_tool_groups_are_not_split_even_with_parallel_interleaving(tmp_path):
    calls = [{"id": cid, "type": "function", "function": {"name": "read", "arguments": "{}"}} for cid in ("c1", "c2")]
    messages = [{"role": "user", "content": "task"},
                {"role": "assistant", "content": "", "tool_calls": calls},
                {"role": "tool", "tool_call_id": "c1", "content": "one"},
                {"role": "assistant", "content": "interleaved while c2 pending"},
                {"role": "tool", "tool_call_id": "c2", "content": "two"},
                {"role": "assistant", "content": "done"},
                {"role": "user", "content": "next"}]
    session = Session()
    for message in messages:
        session.append(message)
    with pytest.raises(ValueError, match="tool-call group"):
        session.compact("checkpoint", 3, 100)
    for budget in (1, 10, 20, 40, 100):
        cut = find_cut(messages, budget)
        assert cut in (0, 1, 5, 6)
        kept_calls = {call["id"] for message in messages[cut:] for call in message.get("tool_calls", [])}
        assert all(message["tool_call_id"] in kept_calls for message in messages[cut:] if message["role"] == "tool")


def test_duplicate_topic_keys_and_oversize_checkpoint_fail_without_publication():
    duplicate = '{"checkpoint":"short","topics":{"launch":"old","launch":"new"}}'
    with pytest.raises(CompactionError, match="duplicate"):
        compress(ScriptedLLM(duplicate))
    with pytest.raises(CompactionError, match="word budget"):
        compress(ScriptedLLM(extraction("one two three", {})), max_words=2)


def test_complete_oversized_old_topic_is_not_silently_truncated(tmp_path):
    session = bound_session(tmp_path)
    old = "Known exact facts " * 6000 + "TAIL-ID: KEEP-919; status uncertain"
    session.compact(CompactionResult("checkpoint", {"launch": old}), 2, 100)
    before = session.context()
    llm = ScriptedLLM(extraction("checkpoint", {"launch": "New approval"}))
    with pytest.raises(CompactionError, match="complete topic/checkpoint"):
        compress(llm, previous=session.summary, existing_topics=session.read_topics())
    assert len(llm.requests) == 1  # oversized merge never reaches the server
    assert session.context() == before
    assert session.read_topics()["launch"] == old


def test_large_history_is_chunked_and_each_request_obeys_window_budget():
    contents = [extraction("Task in progress", {}) for _ in range(20)]
    llm = ScriptedLLM(*contents)
    result = compress(llm, messages=[{"role": "user", "content": "x" * 140000}], density=1.5)
    assert result.checkpoint == "Task in progress"
    assert len(llm.requests) > 1
    for request in llm.requests:
        estimated = sum(estimate_tokens(message) for message in request["messages"])
        assert estimated * 1.5 + request["max_tokens"] <= 16000


def test_v1_journals_load_and_tiered_journals_fail_without_modification(tmp_path):
    journal = tmp_path / "v1.jsonl"
    journal.write_text('\n'.join(json.dumps(entry) for entry in [
        {"type": "session", "id": "legacy-session"},
        {"type": "message", "id": 0, "message": {"role": "user", "content": "old"}},
        {"type": "message", "id": 1, "message": {"role": "user", "content": "kept"}},
        {"type": "compaction", "summary": "Legacy checkpoint", "first_kept_id": 1, "tokens_before": 100},
    ]) + '\n')
    loaded = Session.load(journal)
    assert loaded.summary == "Legacy checkpoint"
    assert loaded.messages == [{"role": "user", "content": "kept"}]
    tiered = tmp_path / "tiered.jsonl"
    tiered.write_text('{"type":"session","id":"tiered-session"}\n{"type":"memory_cards","cards":[]}\n')
    original = tiered.read_bytes()
    with pytest.raises(ValueError, match="unsupported session record"):
        Session.load(tiered)
    assert tiered.read_bytes() == original
