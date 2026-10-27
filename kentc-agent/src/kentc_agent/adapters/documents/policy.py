"""The read policy for documents: convert, answer, digest, route, cache, and attachments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ...context.bigcontext import folder, limits, note_document, real_tokens, store, tokens
from ...workflow import parse_json_object
from ...errors import ToolError
from ..filetypes import DOC_SUFFIXES, reject_unsupported
from ..tools import ToolContext, page, rel
from .budget import map_chunks, merge_notes, reduce_notes
from .common import DIGEST_MERGE, DIGEST_TASK, TRANSCRIBE_TASK, Source, kind_of, split_text
from .loaders import load_source

CACHE_VERSION = "9"


def answer(ctx: ToolContext, path: Path, question: str, pages: str | None = None) -> str:
    """The parsing sub-agent(s) answering `question` from the document: one per chunk (map), then merged. Cached."""
    key = cache_key(ctx, path, "answer", question, pages)
    cached = cache_get(ctx, key, path)
    if cached is not None:
        return cached
    src = load_source(ctx, path, pages)
    task = (f"Extract everything relevant to this question, citing where it appears (page, sheet/row, slide, "
            f"e-mail): {question}\nIf nothing here is relevant, reply exactly: Nothing relevant.")
    notes = map_chunks(ctx, src, task, "reading")
    body = reduce_notes(ctx, notes, path.name, f"Answer this question from the notes: {question}", merge_notes)
    return cache_put(ctx, key, f"# {src.title}\n{source_footer(ctx, src)}\n{body}")


def document_digest(ctx: ToolContext, path: Path, pages: str | None = None) -> tuple[str, dict[str, Any]]:
    """-> (full text, digest). Full text: the converted markdown, or for PDFs and images the parsing sub-agent's
    transcription. Digest: {summary, key_insights, key_values, metadata}, by the parsing sub-agent. Cached."""
    key = cache_key(ctx, path, "route", None, pages)
    cache = ctx.state_dir / "cache" / "documents"
    full_f, digest_f = cache / f"{key}.md", cache / f"{key}.json"
    if full_f.is_file() and digest_f.is_file():
        ctx.events.status("document", f"{path.name}: cached result")
        return full_f.read_text(encoding="utf-8"), json.loads(digest_f.read_text(encoding="utf-8"))
    src = load_source(ctx, path, pages)
    if src.kind in ("pdf", "image"):
        notes = map_chunks(ctx, src, TRANSCRIBE_TASK, "transcribing")
        full = f"# {src.title}\n{source_footer(ctx, src)}\n" + "\n\n".join(f"## {span}\n\n{text}" for span, text in notes)
    else:
        full = src.markdown() + ("\n\n" + source_footer(ctx, src) if src.attachments or src.notes else "")
    digest = structured_digest(ctx, full, path.name)
    digest["metadata"] = {"source": rel(ctx, path), "kind": src.kind, "title": src.title, "units": len(src.units),
                          "pages": pages or "", "tokens": tokens(full),        # chars/4; the route scales it
                          "attachments": [rel(ctx, a) for a in src.attachments], "notes": src.notes}
    cache.mkdir(parents=True, exist_ok=True)
    full_f.write_text(full, encoding="utf-8")
    digest_f.write_text(json.dumps(digest, ensure_ascii=False, indent=1), encoding="utf-8")
    return full, digest


def structured_digest(ctx: ToolContext, text: str, name: str) -> dict[str, Any]:
    """The parsing sub-agent's JSON digest of `text`: one reply per part, merged when there are several."""
    src = Source(Path(name), "text", name, split_text(name, text))
    replies = map_chunks(ctx, src, DIGEST_TASK, "digesting", validate=parse_digest)
    final = reduce_notes(ctx, replies, name, "", lambda _t, body: f"{DIGEST_MERGE}\n\n{body}",
                         validate=parse_digest)
    return parse_digest(final)


def parse_digest(text: str) -> dict[str, Any]:
    """Require a complete JSON digest with typed, evidence-addressable values."""
    data = parse_json_object(text)
    if not isinstance(data.get("summary"), str):
        raise ValueError("Document digest summary must be a string.")
    insights = data.get("key_insights")
    if not isinstance(insights, list) or any(not isinstance(item, str) for item in insights):
        raise ValueError("Document digest key_insights must be a list of strings.")
    values = data.get("key_values")
    if not isinstance(values, list) or any(
        not isinstance(item, dict) or any(not isinstance(item.get(key), str)
                                         for key in ("field", "value", "location"))
        for item in values
    ):
        raise ValueError("Document digest key_values must contain field, value and location strings.")
    return {"summary": data["summary"], "key_insights": insights, "key_values": values}


def route_document(ctx: ToolContext, path: Path, pages: str | None = None) -> str:
    """The big-context route for a document: full text + digest in the operation folder; -> the digest text."""
    full, digest = document_digest(ctx, path, pages)
    r = rel(ctx, path)
    also = f"For specific facts with their locations, read {r} with a question" + \
        (", or with pages for a range." if kind_of(path) == "pdf" else ".")
    return store(ctx, folder(ctx), what=f"read(path={r}{f', pages={pages}' if pages else ''})", full=full,
                 source=None, digest=digest, by="parsing sub-agent", size=real_tokens(ctx, full), also=also)


def source_footer(ctx: ToolContext, src: Source) -> str:
    lines = [f"Notes: {n}" for n in src.notes]
    if src.attachments:
        lines.append("Attachments (saved; read them with read): " +
                     ", ".join(rel(ctx, a) for a in src.attachments))
    return ("\n".join(lines) + "\n") if lines else ""


def read_document(ctx: ToolContext, path: Path, question: str | None = None, pages: str | None = None,
                  offset: int | None = None, limit: int | None = None) -> str:
    """What `read` returns for a document (see the module docstring)."""
    kind = kind_of(path)
    if kind in ("pdf", "image"):
        if question:
            return answer(ctx, path, question, pages) + "\n\n[Answered by the parsing sub-agent from the document.]"
        if offset is not None or limit is not None:          # lines of the (cached) transcription
            return page(document_digest(ctx, path, pages)[0], offset, limit, ctx, "the transcription")
        return route_document(ctx, path, pages)
    if pages:
        raise ToolError("pages applies to PDFs only; use offset/limit for lines of the converted text")
    src = load_source(ctx, path)
    text = src.markdown() + ("\n\n" + source_footer(ctx, src) if src.attachments or src.notes else "")
    if offset is not None or limit is not None:
        return page(text, offset, limit, ctx, "the converted text")
    if real_tokens(ctx, text) <= limits(ctx).result:
        note_document(ctx, rel(ctx, path))      # whole and verbatim: the turn rule may still route it
        return text
    if question:
        return answer(ctx, path, question)
    return route_document(ctx, path)


def attach_document(ctx: ToolContext, path: Path, question: str | None = None,
                    label: str | None = None) -> str:
    """A file for the next message: text as is; documents through the same policy as the read tool."""
    if not path.is_file():
        raise ToolError(f"{label or path}: no such file")
    reject_unsupported(path)
    shown = label or rel(ctx, path)
    if path.suffix.lower() in DOC_SUFFIXES:
        body = read_document(ctx, path, question)
    else:
        body = path.read_text(encoding="utf-8", errors="replace")
    return f'<attachment path="{shown}">\n{body}\n</attachment>'


# ---------------------------------------------------------------------- cache
def cache_key(ctx: ToolContext, path: Path, op: str, request: str | None, pages: str | None) -> str:
    s = ctx.settings
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    for part in (CACHE_VERSION, op, ctx.llm.info().id, request or "", pages or "", s.doc_render, str(s.doc_image_px)):
        h.update(b"\0" + part.encode())
    return h.hexdigest()[:32]


def cache_get(ctx: ToolContext, key: str, path: Path) -> str | None:
    f = ctx.state_dir / "cache" / "documents" / f"{key}.md"
    if f.is_file():
        ctx.events.status("document", f"{path.name}: cached result")
        return f.read_text(encoding="utf-8")
    return None


def cache_put(ctx: ToolContext, key: str, text: str) -> str:
    f = ctx.state_dir / "cache" / "documents" / f"{key}.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return text
