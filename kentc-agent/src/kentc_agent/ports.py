"""Ports between the agent core and its adapters.

The core depends on these protocols, never on a concrete LLM client, UI, or persistence layer.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from .adapters.llm import ModelInfo, Reply


class LLM(Protocol):
    def info(self, *, refresh: bool = False) -> ModelInfo: ...

    def chat(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None,
             max_tokens: int, effort: str | None = None,
             on_delta: Callable[[str, str], None] | None = None) -> Reply: ...


class Events:
    """UI hooks. `agent` names the context speaking: "main", "document" (a parsing sub-agent) or a workflow step."""

    def delta(self, agent: str, kind: str, text: str) -> None: ...
    def tool_start(self, agent: str, name: str, args: dict[str, Any]) -> None: ...
    def tool_end(self, agent: str, name: str, result: str, error: bool) -> None: ...
    def compaction(self, agent: str, before: int, after: int) -> None: ...
    def big_result(self, agent: str, tool: str, args: Any, routed: dict[str, Any], shown: int) -> None:
        """A tool result went to the operation folder (context/bigcontext.py). `routed`: {by, tokens, folder,
        rule}; `shown`: tokens of the digest that entered the context instead."""
    def status(self, agent: str, text: str) -> None: ...
    def turn_end(self, agent: str, tokens: int, window: int) -> None: ...
