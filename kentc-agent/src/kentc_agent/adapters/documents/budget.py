"""Document request budgeting, chunking, and map/reduce parsing sub-agent calls."""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ...errors import ToolError
from ..session import estimate_tokens
from ..tools import ToolContext
from .common import SUB_SYSTEM, TRANSCRIBE_TASK, Chunk, Source, Unit


@dataclass(frozen=True)
class DocumentBudget:
    """A single-shot envelope, in real tokens; document chunk size is only a policy ceiling."""
    input_tokens: int
    output_tokens: int
    density: float
    chunk_tokens: int

    def fits(self, parts: list[dict[str, Any]], *, transcribe: bool = False) -> bool:
        user = estimate_tokens({"content": parts})
        fixed = estimate_tokens({"content": SUB_SYSTEM}) + estimate_tokens({"content": "[]"})
        if math.ceil((fixed + user) * self.density) > self.input_tokens:
            return False
        if user > self.chunk_tokens:
            return False
        # Markdown transcription can expand the source. Images have no known text length: reserve their
        # estimated size too, and reject a length-finished reply rather than claiming it is complete.
        return not transcribe or math.ceil(user * self.density * 1.25) <= self.output_tokens


def document_budget(ctx: ToolContext) -> DocumentBudget:
    from ...agent import MIN_REPLY_TOKENS
    s = ctx.settings
    window = ctx.llm.info(refresh=True).context_window
    if window <= 0:
        raise ToolError("The server did not report a usable document context window.")
    output = min(s.max_output_tokens, window // 2)
    # Leave the Agent's compaction/minimum-reply thresholds untouched: a document request must not
    # trigger history summarization, which would replace evidence before it is read.
    margin = max(256, window // 20)  # Agent.room()'s estimate safety margin
    reserve = max(max(output, MIN_REPLY_TOKENS) + margin, min(s.reserve_tokens, window // 4))
    budget = DocumentBudget(window - reserve, output, max(1.0, ctx.density), s.doc_chunk_tokens)
    if output <= 0 or not budget.fits([{"type": "text", "text": ""}]):
        raise ToolError("The inspected context window is too small for a document request and its reply.")
    return budget


def ask(ctx: ToolContext, parts: list[dict[str, Any]], label: str) -> str:
    """One sub-agent: same model, a new session of its own (logged), no tools, one reply."""
    from ...agent import Agent
    ctx.events.status("document", label)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", label)[:60].strip("-")
    session = _new_session()
    session.path = ctx.state_dir / "subagents" / f"{session.id}-doc-{slug}.jsonl"   # unique: one log per call
    agent = Agent(ctx, tools=[], session=session, system=SUB_SYSTEM, name="document",
                  effort=ctx.settings.sub_effort, max_turns=1)
    agent.density = max(1.0, ctx.density)
    result = agent.run(parts)
    if agent.last_finish == "length":
        raise ToolError(f"{label}: document reply hit max_output_tokens; incomplete content was not cached. "
                        "Use a smaller page range or increase max_output_tokens.")
    if agent.last_finish != "stop":
        raise ToolError(f"{label}: document reply did not complete (finish={agent.last_finish!r}); "
                        "incomplete content was not cached.")
    return result


def _new_session():
    from ..session import Session
    return Session()


def chunk_parts(src: Source, c: Chunk, n: int, total: int, task: str) -> list[dict[str, Any]]:
    head = f"Source: {src.title}. Part {n} of {total}: {c.span}."
    if src.notes:
        head += "\nNotes: " + "; ".join(src.notes)
    parts: list[dict[str, Any]] = [{"type": "text", "text": f"{head}\n\nTask: {task}"}]
    for u in c.units:
        parts.append({"type": "text", "text": f"\n--- {u.name} ---\n{u.text}" if u.text else f"\n--- {u.name} ---"})
        if u.image:
            parts.append(u.image)
    return parts


def map_chunks(ctx: ToolContext, src: Source, task: str, verb: str) -> list[tuple[str, str]]:
    budget = document_budget(ctx)
    transcribe = task == TRANSCRIBE_TASK
    # The character count bounds the eventual number of chunks, including splits, so even the
    # widest Part n/total header is accounted for before any request is sent.
    total_bound = sum(max(1, len(u.text)) for u in src.units) or 1

    def fits(units: list[Unit]) -> bool:
        c = Chunk(units)
        return sum(u.image is not None for u in units) <= ctx.settings.doc_max_images and \
            budget.fits(chunk_parts(src, c, total_bound, total_bound, task), transcribe=transcribe)

    units: list[Unit] = []
    for unit in src.units:
        if fits([unit]):
            units.append(unit)
            continue
        # Keep an image with its page's first text part. Never drop or resize an oversized image
        # silently: its evidence cannot be split safely by the text chunker.
        if unit.image and not fits([Unit(unit.name, "", unit.image)]):
            raise ToolError(f"{unit.name}: image exceeds the inspected document input/output budget; "
                            "use a larger context/output limit or a smaller doc_image_px.")
        remaining, first, number = unit.text, True, 1
        pieces: list[Unit] = []
        while remaining:
            label = f"{unit.name} (part {number}/{max(1, len(unit.text))})"
            image = unit.image if first else None
            low, high = 0, len(remaining)
            while low < high:
                mid = (low + high + 1) // 2
                if fits([Unit(label, remaining[:mid], image)]):
                    low = mid
                else:
                    high = mid - 1
            if low == 0:
                raise ToolError(f"{unit.name}: document prompt leaves no room for source text.")
            # Retain every character, including the boundary newline.
            cut = remaining.rfind("\n", 0, low) + 1
            if cut == 0:
                cut = low
            pieces.append(Unit(label, remaining[:cut], image))
            remaining, first, number = remaining[cut:], False, number + 1
        for i, piece in enumerate(pieces, 1):
            piece.name = f"{unit.name} (part {i}/{len(pieces)})"
        units.extend(pieces)
        if not unit.text:
            raise ToolError(f"{unit.name}: document unit exceeds the inspected request budget.")

    chunks: list[Chunk] = []
    for unit in units:
        if not chunks or not fits([*chunks[-1].units, unit]):
            chunks.append(Chunk())
        chunks[-1].units.append(unit)
    return [(c.span, ask(ctx, chunk_parts(src, c, i, len(chunks), task),
                         f"{src.path.name}: {verb} {c.span} ({i}/{len(chunks)})"))
            for i, c in enumerate(chunks, 1)]


def reduce_notes(ctx: ToolContext, notes: list[tuple[str, str]], name: str, task: str,
                 merge: Callable[[str, str], str]) -> str:
    """Fold consecutive results only when their complete labeled evidence fits."""
    if not notes:
        return ""
    budget = document_budget(ctx)

    def parts(group: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = "\n\n".join(f"## From {label}\n{text}" for label, text in group)
        return [{"type": "text", "text": merge(task, body)}]

    while len(notes) > 1:
        groups: list[list[tuple[str, str]]] = []
        for note in notes:
            if not budget.fits(parts([note])):
                raise ToolError(f"{name}: notes from {note[0]} exceed the inspected reduction budget; "
                                "cannot merge without losing evidence.")
            if groups and budget.fits(parts([*groups[-1], note])):
                groups[-1].append(note)
            else:
                groups.append([note])
        if len(groups) == len(notes):
            raise ToolError(f"{name}: no pair of notes fits the inspected reduction budget; "
                            "cannot reduce further without losing evidence.")
        merged = []
        for group in groups:
            if len(group) == 1:
                merged.append(group[0])
                continue
            span = f"{group[0][0]} .. {group[-1][0]}"
            merged.append((span, ask(ctx, parts(group), f"{name}: merging ({span})")))
        notes = merged
    return notes[0][1]


def merge_notes(task: str, body: str) -> str:
    return ("These are notes taken from consecutive parts of one source. Merge them into one coherent result for "
            "this task, keeping every relevant fact, number, date and location reference, dropping repetition and "
            f"'nothing relevant' notes.\n\nTask: {task}\n\n{body}")
