from __future__ import annotations

import json
import math

import pytest

from kentc_agent.adapters import documents
from kentc_agent.adapters.documents import Source, Unit
from kentc_agent.adapters.documents import policy
from kentc_agent.adapters.llm import Reply
from kentc_agent.adapters.session import Session, estimate_tokens
from kentc_agent.adapters.tools import ToolError

from .conftest import FakeLLM


def test_small_window_transcription_preserves_text_pages_and_images(make_ctx, tmp_path):
    llm = FakeLLM(lambda _m, _t: Reply(content="Transcribed material.", finish="stop"), window=4096)
    ctx = make_ctx(llm, max_output_tokens=1024)
    ctx.density = 1.75
    text = "Account 123: balance 456.78\n" * 180
    image = documents.image_part(b"image", "image/png", 64)
    source = Source(tmp_path / "report.pdf", "pdf", "Report", [Unit("page 7", text, image)])

    documents.map_chunks(ctx, source, documents.TRANSCRIBE_TASK, "transcribing")

    source_parts = []
    image_pages = []
    for request in llm.requests:
        messages = request["messages"]
        counted = [{**m, "content": [
            {**p, "_tokens": image["_tokens"]} if p["type"] == "image_url" else p
            for p in m["content"]]} if isinstance(m["content"], list) else m for m in messages]
        prompt = math.ceil(sum(estimate_tokens(m) for m in counted) * ctx.density)
        assert prompt + request["max_tokens"] <= 4096
        parts = messages[-1]["content"]
        # Transcription expansion has room within the requested output, not merely the input window.
        assert math.ceil(estimate_tokens(counted[-1]) * ctx.density * 1.25) <= 1024
        for part in parts[1:]:
            if part["type"] == "text":
                label, body = part["text"].split(" ---\n", 1)
                assert label.startswith("\n--- page 7")
                source_parts.append(body)
            else:
                image_pages.append(parts[1]["text"].split(" ---", 1)[0])
    assert "".join(source_parts) == text
    assert image_pages == ["\n--- page 7 (part 1/" + str(len(source_parts)) + ")"]
    assert not any(event[0] == "compaction" for event in ctx.events.log)


def test_oversized_image_errors_instead_of_omitting_page(make_ctx, tmp_path):
    llm = FakeLLM(lambda _m, _t: pytest.fail("oversized evidence must not reach the model"), window=4096)
    ctx = make_ctx(llm, max_output_tokens=1024)
    source = Source(tmp_path / "scan.pdf", "pdf", "Scan", [
        Unit("page 2", "Amount: 125", documents.image_part(b"image", "image/png", 5000)),
    ])
    with pytest.raises(ToolError, match="page 2: image exceeds"):
        documents.map_chunks(ctx, source, documents.TRANSCRIBE_TASK, "transcribing")
    assert llm.requests == []


@pytest.mark.parametrize("finish", ["length", "content_filter", ""])
def test_incomplete_reply_never_populates_document_cache(make_ctx, tmp_path, monkeypatch, finish):
    llm = FakeLLM(lambda _m, _t: Reply(content="Only the first account", finish=finish), window=4096)
    ctx = make_ctx(llm, max_output_tokens=1024)
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"source document")
    monkeypatch.setattr(policy, "load_source", lambda *_a: Source(
        path, "pdf", "Scan", [Unit("page 1", "Account 123, amount 456.78")]))

    with pytest.raises(ToolError, match="incomplete content was not cached"):
        documents.document_digest(ctx, path)
    assert list((ctx.state_dir / "cache" / "documents").glob("*")) == []
    assert len(llm.requests) == (ctx.settings.output_retries + 1 if finish == "length" else 1)
    assert all(request["messages"] == llm.requests[0]["messages"] for request in llm.requests)


def test_reduction_refuses_pair_that_exceeds_window(make_ctx):
    llm = FakeLLM(lambda _m, _t: pytest.fail("oversized pair must not reach the model"), window=4096)
    ctx = make_ctx(llm)
    notes = [("page 1", "A" * 5500), ("page 2", "B" * 5500)]
    with pytest.raises(ToolError, match="no pair of notes fits"):
        documents.reduce_notes(ctx, notes, "report", "Keep the amounts", documents.merge_notes)
    assert llm.requests == []


def test_structured_digest_reduces_within_small_window(make_ctx):
    payload = '{"summary":"Accounts for 2026", "key_insights":["Outstanding debt"], "key_values":[{"field":"total", "value":"125", "location":"page 1"}]}'
    llm = FakeLLM(lambda _m, _t: Reply(content=payload, finish="stop"), window=4096)
    ctx = make_ctx(llm, max_output_tokens=1024)
    documents.structured_digest(ctx, "Account 123 owes 125.\n" * 500, "report")
    for request in llm.requests:
        assert sum(estimate_tokens(m) for m in request["messages"]) + request["max_tokens"] <= 4096


@pytest.mark.parametrize("invalid", [
    "This is a prose summary, not JSON.",
    '{"summary":"Rejected partial output","key_insights":[],"key_values":[',
    '{"summary":"Rejected output","key_insights":[],"key_values":[],}',
    'Preface {"summary":"Rejected output","key_insights":[],"key_values":[]}',
    '{"summary":123,"key_insights":[],"key_values":[]}',
    '{"summary":"Rejected output","key_values":[]}',
    '{"summary":"Rejected output","key_insights":[123],"key_values":[]}',
    '{"summary":"Rejected output","key_insights":[],"key_values":[null]}',
    '{"summary":"Rejected output","key_insights":[],"key_values":[{"field":"total","value":"125"}]}',
    '{"summary":"Rejected output","key_insights":[],"key_values":[{"field":"total","value":125,"location":"page 1"}]}',
])
def test_digest_retries_invalid_json_in_clean_session_before_accepting_and_caching(
        make_ctx, tmp_path, monkeypatch, invalid):
    expected = {"summary": "Account 123 owes 125.", "key_insights": ["Debt of 125"],
                "key_values": [{"field": "total", "value": "125", "location": "section 1"}]}
    valid = json.dumps(expected)
    outputs = iter([invalid, valid])
    llm = FakeLLM(lambda _m, _t: Reply(content=next(outputs), finish="stop"), window=8192)
    ctx = make_ctx(llm, output_retries=1)
    path = tmp_path / "report.docx"
    path.write_bytes(b"original document")
    evidence = "Section 1: Account 123 owes 125. Do not omit the account identifier."
    monkeypatch.setattr(policy, "load_source", lambda *_a: Source(
        path, "docx", "Report", [Unit("section 1", evidence)]))

    full, digest = documents.document_digest(ctx, path)

    assert evidence in full
    assert {key: digest[key] for key in expected} == expected
    assert len(llm.requests) == 2
    assert llm.requests[0]["messages"] == llm.requests[1]["messages"]
    assert evidence in json.dumps(llm.requests[1]["messages"])
    assert all(message["role"] != "assistant" for message in llm.requests[1]["messages"])
    sessions = [Session.load(log) for log in (ctx.state_dir / "subagents").glob("*.jsonl")]
    assert len(sessions) == 2
    assert len({session.id for session in sessions}) == 2
    assert sorted([message["role"] for message in session.messages] for session in sessions) == [
        ["user"], ["user", "assistant"],
    ]
    assert [message["content"] for session in sessions for message in session.messages
            if message["role"] == "assistant"] == [valid]
    assert documents.document_digest(ctx, path) == (full, digest)
    assert len(llm.requests) == 2


@pytest.mark.parametrize("stage", ["map", "reduce"])
def test_persistently_invalid_digest_map_or_reduce_never_populates_cache(
        make_ctx, tmp_path, monkeypatch, stage):
    valid = '{"summary":"Accounts owe 125.","key_insights":["Debt"],"key_values":[{"field":"total","value":"125","location":"section 1"}]}'
    invalid = '{"summary":"Rejected output","key_insights":[],"key_values":[{"value":"125"}]}'
    failed_requests = []

    def respond(messages, _tools):
        reducing = documents.DIGEST_MERGE in messages[-1]["content"][0]["text"]
        if reducing == (stage == "reduce"):
            failed_requests.append(messages)
            return Reply(content=invalid, finish="stop")
        return Reply(content=valid, finish="stop")

    llm = FakeLLM(respond, window=8192)
    ctx = make_ctx(llm, max_output_tokens=1024, doc_chunk_tokens=1300, output_retries=1)
    path = tmp_path / "report.docx"
    path.write_bytes(b"original document")
    evidence = "Account 123 owes 125 in section 1.\n" * 500
    monkeypatch.setattr(policy, "load_source", lambda *_a: Source(
        path, "docx", "Report", [Unit("section 1", evidence)]))

    with pytest.raises(ToolError, match="incomplete content was not cached"):
        documents.document_digest(ctx, path)

    assert len(failed_requests) == 2
    assert failed_requests[0] == failed_requests[1]
    assert "Rejected output" not in json.dumps(failed_requests[1])
    assert all(message["role"] != "assistant" for message in failed_requests[1])
    assert list((ctx.state_dir / "cache" / "documents").glob("*")) == []
    sessions = [Session.load(log) for log in (ctx.state_dir / "subagents").glob("*.jsonl")]
    assert len(sessions) == len(llm.requests)
    assert all(message["content"] != invalid for session in sessions
               for message in session.messages if message["role"] == "assistant")


def test_digest_retries_invalid_merge_without_replacing_accepted_map_evidence(make_ctx):
    mapped = '{"summary":"Account 123 owes 125.","key_insights":["Debt"],"key_values":[{"field":"total","value":"125","location":"section 1"}]}'
    merged = '{"summary":"Combined accounts owe 125.","key_insights":["Debt"],"key_values":[{"field":"total","value":"125","location":"section 1"}]}'
    invalid = '{"summary":"Rejected merge","key_values":[]}'
    merges = []

    def respond(messages, _tools):
        if documents.DIGEST_MERGE in messages[-1]["content"][0]["text"]:
            merges.append(messages)
            return Reply(content=invalid if len(merges) == 1 else merged, finish="stop")
        return Reply(content=mapped, finish="stop")

    llm = FakeLLM(respond, window=8192)
    ctx = make_ctx(llm, max_output_tokens=1024, doc_chunk_tokens=1300, output_retries=1)

    digest = documents.structured_digest(ctx, "Account 123 owes 125.\n" * 500, "report")

    assert digest == json.loads(merged)
    assert len(merges) >= 2
    assert merges[0] == merges[1]
    assert mapped in merges[1][-1]["content"][0]["text"]
    assert invalid not in merges[1][-1]["content"][0]["text"]
    assert all(message["role"] != "assistant" for message in merges[1])


def test_transcription_retries_truncation_with_all_original_evidence(make_ctx, tmp_path):
    outputs = iter([Reply(content="Account 123", finish="length"),
                    Reply(content="Account 123 owes 125. Deadline: 2026-12-31.", finish="stop")])
    llm = FakeLLM(lambda _m, _t: next(outputs), window=8192)
    ctx = make_ctx(llm, max_output_tokens=1024, output_retries=1)
    evidence = "Account 123 owes 125. Deadline: 2026-12-31."
    image = documents.image_part(b"original scan", "image/png", 64)
    source = Source(tmp_path / "scan.pdf", "pdf", "Scan", [Unit("page 1", evidence, image)])

    notes = documents.map_chunks(ctx, source, documents.TRANSCRIBE_TASK, "transcribing")

    assert notes == [("page 1", evidence)]
    assert len(llm.requests) == 2
    assert llm.requests[0]["messages"] == llm.requests[1]["messages"]
    parts = llm.requests[1]["messages"][-1]["content"]
    assert evidence in parts[1]["text"]
    assert parts[2]["image_url"] == image["image_url"]
    assert all(message["role"] != "assistant" for message in llm.requests[1]["messages"])


def test_structured_digest_refusal_is_not_retried_or_cached(make_ctx, tmp_path, monkeypatch):
    refusal = "I cannot provide this document summary."
    llm = FakeLLM(lambda _m, _t: Reply(content=refusal, finish="content_filter"), window=8192)
    ctx = make_ctx(llm, output_retries=2)
    path = tmp_path / "report.docx"
    path.write_bytes(b"original document")
    monkeypatch.setattr(policy, "load_source", lambda *_a: Source(
        path, "docx", "Report", [Unit("section 1", "Account 123 owes 125.")]))

    with pytest.raises(ToolError, match="incomplete content was not cached"):
        documents.document_digest(ctx, path)

    assert len(llm.requests) == 1
    assert list((ctx.state_dir / "cache" / "documents").glob("*")) == []
    sessions = [Session.load(log) for log in (ctx.state_dir / "subagents").glob("*.jsonl")]
    assert len(sessions) == 1
    assert [message["role"] for message in sessions[0].messages] == ["user"]
