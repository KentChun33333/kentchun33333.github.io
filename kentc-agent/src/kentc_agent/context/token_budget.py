"""Centralized, window-scaled token budget policy for kentc-agent.

All pre-buffer, compaction, safety-margin, and checkpoint-word limits scale
linearly relative to `BASE_WINDOW = 65_536`, with safe floors for small test
windows and upper caps for very large contexts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import Settings

BASE_WINDOW = 65_536
MIN_REPLY_TOKENS = 1024
BASE_CHECKPOINT_WORDS = 600
DEFAULT_RESERVE_TOKENS = 16_384
DEFAULT_KEEP_RECENT_TOKENS = 20_000
DEFAULT_MAX_OUTPUT_TOKENS = 8_192


@dataclass(frozen=True)
class TokenBudget:
    """Computed token & word budgets for a given model `window` and `Settings`."""

    window: int
    scale: float
    reserve_tokens: int
    keep_recent_tokens: int
    safety_margin: int
    checkpoint_max_words: int
    compaction_max_output_tokens: int
    compaction_overhead_tokens: int
    min_reply_tokens: int = MIN_REPLY_TOKENS
    min_preflight_reply_tokens: int = MIN_REPLY_TOKENS // 2


def compute_token_budget(window: int, settings: Settings | None = None) -> TokenBudget:
    """Scale all context pre-buffers linearly from the 65,536-token baseline."""
    w = max(1, int(window))
    scale = w / BASE_WINDOW

    base_reserve = settings.reserve_tokens if settings is not None else DEFAULT_RESERVE_TOKENS
    base_keep = settings.keep_recent_tokens if settings is not None else DEFAULT_KEEP_RECENT_TOKENS
    max_output = settings.max_output_tokens if settings is not None else DEFAULT_MAX_OUTPUT_TOKENS

    # Linearly scale pre-buffers with window size while respecting safe ratio bounds.
    reserve = min(w // 4, max(256, round(base_reserve * scale)))
    keep_recent = min(w // 3, max(512, round(base_keep * scale)))
    safety_margin = max(256, w // 20)
    checkpoint_words = max(300, min(2400, round(BASE_CHECKPOINT_WORDS * scale)))
    compaction_out = min(int(0.8 * reserve), max_output)
    compaction_overhead = max(256, round(256 * max(1.0, scale)))

    return TokenBudget(
        window=w,
        scale=round(scale, 4),
        reserve_tokens=reserve,
        keep_recent_tokens=keep_recent,
        safety_margin=safety_margin,
        checkpoint_max_words=checkpoint_words,
        compaction_max_output_tokens=compaction_out,
        compaction_overhead_tokens=compaction_overhead,
    )
