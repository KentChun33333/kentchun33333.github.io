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
