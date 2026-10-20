from __future__ import annotations

import math

import pytest

from kentc_agent.adapters import documents
from kentc_agent.adapters.documents import Source, Unit
from kentc_agent.adapters.documents import policy
from kentc_agent.adapters.llm import Reply
from kentc_agent.adapters.session import estimate_tokens
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
