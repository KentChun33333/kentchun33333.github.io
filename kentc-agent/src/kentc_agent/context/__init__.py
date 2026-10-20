"""Context management: token-aware compaction and big-result routing."""

from .bigcontext import CallResult, Limits, limits, real_tokens, route_text, route_turn, tokens
from .compaction import CompactionError, find_cut, serialize, shrink_tool_results, summarize

__all__ = [
    "CallResult",
    "CompactionError",
    "Limits",
    "find_cut",
    "limits",
    "real_tokens",
    "route_text",
    "route_turn",
    "serialize",
    "shrink_tool_results",
    "summarize",
    "tokens",
]
