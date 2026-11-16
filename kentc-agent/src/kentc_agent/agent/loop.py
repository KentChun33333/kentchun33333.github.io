"""The agent loop: prompt -> (model call -> tool calls -> results)* -> answer.

Context controls live beside the loop: vertical compaction in budget.py (context/compaction.py), horizontal
big-result routing in executor.py (context/bigcontext.py), and the safety check on every tool result in
executor.py (context/safety.py).
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..adapters.llm import ContextOverflow, IncompleteReply, LLMError, Reply
from ..adapters.session import Session, estimate_tokens, loggable
from ..adapters.tools import CORE_TOOLS, Tool, ToolContext
from ..adapters.trace import Operation, Trace
from ..context.bigcontext import CallResult, limits
from ..context.memory import WorkspaceMemory
from ..context.task_state import milestone_dir
from ..errors import Aborted
from .budget import BudgetMixin
from .executor import ToolExecutorMixin, _defer_interrupt

MIN_REPLY_TOKENS = 1024
FILE_CHUNK_HINT = "\nFor long files, target at most {tokens:{width}d} estimated tokens of new text per write or edit turn."
FILE_RETRY = (
    "If the requested deliverable is a file, keep the sections already saved. Create a short skeleton if needed, "
    "then send one smaller, complete write or edit call for the next section. Wait for the tool result before "
    "continuing in another turn."
)

BASE_PROMPT = """You are kentc-agent, a capable general-purpose agent running on a local model. You complete the \
user's task by thinking briefly, calling tools, checking results, and answering.

Workspace: {workspace} (relative paths resolve here; writes must stay inside it)
Date: {date}

Guidelines:
- Inspect before acting: look with bash (ls, find, rg -n / grep -rn) and read files rather than guessing. Read only
  the parts you need (offset/limit).
- Large tool results (a big file, long command output, many matches, or a turn whose results add up to too much)
  are stored, not shown: you get a digest (summary, key insights, key values, metadata) and the path of the full
  text. Reason from the digest first; read the stored text with offset/limit or search it with bash only for what
  you need.
- Documents: read handles Word, Excel, CSV, PowerPoint, e-mail (.eml/.msg) and HTML. Small ones come back as
  converted text. PDFs, images and large documents are read by a parsing sub-agent in its own session; ask it a
  precise question (read with question) to get specific facts with their locations. Never dump documents
  yourself with bash (pdftotext, unzip, python libraries). E-mail attachments are saved and listed; read them the
  same way. Video is not supported.
- Separate what a document states from what you infer; cite the file and location for every material fact.
- Compute every total and ratio with bash (python3 -c '...'); never do arithmetic in your head.
- Change files with edit (exact, unique old_text); use write for new files or full rewrites.
- For a long file and when write and edit are available, create a short skeleton with unique section markers.
  Fill one section per model turn using edit. Split long sections and keep a marker for the next piece.
  Wait for each tool result, preserve completed sections, and verify the assembled file before replying.
- Verify your work when possible (run it, test it, re-read the result).
- Your context is limited and older turns get summarized: note key facts in your replies, keep tool output small.
- The runtime supplies current context usage, remaining capacity, tool-result limits, and a workspace index.
  Use that index to recover exact evidence after compaction. Read small windows or search stored files.
  When capacity is low, finish the current step, save useful findings to a file, and avoid bulk reads.
- When finished, reply with the final answer and no tool call. Be concise and concrete."""


def load_agents_md(workspace: Path) -> str:
    for name in ("AGENTS.md", "CLAUDE.md"):
        p = workspace / name
        if p.is_file():
            return f"\n\n# Project instructions ({name})\n\n{p.read_text(encoding='utf-8')[:20000]}"
    return ""


class Agent(BudgetMixin, ToolExecutorMixin):
    include_workspace_instructions = True

    def __init__(self, ctx: ToolContext, *, tools: list[Tool], session: Session | None = None,
                 instructions: str = "", name: str = "main", effort: str | None = None,
                 max_turns: int | None = None, system: str | None = None) -> None:
        """`system`: the whole system prompt, verbatim (no base prompt or AGENTS.md); for the parsing sub-agent."""
        self.ctx = ctx
        self.session = session or Session()
        self.name = name
        self.effort = effort
        self.max_turns = ctx.settings.max_turns if max_turns is None else max_turns   # 0: no limit
        self.system = system if system is not None else self._system_prompt(instructions)
        self.context_feedback = system is None  # fixed document/screening protocols keep their exact prompts
        self.memory = WorkspaceMemory(ctx.workspace, self.session.id)
        self.workflow_status = ""
        self.set_tools(tools)
        self.parent = ctx.operation              # set when a tool call starts this agent (a parsing sub-agent)
        if self.parent is not None:
            self.parent.children.append({"session_id": self.session.id, "tool_call_id": self.parent.tool_call_id})
        self.trace = Trace(ctx.state_dir / "traces" / f"{self.session.id}.jsonl", self.session.id) \
            if ctx.settings.trace and self.session.path is not None else None
        self._op: Operation | None = None        # the operation in progress
        self.density = 1.0                       # server tokens per chars/4 token, learned from the server's counts
        ops = ctx.state_dir / "operations" / self.session.id   # numbering when there is no trace to continue from
        self._op_seq = max((int(p.name) for p in ops.iterdir() if p.name.isdigit()), default=0) \
            if ops.is_dir() else 0
        self.last_finish: str | None = None      # latest model finish in this run; run() still returns text
        self.stopped: str | None = None          # "max_turns" when the latest run ended without a final answer
        self.turns = 0                           # model calls in the latest run
        self.output_retries = ctx.settings.output_retries
        self.validate_reply: Callable[[str], Any] | None = None

    def set_tools(self, tools: list[Tool]) -> None:
        """The tools offered from the next model call on (a workflow step narrows them; the context stays)."""
        self.tools = {t.name: t for t in tools}
        self.tool_schemas = [t.schema() for t in tools]
        self.fixed_tokens = estimate_tokens({"content": self.system}) + \
            estimate_tokens({"content": json.dumps(self.tool_schemas)})

    def _system_prompt(self, instructions: str) -> str:
        # tools are described by their schemas, not here: the prompt stays the same when a workflow step changes them
        text = BASE_PROMPT.format(workspace=self.ctx.workspace, date=time.strftime("%Y-%m-%d"))
        if self.include_workspace_instructions:
            text += load_agents_md(self.ctx.workspace)
        if instructions:
            text += f"\n\n# Instructions\n\n{instructions}"
        return text

    # ------------------------------------------------------------------ the loop
    def run(self, prompt: str | list[dict[str, Any]]) -> str:
        """One prompt to an answer. Each turn of the loop is one operation in the trace."""
        self.last_finish, self.stopped, self.turns = None, None, 0
        self.ctx.llm.info(refresh=True)
        self.session.append({"role": "user", "content": self._prepare_prompt(prompt)})
        run = self.trace.next_run() if self.trace else 0
        reply = Reply()
        try:
            while not self.max_turns or self.turns < self.max_turns:
                self.turns += 1
                turn = self.turns
                op = self._begin(run, turn, prompt)
                calls: list[dict[str, Any]] = []
                results: list[CallResult] = []
                start = len(self.session.messages)
                try:
                    reply = self._call()
                    start = len(self.session.messages)
                    self.last_finish = reply.finish
                    with _defer_interrupt():
                        self.session.append(reply.message(), reply.usage)
                        calls = reply.tool_calls
                        op.reply(reply.content, reply.reasoning, calls)
                    self.ctx.events.turn_end(self.name, self.context_tokens(), self.window)
                    if not reply.tool_calls:
                        self._end("answer")
                        return reply.content
                    for call in calls:
                        results.append(self._execute(call))
                    self._settle(results, start=start)
                    self._end("max_turns" if self.turns == self.max_turns else "tool_results")
                except BaseException as e:
                    if calls:
                        self._repair(calls, results, start, e)
                    if self._op is not None:
                        aborted = isinstance(e, (KeyboardInterrupt, Aborted))
                        self._end("aborted" if aborted else "error", "" if aborted else f"{type(e).__name__}: {e}")
                    raise
            self.stopped = "max_turns"
            return (reply.content + "\n\n" if reply.content else "") + \
                f"[Stopped after {self.max_turns} model calls without a final answer.]"
        except (KeyboardInterrupt, Aborted):
            raise Aborted() from None

    def _prepare_prompt(self, prompt: str | list[dict[str, Any]]) -> str | list[dict[str, Any]]:
        """Keep oversized text inputs in the workspace when this agent can retrieve them."""
        if not self.context_feedback or not ({"read", "bash"} & self.tools.keys()):
            return prompt
        threshold = max(512, min(self.ctx.settings.big_turn_tokens, self.window // 5))

        def prepare(text: str) -> str:
            size = math.ceil(estimate_tokens({"content": text}) * self.density)
            if size <= threshold:
                return text
            entry = self.memory.archive(text, kind="input", tokens=size, source=f"user message {self.session.next_id}")
            preview = max(128, int(threshold / self.density))
            return (f"[Large user input stored in {entry['path']}; ~{size} tokens. "
                    "Read or search the full input before answering; this preview has incomplete coverage.]\n"
                    f"{text[:preview]}\n[... full input is in the workspace ...]\n{text[-preview:]}")

        if isinstance(prompt, str):
            return prepare(prompt)
        return [{**part, "text": prepare(part["text"])} if part.get("type") == "text" else part
                for part in prompt]

    # ------------------------------------------------------------------ trace
    def _begin(self, run: int, turn: int, prompt: str | list[dict[str, Any]]) -> Operation:
        op = Operation(self.session.id, self._next_operation(), run, turn, self.name, self.parent)
        if turn == 1:
            op.input["prompt"] = loggable({"content": prompt})["content"]
        self._op = op
        return op

    def _end(self, end: str, error: str = "") -> None:
        op, self._op = self._op, None
        if op is None:
            return
        record = op.finish(end, error)
        if self.trace is None:
            return
        if self.trace.new:
            self.trace.write({"type": "session", "session_id": self.session.id, "agent": self.name,
                              "started": record["started"], "model": record["model"].get("id", ""),
                              "workspace": str(self.ctx.workspace), "session_log": str(self.session.path),
                              "parent": self.parent.parent() if self.parent else None,
                              "max_turns": self.max_turns, "system": self.system})
        self.trace.write(record)

    def _next_operation(self) -> int:
        if self.trace is not None:
            return self.trace.next_operation()
        self._op_seq += 1
        return self._op_seq

    def _call(self) -> Reply:
        on_delta = (lambda kind, text: self.ctx.events.delta(self.name, kind, text))
        op = self._op
        overflows, empty = 0, False
        cap: int | None = None                   # after a server overflow: the max_tokens the server said fits
        rejected = 0
        correction = ""
        preflight_compacted = False
        file_chunk_divisor = 4
        incremental_writes = self.context_feedback and all(
            self.tools.get(name) is CORE_TOOLS[name] for name in ("write", "edit")
        )

        def retry_invalid(problem: str, *, split_file: bool = False) -> None:
            nonlocal rejected, correction, file_chunk_divisor
            if rejected >= self.output_retries:
                raise IncompleteReply(problem)
            if self.max_turns and self.turns >= self.max_turns:
                raise IncompleteReply(f"model-call budget exhausted: {problem}")
            self.turns += 1
            rejected += 1
            correction = (f"The previous attempt was rejected and was not added to the conversation ({problem}). "
                          "Continue from the accepted conversation and original evidence, obey all output requirements and checks, "
                          "and return one complete response within the output budget. Do not continue a partial reply.")
            if incremental_writes and split_file:
                file_chunk_divisor *= 2
                correction += " " + FILE_RETRY
            self.ctx.events.status(self.name, f"discarding invalid output; clean retry {rejected}: {problem}")
            if op is not None:
                op.model["retries"].append(f"invalid output: {problem}")

        while True:
            self._try_compact()
            if self.room() < MIN_REPLY_TOKENS:
                self._try_compact(force=True)
            context = self.session.context()
            max_tokens = max(MIN_REPLY_TOKENS // 2, min(self.ctx.settings.max_output_tokens, self.room()))
            if cap is not None:
                max_tokens = min(max_tokens, cap)
            chunk_tokens = max_tokens // file_chunk_divisor
            hint_width = len(str(chunk_tokens))
            if self.context_feedback:
                self.ctx.available_context_tokens = max(128, self.room() - self.reserve)
            lim = limits(self.ctx)
            if self.context_feedback:
                feedback = self.memory.notice(used=self.context_tokens() + self.feedback_reserve,
                                              window=self.window, reserve=self.reserve,
                                              reply=min(self.ctx.settings.max_output_tokens, max(0, self.room())),
                                              result_limit=lim.result, turn_limit=lim.turn,
                                              compactions=self.session.compactions)
                if self.workflow_status:
                    feedback += "\n" + self.workflow_status
                milestones = milestone_dir(self.memory)
                if milestones.is_dir():
                    feedback += f"\nSaved milestones: {self.memory.relative(milestones)}."
                    if "task_state" in self.tools:
                        feedback += " Use task_state with action=show to recover completion criteria and evidence IDs."
                hint = FILE_CHUNK_HINT.format(tokens=chunk_tokens, width=hint_width) \
                    if incremental_writes and chunk_tokens else ""
                context = [{"role": "user", "content": feedback + hint}] + context
            prompt_estimate = math.ceil((self.fixed_tokens + sum(estimate_tokens(m) for m in context) +
                                        (estimate_tokens({"content": correction}) if correction else 0)) * self.density)
            available = self.window - prompt_estimate - max(256, self.window // 20)
            if available < MIN_REPLY_TOKENS // 2:
                if not preflight_compacted:
                    preflight_compacted = True
                    self._try_compact(force=True)
                    continue
                raise ContextOverflow(f"context needs ~{prompt_estimate} prompt tokens, leaving insufficient reply "
                                      f"room in the {self.window}-token window; reduce fixed instructions or input")
            max_tokens = min(max_tokens, available)
            if incremental_writes:
                # Padding to the original width preserves the conservative preflight estimate.
                chunk_tokens = max_tokens // file_chunk_divisor
                hint = FILE_CHUNK_HINT.format(tokens=chunk_tokens, width=hint_width) if chunk_tokens else ""
                context[0]["content"] = feedback + hint
            messages = [{"role": "system", "content": self.system}] + self._wire(context)
            if correction:
                messages.append({"role": "user", "content": correction})
            counted, estimated = self.session.token_parts(self.fixed_tokens)
            if op is not None:
                op.input.update(messages=len(context), tokens=self.context_tokens(), density=round(self.density, 3),
                                window=self.window, summary=self.session.summary is not None, tools=list(self.tools),
                                session_ids=[self.session.ids[0], self.session.ids[-1]] if self.session.ids else [])
                op.input.update(estimated_prompt_tokens=prompt_estimate,
                                remaining_tokens=max(0, self.window - prompt_estimate - max_tokens),
                                memory_index=self.memory.relative(self.memory.index),
                                compaction_count=self.session.compactions)
                op.model.update(id=self.ctx.llm.info().id, effort=self.effort or self.ctx.settings.reasoning_effort,
                                max_tokens=max_tokens)
            t0 = time.monotonic()
            try:
                self.ctx.events.model_request(self.name, messages, prompt_tokens=prompt_estimate,
                                              max_tokens=max_tokens)
                reply = self.ctx.llm.chat(messages, tools=self.tool_schemas or None, effort=self.effort,
                                          max_tokens=max_tokens, on_delta=on_delta)
            except IncompleteReply as e:
                retry_invalid(str(e), split_file=True)
                continue
            except ContextOverflow as e:
                self.ctx.llm.info(refresh=True)
                overflows += 1
                self._calibrate(counted, estimated, e.prompt_tokens)
                if overflows > 2:
                    raise
                real = f"prompt {e.prompt_tokens:,} tokens, estimated {self.context_tokens():,}" \
                    if e.prompt_tokens else "prompt size not reported"
                if overflows == 1 and not e.prompt_too_long and (e.fit is None or e.fit - 16 >= MIN_REPLY_TOKENS // 2):
                    cap = e.fit - 16 if e.fit is not None else max(MIN_REPLY_TOKENS // 2, max_tokens // 2)
                    what = f"retrying with max_tokens {cap:,}" + (" (the server's limit)" if e.fit else "")
                else:
                    cap, what = None, "compacting"
                self.ctx.events.status(self.name, f"server reported a context overflow ({real}); {what}")
                if op is not None:
                    op.model["retries"].append(f"context overflow: {what} | server: {e}")
                if cap is None:
                    self._try_compact(force=True)
                continue
            self._calibrate(counted, estimated, reply.usage.prompt_tokens if reply.usage else None)
            if op is not None:
                u = reply.usage
                op.model.update(prompt_tokens=u.prompt_tokens if u else None,
                                completion_tokens=u.completion_tokens if u else None, finish=reply.finish,
                                ms=round((time.monotonic() - t0) * 1000))
            problem = ""
            split_file = reply.finish == "length"
            if reply.finish and reply.finish not in ("stop", "tool_calls", "length"):
                raise LLMError(f"response did not finish normally (finish={reply.finish!r})")
            if reply.finish == "length":
                problem = "The reply hit max_output_tokens; generate a complete response within the output budget."
            else:
                try:
                    for call in reply.tool_calls:
                        fn = call["function"]
                        split_file = fn.get("name") in ("write", "edit")
                        if not fn.get("name") or not isinstance(json.loads(fn.get("arguments") or "{}"), dict):
                            raise ValueError("tool arguments must be one complete JSON object with a function name")
                    split_file = False
                    if not reply.tool_calls and self.validate_reply is not None:
                        if reply.finish != "stop":
                            raise LLMError(f"structured response did not finish normally (finish={reply.finish!r})")
                        self.validate_reply(reply.content)
                except (ValueError, KeyError, TypeError) as e:
                    problem = f"The response failed validation: {e}"
            if problem:
                retry_invalid(problem, split_file=split_file)
                continue
            if reply.content or reply.tool_calls or empty:
                return reply
            empty = True                         # an empty turn (ended inside its thinking): ask once more
            self.ctx.events.status(self.name, "empty reply; retrying")
            if op is not None:
                op.model["retries"].append("empty reply: asked again")
