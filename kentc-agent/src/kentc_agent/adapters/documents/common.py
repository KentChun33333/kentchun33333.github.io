"""Shared document model and small conversion helpers."""

from __future__ import annotations

import base64
import datetime as dt
import mimetypes
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pymupdf

from ..filetypes import DOCUMENT_SUFFIXES, reject_unsupported
from ..session import CHARS_PER_TOKEN, image_tokens

TEXT_RICH_CHARS = 200          # a PDF page with less text is treated as scanned: rendered, not trusted as text
UNIT_TOKENS = 3000             # long text (a Word body, a big sheet) is cut into units of about this size
MAX_SHEET_ROWS = 5000

SUB_SYSTEM = ("You are a document parsing sub-agent. You read document text, tables, e-mails and images and report "
              "faithfully: never invent content, keep exact numbers, names, dates and quotes, mark anything illegible "
              "as [illegible]. Your reply is passed to another agent that cannot see the source, so make it "
              "self-contained. Reply in the source's language unless asked otherwise.")

TRANSCRIBE_TASK = ("Transcribe this material faithfully as clean markdown: all text in reading order, tables as "
                   "markdown tables, and for each figure or image what it shows and its key values. Keep every "
                   "number, amount, date, name and identifier exactly. No preamble, no commentary.")
DIGEST_TASK = ('Reply with ONLY one JSON object (no prose, no code fence) describing this material:\n'
               '{"summary": "3-6 sentences: what it is, who is involved, what it says, the period", '
               '"key_insights": ["up to 8 findings that matter: totals, anomalies, risks, changes, gaps"], '
               '"key_values": [{"field": "name of the value", "value": "exact value as written", '
               '"location": "page / sheet and row / slide / section"}]}\n'
               "At most 25 key values: identifiers, parties, amounts, dates, totals. Exact numbers and names; never "
               "invent.")
DIGEST_MERGE = ("These are JSON digests of consecutive parts of one source. Merge them into ONE JSON object of the "
                "same shape: a summary of the whole source, at most 8 key_insights and 25 key_values (the most "
                "material ones, with their locations). Reply with only the JSON object.")


@dataclass
class Unit:
    """One addressable piece of a document: 'page 3', 'sheet Holdings rows 1-120', 'slide 4', 'email body'."""
    name: str
    text: str
    image: dict[str, Any] | None = None


@dataclass
class Source:
    path: Path
    kind: str
    title: str
    units: list[Unit] = field(default_factory=list)
    attachments: list[Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def markdown(self) -> str:
        parts = [f"# {self.title}"]
        parts += [f"\n## {u.name}\n\n{u.text}" + ("\n\n[image]" if u.image else "") for u in self.units]
        return "\n".join(parts)


@dataclass
class Chunk:
    units: list[Unit] = field(default_factory=list)

    @property
    def span(self) -> str:
        a, b = self.units[0].name, self.units[-1].name
        return a if a == b else f"{a} .. {b}"


def kind_of(path: Path) -> str:
    reject_unsupported(path)
    suffix = path.suffix.lower()
    for kind, suffixes in DOCUMENT_SUFFIXES.items():
        if suffix in suffixes:
            return kind
    if (mimetypes.guess_type(path.name)[0] or "").startswith("image/"):
        return "image"
    return "text"


def image_part(data: bytes, mime: str, tokens: int) -> dict[str, Any]:
    url = f"data:{mime};base64,{base64.b64encode(data).decode()}"
    return {"type": "image_url", "image_url": {"url": url}, "_tokens": tokens}


def render(page: pymupdf.Page, max_px: int) -> dict[str, Any]:
    zoom = min(3.0, max_px / max(page.rect.width, page.rect.height))
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    return image_part(pix.tobytes("png"), "image/png", image_tokens(pix.width, pix.height))


def load_image(data: bytes, name: str, max_px: int) -> dict[str, Any]:
    """PNG at most `max_px` on its longest side; formats MuPDF cannot open go as they are (the server converts)."""
    try:
        with pymupdf.open(stream=data, filetype=Path(name).suffix.lstrip(".") or "png") as doc:
            return render(doc[0], max_px)
    except (pymupdf.FileDataError, RuntimeError, ValueError):
        return image_part(data, mimetypes.guess_type(name)[0] or "image/png", 1500)


def cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dt.datetime):
        return value.isoformat(sep=" ", timespec="minutes") if value.time() != dt.time() else value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def table_markdown(rows: list[list[str]], first_row: int = 1) -> str:
    """Rows with a leading row-number column so evidence can cite 'row 12'."""
    width = max((len(r) for r in rows), default=0)
    lines = []
    for i, r in enumerate(rows):
        lines.append(f"| {first_row + i} | " + " | ".join(r + [""] * (width - len(r))) + " |")
        if i == 0:
            lines.append("|---|" + "---|" * width)
    return "\n".join(lines)


def split_text(prefix: str, text: str, max_tokens: int = UNIT_TOKENS) -> list[Unit]:
    """Long text -> units on line boundaries ('body (part 2/5)')."""
    limit = max_tokens * CHARS_PER_TOKEN
    if len(text) <= limit:
        return [Unit(prefix, text)]
    parts, cur = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(line[:limit])
            line = line[limit:]
        if len(cur) + len(line) + 1 > limit and cur:
            parts.append(cur)
            cur = ""
        cur = f"{cur}\n{line}" if cur else line
    if cur:
        parts.append(cur)
    return [Unit(f"{prefix} (part {i}/{len(parts)})", p) for i, p in enumerate(parts, 1)]


def html_text(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "head"]):
        tag.decompose()
    text = soup.get_text("\n")
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()
