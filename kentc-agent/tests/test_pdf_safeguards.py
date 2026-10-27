from __future__ import annotations

import json

import pymupdf
import pytest

from kentc_agent.adapters.documents import load_pdf
from kentc_agent.adapters.documents.policy import answer, document_digest
from kentc_agent.adapters.llm import ModelInfo, Reply
from kentc_agent.errors import ToolError

from .conftest import FakeLLM


PLACEHOLDER = ("Please wait... If this message is not eventually replaced by the proper contents of the "
               "document, your PDF viewer may not be able to display this type of document. You can upgrade "
               "to the latest version of Adobe Reader for Windows, Mac, or Linux by visiting the Adobe website.")


def pdf(path, texts, *, xfa=False, indirect=True, packets=False):
    with pymupdf.open() as doc:
        for text in texts:
            page = doc.new_page()
            assert page.insert_textbox(pymupdf.Rect(40, 40, 550, 750), text, fontsize=9) >= 0
        if xfa:
            stream = doc.get_new_xref()
            doc.update_object(stream, "<< >>")
            doc.update_stream(stream, b'<template xmlns="http://www.xfa.org/schema/xfa-template/3.3/"/>')
            value = f"[(template) {stream} 0 R]" if packets else f"{stream} 0 R"
            form = f"<< /XFA {value} >>"
            if indirect:
                ref = doc.get_new_xref()
                doc.update_object(ref, form)
                form = f"{ref} 0 R"
            doc.xref_set_key(doc.pdf_catalog(), "AcroForm", form)
        doc.save(path)
    return path


def unused_model():
    return FakeLLM(lambda m, t: pytest.fail("uninspected PDF must not reach the model"), window=65536)


@pytest.mark.parametrize("mode", ["auto", "always", "never"])
@pytest.mark.parametrize("xfa", [False, True])
@pytest.mark.parametrize("text", [PLACEHOLDER, PLACEHOLDER.upper().replace(" ", "\n"),
    "To view the full contents of this document, you need a later version of the PDF viewer."])
def test_viewer_placeholder_fails_before_model_or_cache(make_ctx, tmp_path, mode, text, xfa):
    path = pdf(tmp_path / "blocked.pdf", [text], xfa=xfa)
    ctx = make_ctx(unused_model(), doc_render=mode)
    for read in (lambda: document_digest(ctx, path), lambda: answer(ctx, path, "What is the balance?")):
        with pytest.raises(ToolError):
            read()
    assert ctx.llm.requests == []
    assert not list((ctx.state_dir / "cache" / "documents").glob("*"))


@pytest.mark.parametrize("indirect", [False, True])
@pytest.mark.parametrize("packets", [False, True])
def test_xfa_uses_visual_static_pages_not_extracted_text(make_ctx, tmp_path, indirect, packets):
    text = "Account balance: 125. This is the static PDF appearance. " * 8
    path = pdf(tmp_path / "xfa.pdf", [text], xfa=True, indirect=indirect, packets=packets)
    src = load_pdf(make_ctx(unused_model()), path, None)
    assert [(u.name, u.text) for u in src.units] == [("page 1", "")]
    assert src.units[0].image["image_url"]["url"].startswith("data:image/png;base64,")
    assert any("dynamic XFA data is not inspected" in n for n in src.notes)


@pytest.mark.parametrize("mode,vision", [("never", True), ("auto", False), ("always", False)])
def test_xfa_fails_when_visual_fallback_is_unavailable(make_ctx, tmp_path, mode, vision):
    path = pdf(tmp_path / "xfa.pdf", ["Account balance: 125"], xfa=True)
    llm = unused_model()
    llm._info = ModelInfo("fake", 65536, vision)
    ctx = make_ctx(llm, doc_render=mode)
    with pytest.raises(ToolError):
        document_digest(ctx, path)
    assert llm.requests == []
    assert not list((ctx.state_dir / "cache" / "documents").glob("*"))


def test_page_selection_does_not_claim_unselected_placeholder_was_inspected(make_ctx, tmp_path):
    path = pdf(tmp_path / "mixed.pdf", [PLACEHOLDER, "Actual balance: 125. " * 20])
    ctx = make_ctx(unused_model())
    src = load_pdf(ctx, path, "2")
    assert [u.name for u in src.units] == ["page 2"]
    assert "125" in src.units[0].text
    assert src.notes == ["pages 2 only"]
    with pytest.raises(ToolError):
        load_pdf(ctx, path, None)


def test_ordinary_adobe_reader_mentions_are_not_placeholders(make_ctx, tmp_path):
    text = "Please wait for approval. Use Adobe Reader to sign this ordinary invoice. Balance: 125. " * 4
    path = pdf(tmp_path / "invoice.pdf", [text])
    src = load_pdf(make_ctx(unused_model()), path, None)
    assert "Balance: 125" in src.units[0].text
    assert all(u.image is None for u in src.units)
    assert src.notes == []


def test_xfa_limitation_survives_transcription_digest_and_cached_read(make_ctx, tmp_path):
    path = pdf(tmp_path / "xfa.pdf", ["Account balance: 125"], xfa=True)
    replies = iter([Reply(content="Static account balance: 125.", finish="stop"),
                    Reply(content=json.dumps({"summary": "Account balance is 125.",
                                              "key_insights": [], "key_values": []}), finish="stop")])
    llm = FakeLLM(lambda m, t: next(replies), window=65536)
    ctx = make_ctx(llm)
    full, digest = document_digest(ctx, path)
    assert "dynamic XFA data is not inspected" in full
    assert any("dynamic XFA data is not inspected" in n for n in digest["metadata"]["notes"])
    assert document_digest(ctx, path) == (full, digest)
    assert len(llm.requests) == 2
    evidence = llm.requests[0]["messages"][-1]["content"]
    assert any(p["type"] == "image_url" for p in evidence)
    assert all("Account balance: 125" not in p.get("text", "") for p in evidence)
