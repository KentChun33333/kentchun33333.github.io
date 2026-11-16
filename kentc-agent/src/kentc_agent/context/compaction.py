"""Token-aware context compaction (the pi-agent scheme).

When the context passes `window - reserve_tokens`, the oldest messages are summarized into a structured checkpoint
and only the newest ~`keep_recent_tokens` stay verbatim. Cuts land on user or assistant messages, never on a tool
result, so every kept tool result still follows the call that asked for it. A previous summary is updated, not
replaced, so knowledge survives repeated compactions."""

from __future__ import annotations

from typing import Any

from ..adapters.llm import LLMClient
from ..adapters.session import CHARS_PER_TOKEN, estimate_tokens

TOOL_RESULT_CHARS = 2000   # per tool result in the text handed to the summarizer

SYSTEM = ("You are a context summarization assistant. You read a conversation between a user and an AI agent and "
          "write a structured checkpoint another agent will use to continue the work. Do not continue the "
          "conversation and do not answer its questions; only summarize it.")

FORMAT = """## Goal
[What the user is trying to accomplish; several items if the session covers several tasks.]

## Constraints & Preferences
- [Requirements and preferences the user stated. Preserve decisive wording where possible.]

## Completion Requirements
- [Conditions and checks that must hold before the task is complete]

## Progress
### Done
- [x] [Completed work and the check that confirmed it. Leave unverified work in progress.]
### In Progress
- [ ] [Current work]
### Blocked
- [Open problems, if any]

## Evidence
- [Relevant observation, its verification status, and exact source path/range or workspace index ID.]

## Decisions & Exploration
- [Decision and short rationale, failed attempt worth avoiding, or explicitly labeled open hypothesis.]

## Next Steps
1. [What should happen next]

## Critical Context
- [Facts, data, workspace index and artifact paths, function names, numbers and errors needed for the next steps]

Keep each section concise. Preserve exact file paths, identifiers, numbers and error messages.
For saved milestones and evidence, keep useful IDs and refer to the workspace records for details.
Do not treat a proposed check, an assistant claim, or an open hypothesis as verified evidence."""

NEW_PROMPT = ("The conversation above is to be summarized. Create a structured context checkpoint in EXACTLY this "
              "format:\n\n" + FORMAT)

UPDATE_PROMPT = ("The conversation above holds NEW messages. Update the summary in <previous-summary> with them:\n"
                 "- PRESERVE everything still relevant from the previous summary\n"
                 "- ADD new progress, decisions and context\n"
                 "- MOVE items from In Progress to Done when the completion check is confirmed\n"
                 "- UPDATE Next Steps\n\nUse EXACTLY this format:\n\n" + FORMAT)


class CompactionError(RuntimeError):
    pass


def find_cut(messages: list[dict[str, Any]], keep_recent_tokens: int) -> int:
    """Index of the first message to keep verbatim (0: nothing can be summarized).

    Walks back from the newest message until `keep_recent_tokens` are covered, then moves forward to the nearest
    valid cut (a user or assistant message)."""
    valid = [i for i, m in enumerate(messages) if m["role"] in ("user", "assistant") and i > 0]
    if not valid:
        return 0
    acc = 0
    for i in range(len(messages) - 1, -1, -1):
        acc += estimate_tokens(messages[i])
        if acc >= keep_recent_tokens:
            later = [c for c in valid if c >= i]
            return later[0] if later else valid[-1]
    return 0   # everything fits in the recent budget


def serialize(messages: list[dict[str, Any]]) -> str:
    out: list[str] = []
    for m in messages:
        role = m["role"]
        content = m.get("content")
        if isinstance(content, list):
            content = "\n".join(p.get("text", "[image]") if p.get("type") == "text" else "[image]" for p in content)
        content = content or ""
        if role == "user":
            out.append(f"[User]: {content}")
        elif role == "assistant":
            if content:
                out.append(f"[Assistant]: {content}")
            for c in m.get("tool_calls") or []:
                out.append(f"[Assistant tool call]: {c['function']['name']}({c['function']['arguments']})")
        elif role == "tool":
            if len(content) > TOOL_RESULT_CHARS:
                content = content[:TOOL_RESULT_CHARS] + f"\n[... {len(content) - TOOL_RESULT_CHARS} more chars]"
            out.append(f"[Tool result]: {content}")
    return "\n\n".join(out)


def summarize(llm: LLMClient, messages: list[dict[str, Any]], previous: str | None, *, window: int,
              reserve_tokens: int, max_output_tokens: int, effort: str, focus: str | None = None,
              max_words: int = 3000, density: float = 1.0) -> str:
    """Summarize `messages` (updating `previous`) into at most `max_words`. Large histories are folded in chunk by
    chunk; `density` (server tokens per chars/4 token) keeps each chunk inside the window."""
    max_tokens = min(int(0.8 * reserve_tokens), max_output_tokens)
    margin = max(256, window // 20)
    remaining = serialize(messages)
    summary = previous
    while remaining:
        prefix = "<conversation>\n"
        suffix = "\n</conversation>\n\n"
        if summary:
            suffix += f"<previous-summary>\n{summary}\n</previous-summary>\n\n"
        suffix += (UPDATE_PROMPT if summary else NEW_PROMPT) + \
            f"\n\nThe whole checkpoint must stay under {max_words} words: it replaces the conversation above."
        if focus:
            suffix += f"\n\nAdditional focus: {focus}"
        overhead = sum(estimate_tokens(m) for m in [{"content": SYSTEM}, {"content": prefix + suffix}])
        budget = int((window - max_tokens - margin) / density) - overhead - 8
        if budget < 128 or max_tokens <= 0:
            raise CompactionError(f"context window {window} is too small to summarize into")
        end = min(len(remaining), budget * CHARS_PER_TOKEN)
        boundary = remaining.rfind("\n\n", 0, end)
        if end < len(remaining) and boundary > end // 2:
            end = boundary + 2
        prompt = prefix + remaining[:end] + suffix
        remaining = remaining[end:]
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
        reply = llm.chat(messages, max_tokens=max_tokens, effort=effort)
        if reply.finish == "length" or not reply.content:     # thinking used the budget: once more without it
            reply = llm.chat(messages, max_tokens=max_tokens, effort="none")
        if reply.finish == "length" or not reply.content:
            raise CompactionError("summarization was cut off or empty; context left unchanged")
        summary = reply.content
    if summary is None:
        raise CompactionError("nothing to summarize")
    return summary


def shrink_tool_results(messages: list[dict[str, Any]], max_tokens_each: int) -> int:
    """Last resort when even the kept messages overflow: truncate oversized tool results in place."""
    limit = max_tokens_each * CHARS_PER_TOKEN
    n = 0
    for m in messages:
        c = m.get("content")
        if m["role"] == "tool" and isinstance(c, str) and len(c) > limit:
            m["content"] = c[: limit // 2] + f"\n\n[... {len(c) - limit} chars dropped to fit the context ...]\n\n" \
                + c[-limit // 2:]
            n += 1
    return n
