"""Tests for Global Memory Store and Dreaming Task in kentc-breezeman."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from kentc_agent.config import STATE_DIR, Settings
from kentc_breezeman.app import create_app
from kentc_breezeman.dream import collect_session_delta, run_dream
from kentc_breezeman.memory_store import MemoryNode, MemoryStore
from kentc_breezeman.runtime import Runtime


class _FakeLLM:
    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = list(responses or [])
        self.calls: list[list[dict[str, str]]] = []

    def info(self, refresh: bool = False):
        return SimpleNamespace(id="fake-model", context_window=32768)

    def chat(self, messages, tools=None, **kwargs):
        self.calls.append(messages)
        content = self._responses.pop(0) if self._responses else '{"candidates": []}'
        return SimpleNamespace(content=content, tool_calls=[], usage=None, finish_reason="stop")


def _write_journal(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_memory_store_roundtrip_and_index(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory")
    store.ensure_layout()

    active = MemoryNode(
        id="fact-user-style",
        type="fact",
        summary="User prefers minimalist design.",
        rel_path="facts/user/style.md",
        body="- Keep outputs concise.",
        tags=["user", "style"],
    )
    superseded = MemoryNode(
        id="fact-old-job",
        type="fact",
        summary="User worked at OldCo.",
        rel_path="facts/user/old-job.md",
        status="superseded",
        valid_until="2026-11-19",
    )
    store.write_node(active)
    store.write_node(superseded)

    loaded = store.read_node("facts/user/style.md")
    assert loaded.id == "fact-user-style"
    assert loaded.summary == "User prefers minimalist design."

    index_path = store.rebuild_index(last_dreamed="2026-11-19")
    index_text = index_path.read_text(encoding="utf-8")
    assert "fact-user-style" in index_text
    assert "fact-old-job" not in index_text

    arch_rel = store.archive_node("facts/user/old-job.md")
    assert arch_rel == "archive/facts/user/old-job.md"
    assert not (store.root / "facts/user/old-job.md").exists()
    assert (store.root / arch_rel).is_file()

    with pytest.raises(ValueError):
        store.read_node("../escape.md")
    assert not (store.root / "proposals").exists()


def test_collect_session_delta_uses_topics_and_uncompacted_tail(tmp_path: Path) -> None:
    jpath = tmp_path / STATE_DIR / "sessions" / "s1.jsonl"
    mdir = tmp_path / STATE_DIR / "memory" / "s1"
    mdir.mkdir(parents=True, exist_ok=True)
    (mdir / "arch.md").write_text("# Architecture\nUse append-only jsonl.\n", encoding="utf-8")

    _write_journal(
        jpath,
        [
            {"type": "session", "id": "s1"},
            {"type": "message", "id": 0, "message": {"role": "user", "content": "old compacted msg"}},
            {"type": "compaction", "summary": "cp", "first_kept_id": 1, "topic_root": str(mdir), "topics": {}},
            {"type": "message", "id": 1, "message": {"role": "user", "content": "fresh tail msg"}},
        ],
    )

    delta = collect_session_delta("s1", jpath, mdir, prev_watermark=None)
    assert delta is not None
    assert "arch.md" in delta.changed_topics
    assert [m["content"] for m in delta.tail_messages] == ["fresh tail msg"]
    assert delta.next_msg_id == 2

    # Second call with updated watermark finds nothing new
    delta2 = collect_session_delta(
        "s1",
        jpath,
        mdir,
        prev_watermark={"last_msg_id": delta.next_msg_id, "topic_hashes": delta.topic_hashes},
    )
    assert delta2 is None


def test_run_dream_three_tracks_supersede_promote_and_sim(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory")
    store.ensure_layout()
    store.write_node(
        MemoryNode(
            id="fact-user-job-old",
            type="fact",
            summary="User works at OldCorp.",
            rel_path="facts/user/job-old.md",
            body="Role: Engineer at OldCorp.",
        )
    )
    store.write_node(
        MemoryNode(
            id="sim-pdf-overflow",
            type="sim",
            summary="For large PDF on qwen38, raising reserve_tokens -> failed (discard).",
            rel_path="sim/pdf-overflow.md",
            body="### [2026-11-18]\n- Strategy: raise reserve_tokens -> FAILED",
            models_tested=["qwen38"],
        )
    )
    store.rebuild_index(last_dreamed="2026-11-18")

    s1_j = tmp_path / STATE_DIR / "sessions" / "s1.jsonl"
    _write_journal(
        s1_j,
        [
            {"type": "session", "id": "s1"},
            {"type": "message", "id": 0, "message": {"role": "user", "content": "I moved to NewCorp."}},
        ],
    )
    s2_j = tmp_path / STATE_DIR / "sessions" / "s2.jsonl"
    _write_journal(
        s2_j,
        [
            {"type": "session", "id": "s2"},
            {"type": "message", "id": 0, "message": {"role": "user", "content": "Page split worked again."}},
        ],
    )

    extract_s1 = json.dumps(
        {
            "candidates": [
                {
                    "id": "fact-user-job-new",
                    "type": "fact",
                    "target_rel_path": "facts/user/job-new.md",
                    "summary": "User works at NewCorp.",
                    "tags": ["user", "career"],
                    "supersedes_id": "fact-user-job-old",
                    "body": "Role: AI VP at NewCorp.",
                },
                {
                    "id": "pattern-pdf-split",
                    "type": "pattern",
                    "target_rel_path": "patterns/pdf-split.md",
                    "summary": "When summarizing large PDFs, split by page first to avoid overflow.",
                    "tags": ["pdf"],
                    "body": "1. Split by page.",
                },
                {
                    "id": "sim-pdf-overflow",
                    "type": "sim",
                    "target_rel_path": "sim/pdf-overflow.md",
                    "summary": "For large PDF on qwen38, page-split -> verified (retain).",
                    "tags": ["pdf", "overflow"],
                    "models_tested": ["qwen38", "gemini-4"],
                    "body": "- Strategy: page-split -> VERIFIED (retain)",
                },
            ]
        }
    )
    extract_s2 = json.dumps(
        {
            "candidates": [
                {
                    "id": "pattern-pdf-split",
                    "type": "pattern",
                    "target_rel_path": "patterns/pdf-split.md",
                    "summary": "When summarizing large PDFs, split by page first to avoid overflow.",
                    "tags": ["pdf"],
                    "body": "2. Verified across two sessions.",
                }
            ]
        }
    )
    merge_pattern = "1. Split by page.\n2. Verified across two sessions."

    llm = _FakeLLM([extract_s1, extract_s2, merge_pattern])
    report = run_dream(tmp_path, llm, now=1000.0)

    assert report.sessions_processed == 2
    assert report.created == 2
    assert report.updated == 2
    assert report.superseded == 1
    assert report.archived >= 1

    # Old fact archived with superseded_by link
    archived_old = store.read_node("archive/facts/user/job-old.md")
    assert archived_old.status == "archived"
    assert archived_old.superseded_by == "fact-user-job-new"

    # Pattern promoted to verified + active on 2nd verification
    pat = store.read_node("patterns/pdf-split.md")
    assert pat.verified_count == 2
    assert pat.confidence == "verified"
    assert pat.status == "active"

    # SIM kept prior failed attempt AND appended new verified attempt
    sim = store.read_node("sim/pdf-overflow.md")
    assert "raise reserve_tokens -> FAILED" in sim.body
    assert "page-split -> VERIFIED" in sim.body
    assert "gemini-4" in sim.models_tested


def test_dream_api_and_scheduler(tmp_path: Path) -> None:
    llm = _FakeLLM(['{"candidates": []}'])
    rt = Runtime(tmp_path, Settings(), llm)
    with TestClient(create_app(rt)) as client:
        r0 = client.get("/api/dream")
        assert r0.status_code == 200
        assert r0.json()["enabled"] is False

        r1 = client.patch("/api/dream", json={"enabled": True, "interval_min": 15})
        assert r1.status_code == 200
        body = r1.json()
        assert body["enabled"] is True
        assert body["interval_min"] == 15.0
        assert body["next_run"] is not None

        r2 = client.post("/api/dream/run")
        assert r2.status_code == 200
        assert r2.json()["status"]["index_exists"] is True
        assert "volumes" in r2.json()["status"]

        # Nodes listing & search endpoint
        rt.memory_store.write_node(
            MemoryNode(
                id="fact-ui-test",
                type="fact",
                summary="User prefers Dreaming stage in topbar.",
                rel_path="facts/user/ui-test.md",
                tags=["ui"],
            )
        )
        nodes_all = client.get("/api/dream/nodes").json()
        assert any(n["id"] == "fact-ui-test" for n in nodes_all)
        nodes_filtered = client.get("/api/dream/nodes?q=topbar&track=fact").json()
        assert len(nodes_filtered) == 1 and nodes_filtered[0]["id"] == "fact-ui-test"

        # Due tick triggers dream
        due_now = r2.json()["status"]["next_run"] + 1
        assert rt.tick_dream(now=due_now) is True


def test_task_chat_and_studio_receive_root_memory_hint(tmp_path: Path) -> None:
    from kentc_breezeman.studio import StudioRegistry

    rt = Runtime(tmp_path, Settings(), _FakeLLM())
    task = rt.create_task("Subfolder Task")
    chat = rt.chat(task["chat_key"])
    expected_index = str((tmp_path / "memory" / "INDEX.md").resolve())
    assert expected_index in chat.agent.system

    # Clearing skill keeps memory hint; setting a skill preserves Chat.skill detection
    chat.set_skill(None)
    assert expected_index in chat.agent.system
    assert chat.skill is None

    reg = StudioRegistry(tmp_path, rt.skills)
    try:
        desc = reg.create_studio("TER Memory Check", template="ter")
        mounted = reg.mount(desc["id"])
        skills_seen = [
            p.skills
            for app in mounted.service.config.apps.values()
            for p in (*(a.provider for a in app.agents.values()), *app.extras.values(), app.report.provider)
            if hasattr(p, "skills")
        ]
        assert skills_seen and all(expected_index in s for s in skills_seen)
    finally:
        reg.close()


def test_tick_schedules_pre_compacts_above_half_window(tmp_path: Path, monkeypatch) -> None:
    import threading

    rt = Runtime(tmp_path, Settings(), _FakeLLM())
    task = rt.create_task("Scheduled Task")
    rt.update_dream_schedule(enabled=False)
    rt.update_task(task["id"], schedule={"enabled": True, "interval_min": 5, "prompt": "check"})
    chat = rt.chat(task["chat_key"])

    compacted_calls: list[tuple[bool, str | None]] = []
    sent_prompts: list[str] = []
    done = threading.Event()

    def fake_compact(*, force: bool = False) -> None:
        compacted_calls.append((force, chat.busy))

    def fake_run(prompt: str) -> str:
        sent_prompts.append(prompt)
        done.set()
        return "ok"

    monkeypatch.setattr(chat.agent, "_try_compact", fake_compact)
    monkeypatch.setattr(chat.agent, "run", fake_run)

    # Below 50% of dynamic (non-fixed) window -> no pre-compact
    fixed = chat.agent.fixed_tokens
    threshold = fixed + int((chat.agent.window - fixed) * 0.5)
    monkeypatch.setattr(chat.agent, "context_tokens", lambda: threshold)
    due = rt.list_tasks()[0]["schedule"]["next_run"] + 1
    assert rt.tick_schedules(now=due) == [task["id"]]
    assert done.wait(timeout=3.0)
    assert compacted_calls == []
    assert sent_prompts == ["check"]

    # Wait for worker to finish clearing busy flag
    while chat.busy:
        pass

    # Above 50% of dynamic window -> pre-compact with force=True inside worker while chat.busy == "chat"
    done.clear()
    monkeypatch.setattr(chat.agent, "context_tokens", lambda: threshold + 1)
    due2 = rt.list_tasks()[0]["schedule"]["next_run"] + 1
    assert rt.tick_schedules(now=due2) == [task["id"]]
    assert done.wait(timeout=3.0)
    assert compacted_calls == [(True, "chat")]
    assert sent_prompts == ["check", "check"]

    while chat.busy:
        pass

    # Even if fixed_tokens alone exceeds 50% of window, low dynamic tokens must NOT thrash compaction
    done.clear()
    compacted_calls.clear()
    monkeypatch.setattr(chat.agent, "fixed_tokens", int(chat.agent.window * 0.6))
    monkeypatch.setattr(chat.agent, "context_tokens", lambda: int(chat.agent.window * 0.6) + 100)
    due3 = rt.list_tasks()[0]["schedule"]["next_run"] + 1
    assert rt.tick_schedules(now=due3) == [task["id"]]
    assert done.wait(timeout=3.0)
    assert compacted_calls == []


def test_tick_schedules_defers_when_chat_busy_without_advancing_last_run(tmp_path: Path) -> None:
    rt = Runtime(tmp_path, Settings(), _FakeLLM())
    task = rt.create_task("Busy Scheduled Task")
    rt.update_task(task["id"], schedule={"enabled": True, "interval_min": 60, "prompt": "ping"})
    chat = rt.chat(task["chat_key"])
    due = rt.list_tasks()[0]["schedule"]["next_run"] + 1

    # Simulate an active user run
    chat.busy = "chat"
    try:
        assert rt.tick_schedules(now=due, retry_sec=45.0) == []
    finally:
        chat.busy = None

    sched = rt.list_tasks()[0]["schedule"]
    assert sched["last_run"] is None
    assert sched["last_status"] == "deferred_busy"
    assert sched["next_run"] == due + 45.0


def test_collect_session_delta_reads_nested_generation_topics_from_task_subfolder(tmp_path: Path) -> None:
    from kentc_agent.context.compaction import CompactionResult

    rt = Runtime(tmp_path, Settings(), _FakeLLM())
    task = rt.create_task("Long Horizon Task")
    chat = rt.chat(task["chat_key"])
    chat.session.append({"role": "user", "content": "design note"})
    chat.session.append({"role": "assistant", "content": "recorded"})
    chat.session.compact(CompactionResult("Checkpoint", {"arch": "# Arch\nNested generation topic."}), 1, 100)

    delta = collect_session_delta(
        chat.session.id,
        chat.session.path,
        tmp_path / STATE_DIR / "memory" / chat.session.id,
        prev_watermark=None,
    )
    assert delta is not None
    assert "arch.md" in delta.changed_topics
    assert "Nested generation topic." in delta.changed_topics["arch.md"]

    # Second run with watermark sees no unchanged topics
    delta2 = collect_session_delta(
        chat.session.id,
        chat.session.path,
        tmp_path / STATE_DIR / "memory" / chat.session.id,
        prev_watermark={"last_msg_id": delta.next_msg_id, "topic_hashes": delta.topic_hashes},
    )
    assert delta2 is None


def test_studio_allowed_read_roots_permits_global_memory_read_only(tmp_path: Path) -> None:
    from kentc_agent.adapters.tools import ToolContext, _read, _write
    from kentc_agent.errors import ToolError
    from kentc_agent.ports import Events
    from kentc_breezeman.studio import StudioRegistry

    mem_dir = tmp_path / "memory"
    mem_dir.mkdir(parents=True, exist_ok=True)
    index_file = mem_dir / "INDEX.md"
    index_file.write_text("# Global Memory Index\n- fact-1\n", encoding="utf-8")
    secret_file = tmp_path / "outside.txt"
    secret_file.write_text("do not read", encoding="utf-8")

    rt = Runtime(tmp_path, Settings(), _FakeLLM())
    reg = StudioRegistry(tmp_path, rt.skills)
    try:
        desc = reg.create_studio("TER Read Root Check", template="ter")
        mounted = reg.mount(desc["id"])
        providers = [
            p
            for app in mounted.service.config.apps.values()
            for p in (*(a.provider for a in app.agents.values()), *app.extras.values(), app.report.provider)
            if hasattr(p, "allowed_read_roots")
        ]
        assert providers and all(mem_dir.resolve() in p.allowed_read_roots for p in providers)

        case_dir = tmp_path / "tasks" / "ter-read-root-check" / "cases" / "C1"
        case_dir.mkdir(parents=True, exist_ok=True)
        ctx = ToolContext(case_dir, Settings(), _FakeLLM(), Events(), confine_reads=True,
                          allowed_read_roots=providers[0].allowed_read_roots)

        # Allowed: read global memory INDEX.md
        assert "Global Memory Index" in _read(ctx, {"path": str(index_file)})
        # Denied: write to global memory (read-only!)
        with pytest.raises(ToolError):
            _write(ctx, {"path": str(index_file), "content": "hacked"})
        # Denied: read arbitrary file outside case_dir and memory/
        with pytest.raises(ToolError):
            _read(ctx, {"path": str(secret_file)})
    finally:
        reg.close()


def test_clear_context_messages_checkpoint_and_all(tmp_path: Path) -> None:
    from kentc_agent.adapters.session import Session
    from kentc_agent.context.compaction import CompactionResult

    rt = Runtime(tmp_path, Settings(), _FakeLLM())
    chat = rt.new_chat()
    chat.session.bind_memory(tmp_path, tmp_path / STATE_DIR)
    chat.session.append({"role": "user", "content": "msg 1"})
    chat.session.append({"role": "assistant", "content": "reply 1"})
    chat.session.compact(CompactionResult("Old checkpoint", {"t1": "Topic 1"}), 1, 50)
    chat.session.append({"role": "user", "content": "msg 2"})

    with TestClient(create_app(rt)) as client:
        # 1. Clear checkpoint only -> keeps live messages
        r1 = client.post(f"/api/chats/{chat.key}/context/clear", json={"scope": "checkpoint"})
        assert r1.status_code == 200
        assert r1.json()["checkpoint"] == ""
        assert len(r1.json()["messages"]) == 2

        # 2. Restore a checkpoint, then clear messages only -> keeps checkpoint
        chat.session.compact(CompactionResult("Kept checkpoint", {}), 0, 50)
        r2 = client.post(f"/api/chats/{chat.key}/context/clear", json={"scope": "messages"})
        assert r2.status_code == 200
        assert r2.json()["checkpoint"] == "Kept checkpoint"
        assert len(r2.json()["messages"]) == 1
        assert "Kept checkpoint" in r2.json()["messages"][0]["content"]
        assert chat.session.messages == []

        # 3. Clear all -> clears both and reloads cleanly from disk
        chat.session.append({"role": "user", "content": "msg 3"})
        r3 = client.post(f"/api/chats/{chat.key}/context/clear", json={"scope": "all"})
        assert r3.status_code == 200
        assert r3.json()["checkpoint"] == ""
        assert r3.json()["messages"] == []

    reloaded = Session.load(chat.session.path)
    assert reloaded.summary == ""
    assert reloaded.messages == []
    assert reloaded.read_topics() == {"t1": "Topic 1"}


def test_task_and_chat_requirements_pin_persist_across_compaction(tmp_path: Path) -> None:
    from kentc_agent.adapters.session import Session
    from kentc_agent.context.compaction import CompactionResult

    rt = Runtime(tmp_path, Settings(), _FakeLLM())
    with TestClient(create_app(rt)) as client:
        task = client.post("/api/tasks", json={"name": "Long Horizon Ops"}).json()
        tid, key = task["id"], task["chat_key"]

        # Patch task with pinned requirements
        r = client.patch(
            f"/api/tasks/{tid}",
            json={"requirements": ["Always cite exact file paths.", "Never modify production DB."]},
        )
        assert r.status_code == 200
        assert r.json()["requirements"] == ["Always cite exact file paths.", "Never modify production DB."]

        # Exposed on chat requirements endpoint and context view
        assert client.get(f"/api/chats/{key}/requirements").json()["requirements"] == [
            "Always cite exact file paths.",
            "Never modify production DB.",
        ]
        ctx = client.get(f"/api/chats/{key}/context").json()
        assert ctx["requirements"] == ["Always cite exact file paths.", "Never modify production DB."]
        assert any("Always cite exact file paths." in m["content"] for m in ctx["messages"])

        # Survives compaction & disk reload
        chat = rt.chat(key)
        chat.session.append({"role": "user", "content": "run 1"})
        chat.session.compact(CompactionResult("Checkpoint after run 1", {}), 1, 50)
        assert Session.load(chat.session.path).requirements == [
            "Always cite exact file paths.",
            "Never modify production DB.",
        ]

        # Toggle / unpin via chat endpoint
        r2 = client.post(f"/api/chats/{key}/requirements", json={"text": "Never modify production DB.", "active": False})
        assert r2.status_code == 200
        assert r2.json()["requirements"] == ["Always cite exact file paths."]

        # Replace via PUT
        r3 = client.put(f"/api/chats/{key}/requirements", json={"requirements": ["Output JSON only."]})
        assert r3.status_code == 200
        assert r3.json()["requirements"] == ["Output JSON only."]


def test_bm25_topk_bounded_index_chunking_and_idempotent_pattern_verification(tmp_path: Path) -> None:
    from kentc_breezeman.dream import SessionDelta, apply_candidate, extract_candidates, DreamReport
    from kentc_breezeman.memory_store import bm25_search

    store = MemoryStore(tmp_path / "memory")
    store.ensure_layout()
    # Create 25 facts (> default max_per_track=20) including a targeted needle
    for i in range(25):
        store.write_node(
            MemoryNode(
                id=f"fact-item-{i:02d}",
                type="fact",
                summary=f"Generic architecture note number {i}.",
                rel_path=f"facts/project/item-{i:02d}.md",
                tags=["misc"],
            )
        )
    store.write_node(
        MemoryNode(
            id="fact-qwen38-overflow",
            type="fact",
            summary="Model qwen38 requires page-split for TER-2026 PDFs.",
            rel_path="facts/project/qwen38.md",
            tags=["qwen38", "ter-2026", "pdf"],
        )
    )
    index_path = store.rebuild_index(last_dreamed="2026-11-19", max_per_track=5)
    root_index = index_path.read_text(encoding="utf-8")
    assert "see `facts/INDEX.md`" in root_index
    assert (store.root / "facts" / "INDEX.md").is_file()
    assert "fact-qwen38-overflow" in (store.root / "facts" / "INDEX.md").read_text(encoding="utf-8")

    # BM25 ranks the exact domain match #1
    active = store.list_nodes(statuses={"active", "provisional"})
    top = bm25_search(active, "How should qwen38 handle TER-2026 PDFs?", top_k=3)
    assert top[0].id == "fact-qwen38-overflow"

    # Delta chunking with a tiny window splits into multiple LLM calls and deduplicates candidates
    class _SmallWindowLLM(_FakeLLM):
        def info(self, refresh: bool = False):
            return SimpleNamespace(id="tiny-model", context_window=2048)

    delta = SessionDelta(
        session_id="s-big",
        changed_topics={"big.md": ("Paragraph about qwen38 and TER-2026.\n\n" * 120).strip()},
        tail_messages=[],
        next_msg_id=1,
        topic_hashes={"big.md": "abc"},
    )
    cand_json = json.dumps({
        "candidates": [{
            "id": "pattern-idempotent",
            "type": "pattern",
            "target_rel_path": "patterns/idempotent.md",
            "summary": "When parsing TER-2026 on qwen38, split pages first.",
            "tags": ["qwen38"],
            "body": "Step 1: split pages.",
        }]
    })
    llm = _SmallWindowLLM([cand_json] * 20)
    cands = extract_candidates(llm, delta, root_index, active_nodes=active, top_k=3)
    assert len(llm.calls) > 1
    assert len(cands) == 1
    assert "fact-qwen38-overflow" in llm.calls[0][1]["content"]

    # Idempotent pattern verification: re-applying from the same session_id does NOT double-increment verified_count
    report = DreamReport()
    merge_llm = _FakeLLM(["Step 1: split pages.", "Step 1: split pages."])
    apply_candidate(merge_llm, store, cands[0], report, "2026-11-19", session_id="s-big")
    apply_candidate(merge_llm, store, cands[0], report, "2026-11-19", session_id="s-big")
    pat = store.read_node("patterns/idempotent.md")
    assert pat.verified_count == 1
    assert pat.status == "provisional"

    # Different session_id promotes verified_count -> 2 -> active/verified
    apply_candidate(merge_llm, store, cands[0], report, "2026-11-19", session_id="s-second")
    pat2 = store.read_node("patterns/idempotent.md")
    assert pat2.verified_count == 2
    assert pat2.status == "active"
    assert pat2.confidence == "verified"


def test_sim_seal_and_roll_archives_older_attempts_and_distills_head(tmp_path: Path) -> None:
    from kentc_breezeman.dream import seal_and_roll_sim

    store = MemoryStore(tmp_path / "memory")
    store.ensure_layout()
    entries = "\n\n".join(f"### [2026-11-{i:02d}]\n- Attempt {i}: strategy {i}" for i in range(1, 10))
    node = MemoryNode(
        id="sim-long-ledger",
        type="sim",
        summary="For long ledger, keep head compact.",
        rel_path="sim/long-ledger.md",
        body=entries,
    )
    store.write_node(node)

    llm = _FakeLLM(["## Active Strategy\n- Use strategy 9.\n\n## Known Pitfalls (Do Not Repeat)\n- Strategies 1-6 failed."])
    rolled = seal_and_roll_sim(llm, store, node, "2026-11-19", max_entries=8, keep_recent=3)
    assert rolled is True
    assert "## Active Strategy" in node.body
    assert "Attempt 9" in node.body and "Attempt 7" in node.body
    assert "Attempt 1" not in node.body
    assert "archive/sim/long-ledger-log.md" in node.body

    cold_text = (store.root / "archive/sim/long-ledger-log.md").read_text(encoding="utf-8")
    assert "Attempt 1" in cold_text and "Attempt 6" in cold_text
    assert "Attempt 9" not in cold_text


def test_schedule_exponential_backoff_and_circuit_breaker(tmp_path: Path, monkeypatch) -> None:
    from kentc_agent.adapters.llm import LLMError

    rt = Runtime(tmp_path, Settings(), _FakeLLM())
    task = rt.create_task("Flaky Task")
    rt.update_task(task["id"], schedule={"enabled": True, "interval_min": 30, "prompt": "check"})
    chat = rt.chat(task["chat_key"])

    def boom(*args, **kwargs):
        raise LLMError("upstream 503")

    monkeypatch.setattr(chat, "send", boom)

    # 1st failure -> backoff 60s
    t0 = rt.list_tasks()[0]["schedule"]["next_run"] + 1
    assert rt.tick_schedules(now=t0, retry_sec=60.0, max_consecutive_errors=3) == []
    s1 = rt.list_tasks()[0]["schedule"]
    assert s1["consecutive_errors"] == 1
    assert s1["last_status"] == "error"
    assert s1["next_run"] == t0 + 60.0
    assert s1["enabled"] is True

    # 2nd failure -> backoff 120s
    t1 = s1["next_run"] + 1
    assert rt.tick_schedules(now=t1, retry_sec=60.0, max_consecutive_errors=3) == []
    s2 = rt.list_tasks()[0]["schedule"]
    assert s2["consecutive_errors"] == 2
    assert s2["next_run"] == t1 + 120.0

    # 3rd failure -> circuit breaker pauses schedule
    t2 = s2["next_run"] + 1
    assert rt.tick_schedules(now=t2, retry_sec=60.0, max_consecutive_errors=3) == []
    s3 = rt.list_tasks()[0]["schedule"]
    assert s3["consecutive_errors"] == 3
    assert s3["enabled"] is False
    assert s3["next_run"] is None
    assert s3["last_status"] == "paused_error"


def test_async_worker_failure_triggers_backoff_circuit_breaker_and_recovery(tmp_path: Path, monkeypatch) -> None:
    import time as _time
    from kentc_agent.adapters.llm import LLMError

    rt = Runtime(tmp_path, Settings(), _FakeLLM())
    task = rt.create_task("Async Flaky Task")
    rt.update_task(task["id"], schedule={"enabled": True, "interval_min": 30, "prompt": "check"})
    chat = rt.chat(task["chat_key"])

    def wait_settled(expected_status: str) -> dict:
        deadline = _time.monotonic() + 3.0
        while _time.monotonic() < deadline:
            sched = rt.list_tasks()[0]["schedule"]
            if not chat.busy and sched.get("last_status") == expected_status:
                return sched
            _time.sleep(0.01)
        return rt.list_tasks()[0]["schedule"]

    def fail_in_worker(prompt: str) -> str:
        raise LLMError("async 503 inside worker")

    monkeypatch.setattr(chat.agent, "run", fail_in_worker)

    # 1st async worker failure -> backoff 60s
    t0 = rt.list_tasks()[0]["schedule"]["next_run"] + 1
    assert rt.tick_schedules(now=t0, retry_sec=60.0, max_consecutive_errors=3) == [task["id"]]
    s1 = wait_settled("error")
    assert s1["consecutive_errors"] == 1
    assert s1["last_error"] == "async 503 inside worker"
    assert s1["next_run"] == t0 + 60.0
    assert s1["enabled"] is True

    # 2nd async worker failure -> backoff 120s
    t1 = s1["next_run"] + 1
    assert rt.tick_schedules(now=t1, retry_sec=60.0, max_consecutive_errors=3) == [task["id"]]
    s2 = wait_settled("error")
    assert s2["consecutive_errors"] == 2
    assert s2["next_run"] == t1 + 120.0

    # 3rd async worker failure -> circuit breaker pauses schedule
    t2 = s2["next_run"] + 1
    assert rt.tick_schedules(now=t2, retry_sec=60.0, max_consecutive_errors=3) == [task["id"]]
    s3 = wait_settled("paused_error")
    assert s3["consecutive_errors"] == 3
    assert s3["enabled"] is False
    assert s3["next_run"] is None

    # Re-enable and succeed -> resets error counter and sets last_status = "ok"
    rt.update_task(task["id"], schedule={"enabled": True, "interval_min": 30, "prompt": "check"})
    monkeypatch.setattr(chat.agent, "run", lambda prompt: "all good")
    t3 = rt.list_tasks()[0]["schedule"]["next_run"] + 1
    assert rt.tick_schedules(now=t3, retry_sec=60.0, max_consecutive_errors=3) == [task["id"]]
    s4 = wait_settled("ok")
    assert s4["consecutive_errors"] == 0
    assert s4["last_error"] is None
    assert s4["next_run"] == t3 + 30 * 60


def test_runtime_recovers_interrupted_running_tasks_on_restart(tmp_path: Path) -> None:
    rt = Runtime(tmp_path, Settings(), _FakeLLM())
    task = rt.create_task("Crash Mid Run")
    rt.update_task(task["id"], schedule={"enabled": True, "interval_min": 30, "prompt": "ping"})
    tasks = rt._read_tasks()
    tasks[0]["schedule"]["last_status"] = "running"
    rt._write_tasks(tasks)

    # New Runtime simulates server restart
    rt2 = Runtime(tmp_path, Settings(), _FakeLLM())
    assert rt2.list_tasks()[0]["schedule"]["last_status"] == "interrupted"


def test_agent_run_dedupes_dangling_user_prompt_and_refreshes_date(tmp_path: Path, monkeypatch) -> None:
    import kentc_agent.agent.loop as loop_mod
    from kentc_agent.adapters.llm import LLMError, Reply
    from kentc_agent.adapters.tools import ToolContext
    from kentc_agent.agent import Agent
    from kentc_agent.ports import Events

    class _FlakyCallLLM(_FakeLLM):
        def __init__(self) -> None:
            super().__init__()
            self.attempts = 0

        def chat(self, messages, tools=None, **kwargs):
            self.attempts += 1
            if self.attempts == 1:
                raise LLMError("transient failure after user append")
            return Reply(content="recovered", finish="stop")

    current_date = ["2026-11-20"]
    real_strftime = loop_mod.time.strftime
    monkeypatch.setattr(
        loop_mod.time,
        "strftime",
        lambda fmt, *a: current_date[0] if fmt == "%Y-%m-%d" else real_strftime(fmt, *a),
    )

    llm = _FlakyCallLLM()
    ctx = ToolContext(tmp_path, Settings(), llm, Events())
    agent = Agent(ctx, tools=[])
    assert "Date: 2026-11-20" in agent.system

    # First run fails after appending user prompt
    with pytest.raises(LLMError):
        agent.run("scheduled check")
    assert [m["role"] for m in agent.session.messages] == ["user"]

    # Advance date to next day and retry the same prompt -> refreshes Date and does NOT duplicate user prompt
    current_date[0] = "2026-11-21"
    answer = agent.run("scheduled check")
    assert answer == "recovered"
    assert "Date: 2026-11-21" in agent.system
    assert [m["role"] for m in agent.session.messages] == ["user", "assistant"]


def test_dream_scheduler_backoff_circuit_breaker_and_stat_fast_path(tmp_path: Path, monkeypatch) -> None:
    # 1. Stat fast-path skips reading unchanged journal files
    jpath = tmp_path / STATE_DIR / "sessions" / "s-fast.jsonl"
    mdir = tmp_path / STATE_DIR / "memory" / "s-fast"
    _write_journal(
        jpath,
        [
            {"type": "session", "id": "s-fast"},
            {"type": "message", "id": 0, "message": {"role": "user", "content": "hello"}},
        ],
    )
    delta = collect_session_delta("s-fast", jpath, mdir, prev_watermark=None)
    assert delta is not None
    wm = {
        "last_msg_id": delta.next_msg_id,
        "topic_hashes": delta.topic_hashes,
        "journal_size": delta.journal_size,
        "journal_mtime_ns": delta.journal_mtime_ns,
        "mem_dir_mtime_ns": delta.mem_dir_mtime_ns,
    }
    monkeypatch.setattr(Path, "read_text", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("should not read unchanged journal")))
    assert collect_session_delta("s-fast", jpath, mdir, prev_watermark=wm) is None
    monkeypatch.undo()

    # 2. Dreaming scheduler exponential backoff & circuit breaker on repeated failures
    class _BrokenLLM(_FakeLLM):
        def chat(self, messages, tools=None, **kwargs):
            raise RuntimeError("dream llm down")

    rt = Runtime(tmp_path, Settings(), _BrokenLLM())
    rt.update_dream_schedule(enabled=True, interval_min=60)

    t0 = rt.dream_status()["next_run"] + 1
    assert rt.tick_dream(now=t0, retry_sec=60.0, max_consecutive_errors=3) is True
    st1 = rt.dream_status()
    assert st1["consecutive_errors"] == 1
    assert st1["last_status"] == "error"
    assert st1["next_run"] == t0 + 60.0
    assert st1["enabled"] is True

    t1 = st1["next_run"] + 1
    assert rt.tick_dream(now=t1, retry_sec=60.0, max_consecutive_errors=3) is True
    st2 = rt.dream_status()
    assert st2["consecutive_errors"] == 2
    assert st2["next_run"] == t1 + 120.0

    t2 = st2["next_run"] + 1
    assert rt.tick_dream(now=t2, retry_sec=60.0, max_consecutive_errors=3) is True
    st3 = rt.dream_status()
    assert st3["consecutive_errors"] == 3
    assert st3["enabled"] is False
    assert st3["next_run"] is None
    assert st3["last_status"] == "paused_error"
