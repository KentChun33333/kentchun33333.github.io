"""Tool execution and turn settlement: run calls, route big results, persist results safely."""

from __future__ import annotations

import json
import signal
import time
from contextlib import contextmanager
from pathlib import Path
from threading import current_thread, main_thread
from typing import Any

from ..adapters.tools import CORE_TOOLS, Tool, ToolError
from ..config import STATE_DIR
from ..context.bigcontext import CallResult, real_tokens, route_turn
from ..context.safety import guard
from ..errors import Aborted


@contextmanager
def _defer_interrupt():
    """Let a short persistence transaction finish before delivering Ctrl-C (never wrap tool execution)."""
    if current_thread() is not main_thread():
        yield
        return
    previous = signal.getsignal(signal.SIGINT)
    if not callable(previous):
        yield
        return
    pending = False

    def interrupted(signum, frame):
        nonlocal pending
        pending = True

    signal.signal(signal.SIGINT, interrupted)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)
        if pending:
            previous(signal.SIGINT, None)


class ToolExecutorMixin:
    """Mixed into Agent; expects ctx, session, tools, name, density and _op."""

    @staticmethod
    def _wire(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Messages as the server takes them (drops bookkeeping keys such as an image part's token estimate)."""
        out = []
        for m in messages:
            if isinstance(m.get("content"), list):
                m = {**m, "content": [{k: v for k, v in p.items() if not k.startswith("_")} for p in m["content"]]}
            out.append(m)
        return out

    def _execute(self, call: dict[str, Any]) -> CallResult:
        """Run one tool call. While it runs, ctx.operation names it, so a sub-agent it starts links back here and
        the tool can leave notes for the big-context route."""
        name = call["function"]["name"]
        try:
            args: Any = json.loads(call["function"]["arguments"] or "{}")
        except json.JSONDecodeError:
            args = None
        op = self._op
        ref = op.tool_call(call["id"], name, args) if op is not None else None
        prev, self.ctx.operation = self.ctx.operation, ref
        self.ctx.density = self.density          # the tool and the router size results in real tokens
        t0 = time.monotonic()
        try:
            result, error = self._tool(name, args)
        finally:
            self.ctx.operation = prev
        return CallResult(call["id"], name, args, result, error, round((time.monotonic() - t0) * 1000), ref)

    def _persist_result(self, r: CallResult, resolved: set[str]) -> None:
        """Append once, keeping persistence and its trace indivisible with respect to Ctrl-C."""
        with _defer_interrupt():
            if r.call_id not in resolved:
                self.session.append({"role": "tool", "tool_call_id": r.call_id, "content": r.text})
                resolved.add(r.call_id)
            if self._op is not None and not any(t["id"] == r.call_id for t in self._op.output["tool_results"]):
                self._op.tool_result(r.call_id, r.name, r.text, r.error, r.ms, r.routed, r.safety)

    def _resolved(self, start: int) -> set[str]:
        return {m["tool_call_id"] for m in self.session.messages[start:] if m["role"] == "tool"}

    def _settle(self, results: list[CallResult], *, start: int) -> None:
        """Route results, check what will enter the context (context/safety.py), then persist; the run's exception
        path repairs any interrupted stage."""
        self.ctx.density = self.density
        route_turn(self.ctx, results)
        if self.ctx.settings.safety_check:
            for r in results:
                r.text, r.safety = guard(r.name, r.text)
                if r.safety:
                    self.ctx.events.status(self.name, f"safety check flagged the {r.name} result: "
                                                      + "; ".join(r.safety[:3]))
        resolved = self._resolved(start)
        for r in results:
            if r.routed:
                self.ctx.events.big_result(self.name, r.name, r.args, r.routed, real_tokens(self.ctx, r.text))
            self._persist_result(r, resolved)

    def _repair(self, calls: list[dict[str, Any]], results: list[CallResult], start: int,
                failure: BaseException) -> None:
        """Resolve every persisted call, without re-running tools, routing, or fallible UI callbacks."""
        by_id = {r.call_id: r for r in results}
        aborted = isinstance(failure, (KeyboardInterrupt, Aborted))
        text = "Aborted by the user." if aborted else \
            f"Error: tool turn failed ({type(failure).__name__}: {failure})."
        with _defer_interrupt():
            resolved = self._resolved(start)
            for call in calls:
                result = by_id.get(call["id"])
                if result is None:
                    result = CallResult(call["id"], call["function"]["name"], None, text, True, 0, None)
                self._persist_result(result, resolved)

    def _tool(self, name: str, args: Any) -> tuple[str, bool]:
        """-> (result for the context, is it an error)."""
        tool = self.tools.get(name)
        if args is None:
            return f"Error: arguments for {name} could not be parsed (invalid JSON). Retry with complete arguments.", True
        if tool is None:
            return f"Error: unknown tool {name!r}. Available: {', '.join(self.tools)}", True
        if not isinstance(args, dict):
            return "Error: arguments must be a JSON object", True
        for key in tool.parameters.get("required", []):
            if key not in args:
                return f"Error: missing argument {key!r}", True
        types = {"string": str, "integer": int, "number": (int, float), "boolean": bool,
                 "object": dict, "array": list, "null": type(None)}
        for key, value in args.items():
            expected = tool.parameters.get("properties", {}).get(key, {}).get("type")
            if expected in types and (not isinstance(value, types[expected]) or
                                      isinstance(value, bool) and expected in ("integer", "number")):
                return f"Error: argument {key!r} must be {expected}. Correct the arguments and retry.", True
        self.ctx.events.tool_start(self.name, name, args)
        error = False
        try:
            result = tool.run(self.ctx, args)
        except ToolError as e:
            result, error = f"Error: {e}", True
        except KeyError as e:
            result, error = f"Error: missing argument {e}", True
        except (OSError, ValueError, RuntimeError) as e:
            result, error = f"Error: {type(e).__name__}: {e}", True
        self.ctx.events.tool_end(self.name, name, result, error)
        return result, error


# ---------------------------------------------------------------------- tool registry
def build_tools(names: list[str] | None, available: dict[str, Tool] | None = None) -> list[Tool]:
    """Tools by name from `available` (default: the core tools; all of them when `names` is None)."""
    available = CORE_TOOLS if available is None else available
    if names is None:
        return list(available.values())
    unknown = [n for n in names if n not in available]
    if unknown:
        raise ValueError(f"unknown tool(s): {', '.join(unknown)}; available: {', '.join(available)}")
    return [available[n] for n in names]


def new_session_path(workspace: Path) -> Path:
    return workspace / STATE_DIR / "sessions" / f"{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
