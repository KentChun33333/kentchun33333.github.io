"""Persistent chat, request inspection, and live events for one local workspace."""

from __future__ import annotations

import json
import logging
import math
import time
from collections import deque
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from threading import Condition, Event, Lock, Thread
from typing import Any

from kentc_agent.adapters.llm import LLMError, ModelInfo
from kentc_agent.adapters.session import SUMMARY_PREFIX, Session, estimate_tokens
from kentc_agent.adapters.tools import ToolContext
from kentc_agent.agent import Aborted
from kentc_agent.config import STATE_DIR, Settings
from kentc_agent.context.compaction import CompactionError
from kentc_agent.ports import Events, LLM
from kentc_agent.workflow import NeedsAnswer, Workflow, WorkflowError, resolve_inputs

from .markdown import render_markdown
from .profiles import WorkspaceRunner
from .workspace import TOOLS, WorkspaceAgent, atomic_text

logger = logging.getLogger(__name__)
PREVIEW_CHARS = 900
INSTRUCTIONS = (
    "You are serving a chat in Kent WebIO. Use list_files to explore folders and read for source evidence. "
    "The user can attach workspace paths to a message. For PDFs, begin with read_pdf_text to inspect embedded "
    "text and cite page numbers. Use read with a focused question and page range for scans, figures, or layout. "
    "Use the other file tools to inspect and update workspace files. "
    "Use write and edit for requested workspace changes and tell the user the output paths. "
    "When producing HTML deliverables, embed styles, scripts, and visualization data or use relative workspace "
    "assets so the files render in the Output viewer."
)
WAITING = " · waiting for model"
RESPONDING = " · model responding"
TOOL_STATUS = {
    "list_files": "Listing workspace files",
    "read": "Reading file",
    "read_pdf_text": "Reading PDF text",
    "write": "Writing file",
    "edit": "Updating file",
}


def rendered_message(record: dict[str, Any]) -> dict[str, Any]:
    return {**record, "markdown_html": render_markdown(record["text"])}


def context_entries(agent: WorkspaceAgent, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for message in messages:
        role = message["role"]
        content = message.get("content") or ""
        if isinstance(content, list):
            content = "\n".join(part.get("text", "[Image]") for part in content)
        if role == "user":
            if content.startswith(SUMMARY_PREFIX):
                role = "checkpoint"
            elif content.startswith("[Runtime context status;"):
                role = "runtime"
            elif content.startswith("My active requirements for this session"):
                role = "requirements"
        for call in message.get("tool_calls") or []:
            function = call["function"]
            content += f"\n{function['name']}({function['arguments']})"
        if not content and message.get("reasoning_content"):
            content = "[Model reasoning]"
        rows.append({
            "role": role, "tokens": math.ceil(estimate_tokens(message) * agent.density),
            "preview": content.strip()[:PREVIEW_CHARS],
            "truncated": len(content.strip()) > PREVIEW_CHARS,
        })
    if agent.tool_schemas:
        rows.append({
            "role": "schemas",
            "tokens": math.ceil(estimate_tokens({"content": json.dumps(agent.tool_schemas)}) * agent.density),
            "preview": ", ".join(agent.tools), "truncated": False,
        })
    return rows


class WebEvents(Events):
    def __init__(self, web: WebIO, *, workflow: bool = False) -> None:
        self.web = web
        self.workflow = workflow
        self.run_agent: WorkspaceAgent | None = None
        self.child: str | None = None

    def subagent_start(self, agent: str, session_id: str, label: str) -> None:
        self.child = session_id
        web = self.web
        parent = self.run_agent.name if self.run_agent is not None else "main"
        web.publish(delegations=[*web.view["delegations"], {
            "id": session_id, "agent": agent, "parent": parent, "label": web.redact(label)[:240],
            "status": "running", "started": time.time(),
        }][-100:])

    def subagent_end(self, agent: str, session_id: str, outcome: str) -> None:
        self.child = None
        web = self.web
        web.publish(delegations=[{**row, "status": outcome, "finished": time.time()} if row["id"] == session_id else row
                                 for row in web.view["delegations"]])

    def _check_cancel(self) -> None:
        if self.web.cancel_requested.is_set():
            raise Aborted()

    def model_request(self, agent: str, messages: list[dict[str, Any]], *,
                      prompt_tokens: int, max_tokens: int) -> None:
        self._check_cancel()
        web = self.web
        if agent == "document" and self.child:
            status = web.view["status"].removesuffix(WAITING).removesuffix(RESPONDING)
            web.publish(status=status + WAITING)
            return
        if agent != "main" and not self.workflow:
            return
        active = self.run_agent or web.agent
        web.model = active.ctx.llm.info()
        web.publish(
            phase="running", status="Waiting for model", draft="", reasoning="",
            context=web.live_context(active, workflow=self.workflow),
            request={"tokens": prompt_tokens, "estimated": True, "output": max_tokens,
                     "entries": context_entries(active, messages)},
        )

    def delta(self, agent: str, kind: str, text: str) -> None:
        self._check_cancel()
        web = self.web
        if agent == "document" and self.child:
            if kind in ("content", "reasoning") and web.view["status"].endswith(WAITING):
                web.publish(status=web.view["status"].removesuffix(WAITING) + RESPONDING)
            return
        if agent != "main" and not self.workflow:
            return
        if kind in ("content", "reasoning") and web.view["status"] == "Waiting for model":
            web.publish(status="Generating a reply")
        with web.condition:
            if kind == "content":
                web.view["draft"] += text
                web.push({"delta": text})
            elif kind == "reasoning" and web.show_reasoning:
                web.view["reasoning"] += text
                web.push({"reasoning_delta": text})

    def status(self, agent: str, text: str) -> None:
        self._check_cancel()
        if (agent == "main" or self.workflow) and not self.child and text.startswith("compacting context"):
            self.web.publish(phase="compacting", status="Compressing older context")
        elif (agent == "main" or self.workflow) and not self.child and text.startswith("compaction failed"):
            self.web.publish(phase="running", status="Context compression could not finish")
        elif agent == "document":
            self.web.publish(phase="document", status=self.web.redact(text)[:240])

    def tool_start(self, agent: str, name: str, args: dict[str, Any]) -> None:
        self._check_cancel()
        if agent == "main" or self.workflow:
            path = args.get("path")
            pages = args.get("pages")
            status = TOOL_STATUS.get(name, "Running tool")
            detail = name
            if isinstance(path, str) and path:
                if name == "read" and Path(path).suffix.lower() == ".pdf":
                    status = "Reading PDF"
                status += f" · {self.web.redact(Path(path).name)[:120]}"
                detail += f" · {self.web.redact(path)[:240]}"
            if isinstance(pages, str) and pages:
                status += f" · pages {self.web.redact(pages)[:40]}"
            self.web.publish(phase="running", status=status, status_detail=detail)

    def tool_end(self, agent: str, name: str, result: str, error: bool) -> None:
        self._check_cancel()
        if (agent == "main" or self.workflow) and error:
            detail = self.web.view["status_detail"]
            self.web.publish(status_detail=f"{detail}\n{self.web.redact(result)[:300]}")

    def turn_end(self, agent: str, tokens: int, window: int) -> None:
        self._check_cancel()
        if self.child or (agent != "main" and not self.workflow):
            return
        web = self.web
        active = self.run_agent or web.agent
        usage = active.session.usage.get(active.session.ids[-1])
        request = web.view["request"]
        if request is not None and usage is not None and usage.prompt_tokens:
            request = {**request, "tokens": usage.prompt_tokens, "estimated": False,
                       "completion": usage.completion_tokens}
        reasoning = active.session.messages[-1].get("reasoning_content", "") if web.show_reasoning else ""
        if reasoning:
            web.reasoning_parts.append(reasoning)
        web.publish(context=web.live_context(active, workflow=self.workflow), request=request, reasoning=reasoning)

    def compaction(self, agent: str, before: int, after: int) -> None:
        if self.child or (agent != "main" and not self.workflow):
            return
        web = self.web
        if self.run_agent is not None:
            web.publish(phase="running", status="Context compressed",
                        context=web.live_context(self.run_agent, workflow=True))
            with web.condition:
                web.push({"workflow_compaction": {"before": before, "after": after}})
            return
        count = web.agent.session.compactions
        if count > web.compaction_count:
            web.compaction_count = count
            web.record({"type": "compaction", "id": count, "before": before, "after": after, "time": time.time()})
            web.publish(phase="running", status="Context compressed", context=web.live_context())
        else:
            web.publish(context=web.live_context())


class WebIO:
    def __init__(self, workspace: Path, settings: Settings, llm: LLM, *, task: dict[str, Any] | None = None,
                 workflow: Workflow | None = None) -> None:
        self.workspace = workspace
        self.task = task or {"id": "", "title": "Default workspace", "persona": "", "skills": [],
                             "workflow": "", "created": 0, "instructions": ""}
        self.workflow = workflow
        self.condition = Condition()
        self.lock = Lock()
        self.cancel_requested = Event()
        self.sequence = 0
        self.events: deque[tuple[int, dict[str, Any]]] = deque(maxlen=256)
        self.model: ModelInfo | None = None
        self.show_reasoning = settings.show_reasoning
        self.reasoning_parts: list[str] = []
        self.root = workspace / STATE_DIR / "webio"
        root = self.root
        if root.resolve() != root:
            raise ValueError("The WebIO runtime directory must be inside the workspace without symbolic links.")
        root.mkdir(parents=True, exist_ok=True)
        self.activity_path = root / "activity.json"
        self.workflow_activity_path = root / "workflow-activity.json"
        self.workflow_dir = root / "workflow"
        if any(path.is_symlink() for path in (self.activity_path, self.workflow_activity_path, self.workflow_dir)):
            raise ValueError("WebIO task state must be local.")
        self.active_path = root / "active"
        if self.active_path.is_symlink():
            raise ValueError("The active chat pointer must be a local file.")
        active_id = self.active_path.read_text(encoding="utf-8").strip() if self.active_path.exists() else None
        chat_root = root
        if active_id is not None:
            if not active_id or active_id.startswith(".") or Path(active_id).name != active_id:
                raise ValueError("Invalid WebIO active chat ID.")
            chat_root = root / "chats" / active_id
            if chat_root.resolve() != chat_root or not chat_root.is_dir():
                raise ValueError("The active WebIO chat directory is unavailable.")
        self.history = chat_root / "chat.jsonl"
        session_path = chat_root / "session.jsonl"
        if self.history.is_symlink() or session_path.is_symlink():
            raise ValueError("WebIO chat and session files must be local files.")
        session = Session.load(session_path) if session_path.is_file() else Session(session_path)
        if active_id is not None and not session_path.is_file():
            session.id = active_id
        self.finish_interrupted_turn(session)
        self.compaction_count = session.compactions
        self.agent = self.make_agent(settings, llm, session)
        self.credentials = {settings.api_key, getattr(getattr(llm, "settings", None), "api_key", "")} - {""}
        records = [json.loads(line) for line in self.history.read_text(encoding="utf-8").splitlines() if line] \
            if self.history.is_file() else []
        self.messages = [rendered_message(record) for record in records if record["type"] == "message"]
        if not self.show_reasoning:
            for message in self.messages:
                message.pop("reasoning", None)
        self.compactions = [record for record in records if record["type"] == "compaction"]
        self.view = self.idle_view(self.agent)
        self.view.update(self.read_activity(self.activity_path))
        self.view["workflow"] = self.workflow_view(self.workflow_state(), restored=True) if self.workflow else None
        if self.view["run_kind"] == "workflow" and self.view["workflow"] and self.view["workflow"]["gate"]:
            self.view["run_state"] = "waiting"

    def make_agent(self, settings: Settings, llm: LLM, session: Session) -> WorkspaceAgent:
        return WorkspaceAgent(
            ToolContext(self.workspace, settings, llm, WebEvents(self), confine_reads=True),
            tools=TOOLS, session=session, instructions=self.instructions,
            include_workspace_instructions=not self.task["id"],
        )

    @property
    def instructions(self) -> str:
        return "\n\n".join(filter(None, (INSTRUCTIONS, self.task["instructions"])))

    def idle_view(self, agent: WorkspaceAgent) -> dict[str, Any]:
        return {
            "busy": False, "phase": "idle", "status": "", "draft": "", "reasoning": "", "error": "", "notice": "",
            "context": self.live_context(agent), "request": None, "status_since": None, "status_detail": "",
            "failed_stage": "", "activity": [], "delegations": [], "run_state": "ready", "run_kind": "chat",
            "updated": self.task["created"], "workflow": None,
        }

    @staticmethod
    def read_activity(path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() and not path.is_symlink() else {}
            keys = ("activity", "delegations", "run_state", "run_kind", "updated", "workflow_waiting")
            record = {key: data[key] for key in keys if key in data}
            if record.get("run_state") == "running":
                record["run_state"] = "interrupted"
            return record
        except (OSError, ValueError, TypeError):
            return {}

    @staticmethod
    def stored_task_summary(task: dict[str, Any], workspace: Path) -> dict[str, Any]:
        root = workspace / STATE_DIR / "webio"
        view = WebIO.read_activity(root / "activity.json")
        status = "waiting" if view.get("workflow_waiting") else view.get("run_state", "ready")
        return WebIO.summarize_task(task, status, view.get("updated", task["created"]))

    @staticmethod
    def summarize_task(task: dict[str, Any], run_status: str, updated: float) -> dict[str, Any]:
        status = run_status
        if task["id"] and run_status != "running":
            if task.get("closed"):
                status = "closed"
            elif run_status in ("ready", "done"):
                status = "open"
        return {"id": task["id"], "title": task["title"], "status": status,
                "updated": max(updated, task.get("modified", 0))}

    def task_view(self) -> dict[str, Any]:
        return {**{key: self.task[key] for key in ("id", "title", "persona", "skills", "workflow")},
                "closed": self.task.get("closed", False)}

    def task_summary(self) -> dict[str, Any]:
        with self.condition:
            workflow = self.view["workflow"]
            status = "waiting" if not self.view["busy"] and workflow and workflow["status"] == "waiting" \
                else self.view["run_state"]
            return self.summarize_task(self.task, status, self.view["updated"])

    def workflow_state(self) -> dict[str, Any]:
        path = self.workflow_dir / "state.json"
        if path.is_symlink():
            raise ValueError("Workflow state must be local.")
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def workflow_view(self, state: dict[str, Any], *, restored: bool = False) -> dict[str, Any]:
        wf = self.workflow
        steps = [{"id": step.id, "kind": step.kind, "status": state.get("steps", {}).get(step.id, {}).get("status", "pending")}
                 for step in wf.steps]
        statuses = {step["status"] for step in steps}
        if state.get("waiting"):
            status = "waiting"
        elif statuses <= {"done", "skipped"}:
            status = "done"
        elif "failed" in statuses:
            status = "failed"
        elif state:
            status = "interrupted" if restored else "running"
        else:
            status = "ready"
        if restored:
            for step in steps:
                if step["status"] == "running":
                    step["status"] = "interrupted"
        return {"name": wf.name, "description": wf.description, "status": status, "steps": steps,
                "gate": state.get("waiting"), "has_inputs": bool(state),
                "inputs": [{"name": name, "description": str(spec.get("description", "")),
                            "required": "default" not in spec and spec.get("required", True),
                            "default": str(spec.get("default", ""))} for name, spec in wf.inputs.items()]}

    def workflow_parameters(self, given: dict[str, str], step: str | None, answer: str | None) -> tuple[dict[str, Any], dict[str, str]]:
        if not self.workflow:
            raise WorkflowError("Choose a task with a workflow first.")
        current = self.view["workflow"]
        gate = current["gate"]
        if current["status"] == "done":
            raise WorkflowError("This workflow has already finished.")
        if gate:
            if step != gate["step"] or answer is None:
                raise WorkflowError("Review the current workflow step before continuing.")
            if gate["options"] and answer not in gate["options"]:
                raise WorkflowError("Choose one of the review options.")
        elif step is not None:
            raise WorkflowError("This workflow step no longer needs an answer.")
        saved = self.workflow_state()
        inputs = saved["inputs"] if saved else resolve_inputs(self.workflow, given)
        answers = {step: answer} if step is not None and answer is not None else {}
        return inputs, answers

    def run_workflow(self, inputs: dict[str, Any], answers: dict[str, str]) -> None:
        self.reasoning_parts.clear()
        events = WebEvents(self, workflow=True)
        chat_ctx = self.agent.ctx
        workflow = replace(self.workflow, skills="\n\n".join(filter(None, (self.workflow.skills, self.instructions))))
        ctx = ToolContext(self.workspace, chat_ctx.settings, chat_ctx.llm, events, confine_reads=True)

        def on_save(state: dict[str, Any]) -> None:
            view = self.workflow_view(state)
            if view != self.view["workflow"]:
                self.publish(workflow=view)
                if view["status"] == "waiting":
                    self.save_activity()

        runner = WorkspaceRunner(workflow, ctx, inputs, self.workflow_dir, answers=answers, on_save=on_save)
        events.run_agent = runner.agent
        self.finish_interrupted_turn(runner.agent.session)
        try:
            runner.run()
        except NeedsAnswer:
            self.publish(status="Waiting for human review")
            return
        finally:
            if runner.agent.saved_outputs:
                self.record({"type": "message", "role": "assistant", "time": time.time(),
                             "text": "Files saved by " + workflow.name + ".", "outputs": list(runner.agent.saved_outputs)})
        if not runner.agent.saved_outputs:
            final = runner.state["steps"].get(workflow.steps[-1].id, {}).get("output") if workflow.steps else None
            self.record({"type": "message", "role": "assistant", "time": time.time(),
                         "text": final or "Workflow completed."})

    def live_context(self, agent: WorkspaceAgent | None = None, *, workflow: bool = False) -> dict[str, Any]:
        agent = agent or self.agent
        window = self.model.context_window if self.model else None
        settings = agent.ctx.settings
        return {
            "tokens": agent.context_tokens(), "window": window,
            "threshold": window - min(settings.reserve_tokens, window // 4) if window else None,
            "deployment": window,
            "scope": "workflow" if workflow else "chat",
            "model": self.model.id if self.model else settings.model,
            "provider": settings.provider,
            "compactions": agent.session.compactions, "density": round(agent.density, 2),
            "entries": context_entries(agent, [{"role": "system", "content": agent.system}, *agent.session.context()]),
        }

    @staticmethod
    def finish_interrupted_turn(session: Session) -> None:
        recorded = set()
        for message in reversed(session.messages):
            if message["role"] == "tool":
                recorded.add(message["tool_call_id"])
                continue
            for call in message.get("tool_calls") or []:
                if call["id"] not in recorded:
                    session.append({"role": "tool", "tool_call_id": call["id"],
                                    "content": "WebIO stopped before the tool outcome was recorded. Check the workspace."})
            break

    def push(self, event: dict[str, Any]) -> None:
        """Publish an event while holding the condition lock."""
        self.sequence += 1
        self.events.append((self.sequence, event))
        self.condition.notify_all()

    def publish(self, **patch: Any) -> None:
        with self.condition:
            if "status" in patch and patch["status"] != self.view["status"]:
                patch["status_since"] = time.time() if patch["status"] else None
                if patch["status"] and patch.get("busy", self.view["busy"]):
                    patch["activity"] = [*patch.get("activity", self.view["activity"]),
                                         {"label": patch["status"], "time": patch["status_since"]}][-100:]
            self.view.update(patch)
            self.push({"patch": patch})

    def redact(self, text: str) -> str:
        for credential in self.credentials:
            text = text.replace(credential, "[redacted]")
        return text

    def record(self, record: dict[str, Any]) -> None:
        is_message = record["type"] == "message"
        event = rendered_message(record) if is_message else record
        with self.history.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        with self.condition:
            rows = self.messages if is_message else self.compactions
            rows.append(event)
            self.push({record["type"]: event})

    def snapshot(self) -> dict[str, Any]:
        with self.condition:
            return {**self.view, "messages": list(self.messages), "compactions": self.compactions[-30:],
                    "workspace": self.task["title"] if self.task["id"] else self.workspace.name,
                    "task": self.task_view(),
                    "session_id": self.agent.session.id, "cursor": self.sequence}

    def clear_chat(self) -> None:
        """Start an empty chat while holding the workspace lock."""
        session = Session()
        chat_root = self.root / "chats" / session.id
        if chat_root.resolve() != chat_root:
            raise ValueError("The WebIO chat directory must be local.")
        session.path = chat_root / "session.jsonl"
        agent = self.make_agent(self.agent.ctx.settings, self.agent.ctx.llm, session)
        view = self.idle_view(agent)
        chat_root.mkdir(parents=True)
        atomic_text(self.active_path, session.id + "\n")
        with self.condition:
            for key in ("activity", "delegations", "run_state", "run_kind", "updated", "workflow"):
                view[key] = self.view[key]
            self.agent = agent
            self.history = chat_root / "chat.jsonl"
            self.messages.clear()
            self.compactions.clear()
            self.reasoning_parts.clear()
            self.compaction_count = 0
            self.view = view
            self.events.clear()
            snapshot = self.snapshot()
            snapshot["cursor"] = self.sequence + 1
            self.push({"snapshot": snapshot})

    def events_after(self, cursor: int) -> list[tuple[int, dict[str, Any]]]:
        with self.condition:
            self.condition.wait_for(lambda: cursor != self.sequence, timeout=12)
            if cursor > self.sequence or (self.events and cursor < self.events[0][0] - 1):
                return [(self.sequence, {"snapshot": self.snapshot()})]
            return [(number, event) for number, event in self.events if number > cursor]

    def start(self, action: Callable[[], str | None], status: str, *, kind: str = "chat") -> bool:
        if not self.lock.acquire(blocking=False):
            return False
        self._start_claimed(action, status, kind)
        return True

    def start_workflow(self, given: dict[str, str], step: str | None, answer: str | None) -> bool:
        if not self.lock.acquire(blocking=False):
            return False
        try:
            inputs, answers = self.workflow_parameters(given, step, answer)
        except BaseException:
            self.lock.release()
            raise
        self._start_claimed(lambda: self.run_workflow(inputs, answers), "Preparing workflow", "workflow")
        return True

    def cancel(self) -> bool:
        with self.condition:
            if not self.view["busy"]:
                return False
            self.cancel_requested.set()
            if self.view["status"] != "Stopping":
                self.view["status"] = "Stopping"
                self.push({"patch": {"status": "Stopping"}})
            return True

    def _start_claimed(self, action: Callable[[], str | None], status: str, kind: str) -> None:
        self.cancel_requested.clear()
        prior = self.read_activity(self.workflow_activity_path) if kind == "workflow" and self.view["workflow"]["has_inputs"] else {}
        self.publish(busy=True, phase="running", status=status, draft="", reasoning="", error="", notice="",
                     status_detail="", failed_stage="", activity=prior.get("activity", []),
                     delegations=prior.get("delegations", []), run_kind=kind,
                     run_state="running", updated=time.time())
        try:
            Thread(target=self.work, args=(action,), daemon=True).start()
        except RuntimeError:
            self.publish(busy=False, phase="idle", status="", run_state="failed")
            self.lock.release()
            raise

    def work(self, action: Callable[[], str | None]) -> None:
        error = ""
        notice = ""
        aborted = False
        try:
            self.save_activity()
            notice = action() or ""
            if self.cancel_requested.is_set():
                aborted = True
                notice = "Stopped by user."
        except Aborted:
            aborted = True
            notice = "Stopped by user."
        except (LLMError, CompactionError, WorkflowError, OSError, ValueError) as exc:
            error = self.redact(str(exc))
        except Exception:
            logger.exception("WebIO job failed")
            error = "The workspace operation failed. Check the WebIO server log."
        finally:
            try:
                self.cancel_requested.clear()
                workflow = self.workflow_view(self.workflow_state(), restored=True) if (aborted and self.workflow) else self.view["workflow"]
                waiting = self.view["run_kind"] == "workflow" and workflow and workflow["status"] == "waiting"
                outcome = "interrupted" if aborted else "failed" if error else "waiting" if waiting else "done"
                updated = time.time()
                self.save_activity(run_state=outcome, updated=updated)
                patch: dict[str, Any] = {
                    "busy": False, "phase": "idle", "status": "", "draft": "", "reasoning": "",
                    "error": error, "notice": notice, "context": self.live_context(), "status_detail": "",
                    "failed_stage": self.view["status"] if error else "", "run_state": outcome, "updated": updated,
                }
                if aborted and self.workflow:
                    patch["workflow"] = workflow
                self.publish(**patch)
            finally:
                self.lock.release()

    def save_activity(self, **updates: Any) -> None:
        record = {key: self.view[key] for key in ("activity", "delegations", "run_state", "run_kind", "updated")}
        workflow = self.view["workflow"]
        record["workflow_waiting"] = bool(workflow and workflow["status"] == "waiting")
        record.update(updates)
        try:
            payload = json.dumps(record, ensure_ascii=False)
            if record["run_kind"] == "workflow":
                atomic_text(self.workflow_activity_path, payload)
            atomic_text(self.activity_path, payload)
        except OSError:
            logger.warning("Could not persist WebIO activity.", exc_info=True)

    def chat(self, text: str, files: list[str]) -> None:
        self.reasoning_parts.clear()
        outputs = self.agent.saved_outputs
        outputs.clear()
        self.record({"type": "message", "role": "user", "text": text, "files": files, "time": time.time()})
        prompt = text
        if files:
            prompt += "\n\nUser-selected workspace files (relative paths):\n" + json.dumps(files, ensure_ascii=False)
        answer = None
        try:
            answer = self.agent.run(prompt)
        finally:
            if answer is not None or outputs:
                text = answer if answer is not None else "Files saved before the run stopped."
                reply = {"type": "message", "role": "assistant", "text": text, "time": time.time()}
                if outputs:
                    reply["outputs"] = list(outputs)
                if self.reasoning_parts:
                    reply["reasoning"] = "\n\n".join(self.reasoning_parts)
                self.record(reply)

    def compact(self) -> str | None:
        if not self.agent.session.messages:
            raise ValueError("Start a conversation before compressing context.")
        self.model = self.agent.ctx.llm.info()
        if self.agent.compact(force=True):
            return None
        return "No older context to compress"
