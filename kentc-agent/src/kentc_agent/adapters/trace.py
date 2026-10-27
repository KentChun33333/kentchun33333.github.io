"""Operation trace: a per-session JSONL debug log of what the local agent actually did.

One operation = one turn of the agent loop: the context goes to the model, the reply comes back, and its tool
calls run until their results are in the context (end "tool_results"), or the reply is the answer (end "answer").
The session log (session.py) stays the resumable conversation; the trace is for reading behaviour: which context
went in, what came out, which files were touched, how long each part took, where a loop went round again.

<workspace>/.kentc-agent/traces/<session_id>.jsonl - one JSON object per line:

  {"type": "session", "session_id", "agent", "started", "model", "workspace", "session_log", "parent", "system"}
      once, when the trace file is created (the system prompt is not repeated per operation)
  {"type": "operation", "session_id", "operation_id", "run", "turn", "agent", "parent", "started", "ms", "end",
   "error"?,
   "input_context":  {"prompt"? (turn 1 of a run), "messages", "tokens", "density", "window", "summary",
                      "session_ids", "tools", "compactions"},
   "model":          {"id", "effort", "max_tokens", "prompt_tokens", "completion_tokens", "finish", "ms", "retries"},
   "output_context": {"reasoning", "content", "tool_calls": [{"id", "name", "arguments"}],
                      "tool_results": [{"id", "name", "error", "ms", "chars", "result", "routed"?, "safety"?}]},
   "assets":   [{"tool", "access", "path"}]                 files the tool calls touched; access "stored" is a
                                                            big result's operation folder (bigcontext.py)
   "children": [{"session_id", "tool_call_id"}]}            sub-agent sessions started by those tool calls

end: tool_results | answer | max_turns | aborted | error. Rejected output is recorded in model.retries.
`run` counts Agent.run calls in the session (a prompt, a workflow step, a retry), `turn` the operations within it.
A sub-agent's trace has `parent: {session_id, operation_id, tool_call_id}` of the tool call that started it.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ACCESS = {"read": "read", "write": "write", "edit": "write"}


def now_iso() -> str:
    t = time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t)) + f".{int(t % 1 * 1000):03d}"


@dataclass
class OpRef:
    """Where a tool call runs: set on the ToolContext while the tool executes, so a sub-agent started by the tool
    can name its parent and register itself as a child. The tool also leaves notes for the big-context route
    (bigcontext.py): which workspace file holds its full result, or which document it read whole."""
    session_id: str
    operation_id: int
    tool_call_id: str = ""
    children: list[dict[str, str]] = field(default_factory=list)
    source: str = ""                           # workspace file holding this call's full result
    document: str = ""                         # a document read whole and verbatim (route: parsing sub-agent)
    routed: dict[str, Any] | None = None       # set once the result went to the operation folder

    def parent(self) -> dict[str, Any]:
        return {"session_id": self.session_id, "operation_id": self.operation_id, "tool_call_id": self.tool_call_id}


class Operation:
    def __init__(self, session_id: str, operation_id: int, run: int, turn: int, agent: str,
                 parent: OpRef | None) -> None:
        self.ref = OpRef(session_id, operation_id)
        self.t0 = time.monotonic()
        self.record: dict[str, Any] = {
            "type": "operation", "session_id": session_id, "operation_id": operation_id, "run": run, "turn": turn,
            "agent": agent, "parent": parent.parent() if parent else None, "started": now_iso(), "ms": 0, "end": "",
            "input_context": {"compactions": []}, "model": {"retries": []},
            "output_context": {"reasoning": "", "content": "", "tool_calls": [], "tool_results": []},
            "assets": [], "children": self.ref.children}

    @property
    def input(self) -> dict[str, Any]:
        return self.record["input_context"]

    @property
    def model(self) -> dict[str, Any]:
        return self.record["model"]

    @property
    def output(self) -> dict[str, Any]:
        return self.record["output_context"]

    def reply(self, content: str, reasoning: str, tool_calls: list[dict[str, Any]]) -> None:
        calls = []
        for c in tool_calls:
            raw = c["function"]["arguments"] or "{}"
            try:
                args: Any = json.loads(raw)
            except json.JSONDecodeError:
                args = raw                       # kept verbatim: the reply may have been cut off mid-call
            calls.append({"id": c["id"], "name": c["function"]["name"], "arguments": args})
        self.output.update(reasoning=reasoning, content=content, tool_calls=calls)

    def tool_call(self, call_id: str, name: str, args: Any) -> OpRef:
        """Record a tool call about to run; -> the reference to put on the ToolContext meanwhile."""
        if isinstance(args, dict) and isinstance(args.get("path"), str):
            self.record["assets"].append({"tool": name, "access": ACCESS.get(name, "use"), "path": args["path"]})
        return OpRef(self.ref.session_id, self.ref.operation_id, call_id, self.ref.children)

    def tool_result(self, call_id: str, name: str, result: str, error: bool, ms: int,
                    routed: dict[str, Any] | None = None, safety: list[str] | None = None) -> None:
        """`result`: what entered the context; `routed`: {by, tokens, folder} when the big-context route kept the
        full result in the operation folder instead; `safety`: context/safety.py findings on the result."""
        entry = {"id": call_id, "name": name, "error": error, "ms": ms, "chars": len(result), "result": result}
        if routed:
            entry["routed"] = routed
            self.record["assets"].append({"tool": name, "access": "stored", "path": routed["folder"]})
        if safety:
            entry["safety"] = safety
        self.output["tool_results"].append(entry)

    def finish(self, end: str, error: str = "") -> dict[str, Any]:
        self.record["end"] = end
        self.record["ms"] = round((time.monotonic() - self.t0) * 1000)
        if error:
            self.record["error"] = error
        return self.record


class Trace:
    """Appends records to one session's trace file; continues the numbering of a resumed session."""

    def __init__(self, path: Path, session_id: str) -> None:
        self.path, self.session_id = path, session_id
        self.operations = self.runs = 0
        if path.is_file():
            for line in reversed(path.read_text(encoding="utf-8").splitlines()):
                rec = json.loads(line) if line.strip() else {}
                if rec.get("type") == "operation":
                    self.operations, self.runs = rec["operation_id"], rec["run"]
                    break

    @property
    def new(self) -> bool:
        return not self.path.is_file()

    def write(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def next_run(self) -> int:
        self.runs += 1
        return self.runs

    def next_operation(self) -> int:
        self.operations += 1
        return self.operations
