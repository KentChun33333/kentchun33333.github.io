from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from kentc_agent.agent import Events
from kentc_agent.config import Settings
from kentc_agent.adapters.llm import ModelInfo, Reply, Usage
from kentc_agent.adapters.tools import ToolContext


def call(name: str, args: str, cid: str = "c1") -> dict[str, Any]:
    return {"id": cid, "type": "function", "function": {"name": name, "arguments": args}}


class FakeLLM:
    """Scripted model: `script(messages, tools)` returns the next Reply. Records every request."""

    def __init__(self, script: Callable[[list[dict[str, Any]], Any], Reply], window: int = 4000) -> None:
        self.script = script
        self.requests: list[dict[str, Any]] = []
        self._info = ModelInfo("fake", window, True)

    def info(self, *, refresh: bool = False) -> ModelInfo:
        return self._info

    def chat(self, messages, *, tools=None, max_tokens, effort=None, on_delta=None) -> Reply:
        self.requests.append({"messages": messages, "tools": tools, "max_tokens": max_tokens})
        reply = self.script(messages, tools)
        if reply.usage is None:
            prompt = sum(len(str(m.get("content"))) for m in messages) // 4
            reply.usage = Usage(prompt, 10)
        return reply


class RecordingEvents(Events):
    def __init__(self) -> None:
        self.log: list[tuple[str, ...]] = []

    def compaction(self, agent, before, after):
        self.log.append(("compaction", agent, before, after))

    def status(self, agent, text):
        self.log.append(("status", agent, text))


@pytest.fixture
def make_ctx(tmp_path: Path):
    def make(llm: FakeLLM, **settings: Any) -> ToolContext:
        return ToolContext(tmp_path, Settings(**settings), llm, RecordingEvents())  # type: ignore[arg-type]
    return make
