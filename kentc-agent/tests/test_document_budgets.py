from __future__ import annotations

import json
import math

import pytest

from kentc_agent.adapters import documents
from kentc_agent.adapters.documents import Source, Unit, policy
from kentc_agent.adapters.llm import Reply
from kentc_agent.adapters.session import Session, estimate_tokens
from kentc_agent.adapters.tools import ToolError

from .conftest import FakeLLM


def stub_docx(tmp_path, monkeypatch, text: str):
    path = tmp_path / "report.docx"
    path.write_bytes(b"original document")
    monkeypatch.setattr(policy, "load_source", lambda *_a: Source(path, "docx", "Report", [Unit("section 1", text)]))
    return path


def test_small_window_transcription_preserves_text_pages_and_images(make_ctx, tmp_path):
    llm = FakeLLM(lambda _m, _t: Reply(content="Transcribed material.", finish="stop"), window=4096)
    ctx = make_ctx(llm, max_output_tokens=1024)
    ctx.density = 1.75
    text = "Account 123: balance 456.78\n" * 180
    image = documents.image_part(b"image", "image/png", 64)
    source = Source(tmp_path / "report.pdf", "pdf", "Report", [Unit("page 7", text, image)])

    documents.map_chunks(ctx, source, documents.TRANSCRIBE_TASK, "transcribing")

    source_parts, image_pages = [], []
    for request in llm.requests:
        messages = request["messages"]
        counted = [{**m, "content": [
            {**p, "_tokens": image["_tokens"]} if p["type"] == "image_url" else p
            for p in m["content"]]} if isinstance(m["content"], list) else m for m in messages]
        assert math.ceil(sum(estimate_tokens(m) for m in counted) * ctx.density) + request["max_tokens"] <= 4096
        assert math.ceil(estimate_tokens(counted[-1]) * ctx.density * 1.25) <= 1024
        parts = messages[-1]["content"]
        for part in parts[1:]:
            if part["type"] == "text":
                label, body = part["text"].split(" ---\n", 1)
                assert label.startswith("\n--- page 7")
                source_parts.append(body)
            else:
                image_pages.append(parts[1]["text"].split(" ---", 1)[0])
    assert "".join(source_parts) == text
    assert image_pages == [f"\n--- page 7 (part 1/{len(source_parts)})"]
    assert not any(event[0] == "compaction" for event in ctx.events.log)


def test_oversized_image_and_reduction_pair_error_before_model(make_ctx, tmp_path):
    ctx = make_ctx(FakeLLM(window=4096), max_output_tokens=1024)
    source = Source(tmp_path / "scan.pdf", "pdf", "Scan", [
        Unit("page 2", "Amount: 125", documents.image_part(b"image", "image/png", 5000)),
    ])
    with pytest.raises(ToolError, match="page 2: image exceeds"):
        documents.map_chunks(ctx, source, documents.TRANSCRIBE_TASK, "transcribing")
    with pytest.raises(ToolError, match="no pair of notes fits"):
        documents.reduce_notes(ctx, [("page 1", "A" * 5500), ("page 2", "B" * 5500)], "report", "Keep",
                               documents.merge_notes)


@pytest.mark.parametrize("finish", ["length", "content_filter", ""])
def test_incomplete_or_refused_reply_never_populates_document_cache(make_ctx, tmp_path, monkeypatch, finish):
    llm = FakeLLM(lambda _m, _t: Reply(content="Only the first account", finish=finish), window=4096)
    ctx = make_ctx(llm, max_output_tokens=1024, output_retries=2)
    path = stub_docx(tmp_path, monkeypatch, "Account 123, amount 456.78")
    with pytest.raises(ToolError, match="incomplete content was not cached"):
        documents.document_digest(ctx, path)
    assert list((ctx.state_dir / "cache" / "documents").glob("*")) == []
    assert len(llm.requests) == (ctx.settings.output_retries + 1 if finish == "length" else 1)
    assert all(r["messages"] == llm.requests[0]["messages"] for r in llm.requests)


def test_structured_digest_reduces_within_small_window(make_ctx):
    payload = '{"summary":"Accounts for 2026","key_insights":["Debt"],"key_values":[{"field":"total","value":"125","location":"page 1"}]}'
    llm = FakeLLM(lambda _m, _t: Reply(content=payload, finish="stop"), window=4096)
    documents.structured_digest(make_ctx(llm, max_output_tokens=1024), "Account 123 owes 125.\n" * 500, "report")
    assert all(sum(estimate_tokens(m) for m in r["messages"]) + r["max_tokens"] <= 4096 for r in llm.requests)


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
    evidence = "Section 1: Account 123 owes 125. Do not omit the account identifier."
    path = stub_docx(tmp_path, monkeypatch, evidence)

    full, digest = documents.document_digest(ctx, path)
    assert evidence in full and {k: digest[k] for k in expected} == expected
    assert len(llm.requests) == 2 and llm.requests[0]["messages"] == llm.requests[1]["messages"]
    assert all(m["role"] != "assistant" for m in llm.requests[1]["messages"])
    sessions = [Session.load(log) for log in (ctx.state_dir / "subagents").glob("*.jsonl")]
    assert sorted([m["role"] for m in s.messages] for s in sessions) == [["user"], ["user", "assistant"]]
    assert documents.document_digest(ctx, path) == (full, digest) and len(llm.requests) == 2


@pytest.mark.parametrize("stage", ["map", "reduce"])
def test_persistently_invalid_digest_map_or_reduce_never_populates_cache(make_ctx, tmp_path, monkeypatch, stage):
    valid = '{"summary":"Accounts owe 125.","key_insights":["Debt"],"key_values":[{"field":"total","value":"125","location":"section 1"}]}'
    invalid = '{"summary":"Rejected output","key_insights":[],"key_values":[{"value":"125"}]}'
    failed_requests = []

    def respond(messages, _tools):
        if (documents.DIGEST_MERGE in messages[-1]["content"][0]["text"]) == (stage == "reduce"):
            failed_requests.append(messages)
            return Reply(content=invalid, finish="stop")
        return Reply(content=valid, finish="stop")

    ctx = make_ctx(FakeLLM(respond, window=8192), max_output_tokens=1024, doc_chunk_tokens=1300, output_retries=1)
    path = stub_docx(tmp_path, monkeypatch, "Account 123 owes 125 in section 1.\n" * 500)
    with pytest.raises(ToolError, match="incomplete content was not cached"):
        documents.document_digest(ctx, path)
    assert len(failed_requests) == 2 and failed_requests[0] == failed_requests[1]
    assert "Rejected output" not in json.dumps(failed_requests[1])
    assert list((ctx.state_dir / "cache" / "documents").glob("*")) == []


def test_digest_merge_and_transcription_retries_keep_original_evidence(make_ctx, tmp_path):
    mapped = '{"summary":"Account 123 owes 125.","key_insights":["Debt"],"key_values":[{"field":"total","value":"125","location":"section 1"}]}'
    merged = '{"summary":"Combined accounts owe 125.","key_insights":["Debt"],"key_values":[{"field":"total","value":"125","location":"section 1"}]}'
    merges = []

    def respond(messages, _tools):
        if documents.DIGEST_MERGE in messages[-1]["content"][0]["text"]:
            merges.append(messages)
            return Reply(content='{"summary":"Rejected merge","key_values":[]}' if len(merges) == 1 else merged,
                         finish="stop")
        return Reply(content=mapped, finish="stop")

    ctx = make_ctx(FakeLLM(respond, window=8192), max_output_tokens=1024, doc_chunk_tokens=1300, output_retries=1)
    assert documents.structured_digest(ctx, "Account 123 owes 125.\n" * 500, "report") == json.loads(merged)
    assert len(merges) >= 2 and merges[0] == merges[1] and "Rejected merge" not in merges[1][-1]["content"][0]["text"]

    evidence = "Account 123 owes 125. Deadline: 2026-12-31."
    outputs = iter([Reply(content="Account 123", finish="length"), Reply(content=evidence, finish="stop")])
    llm2 = FakeLLM(lambda _m, _t: next(outputs), window=8192)
    image = documents.image_part(b"original scan", "image/png", 64)
    source = Source(tmp_path / "scan.pdf", "pdf", "Scan", [Unit("page 1", evidence, image)])
    assert documents.map_chunks(make_ctx(llm2, max_output_tokens=1024, output_retries=1), source,
                                documents.TRANSCRIBE_TASK, "transcribing") == [("page 1", evidence)]
    assert llm2.requests[0]["messages"] == llm2.requests[1]["messages"]
