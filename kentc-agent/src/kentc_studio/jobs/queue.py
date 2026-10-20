"""The studio job queue: a bounded worker pool with one-at-a-time local-model jobs."""

from __future__ import annotations

import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from kentc_agent.errors import Aborted
from kentc_agent.adapters.llm import LLMError
from kentc_agent.adapters.tools import ToolError
from kentc_agent.workflow import WorkflowError

from ..config import AgentError
from ..data import DataError
from ..models import SETTLED, Job, JobEvents

if TYPE_CHECKING:
    from ..service.cases import CaseService

# Expected job failures: reported as the job's error, not as a crash.
JOB_ERRORS = (AgentError, DataError, WorkflowError, LLMError, ToolError, OSError, ValueError, KeyError)


class JobDispatcher:
    """Scans queued jobs and submits ready ones to a bounded pool.

    Local-model jobs run one at a time (`local_busy`); data pulls and external-agent jobs run in parallel.
    """

    def __init__(self, service: CaseService, workers: int = 4) -> None:
        self.service = service
        self.cv = threading.Condition()
        self.local_busy = False
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="job")
        self._thread = threading.Thread(target=self._dispatch, name="job-dispatcher", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def wake(self) -> None:
        with self.cv:
            self.cv.notify_all()

    def _dispatch(self) -> None:
        while True:
            with self.cv:
                started = self._start_ready()
                if not started:
                    self.cv.wait(timeout=2)

    def _start_ready(self) -> bool:
        service = self.service
        for case in list(service.cases.values()):
            status = {j.id: j.status for j in case.jobs}
            for job in case.jobs:
                if job.status != "queued" or any(status.get(a, "done") not in SETTLED for a in job.after):
                    continue
                try:
                    local = service.provider(job).local
                except KeyError:
                    job.status, job.error = "failed", f"{job.agent} is no longer configured in studio.yaml"
                    case.save()
                    return True
                if local and self.local_busy:
                    continue
                job.status, job.started = "running", time.time()
                if local:
                    self.local_busy = True
                case.save()
                self.pool.submit(self._run, case, job, local)
                return True
        return False

    def _run(self, case: Any, job: Job, local: bool) -> None:
        service = self.service
        label = service.label(job)
        try:
            case.event("start", label, "started", job.id)
            job_dir = case.dir / "jobs" / job.id
            job_dir.mkdir(parents=True, exist_ok=True)
            events = JobEvents(case, job, label)
            inputs = service._inputs(case, job, job_dir, events)
            request: dict[str, Any] = {}
            if job.role != "query":
                materials = {"case": case.meta(),
                             "context_documents": (job_dir / "context.md").read_text(encoding="utf-8")} \
                    if job.role == "context" else service.materials(case)
                request = {"role": job.role, "case_id": case.id, "job_id": job.id, "inputs": inputs,
                           "documents": [{**d, "url": f"{service.config.public_url}/api/cases/{case.id}/docs/{d['name']}"}
                                         for d in case.documents],
                           "materials": materials}
            result = service.provider(job).run(case_dir=case.dir, job_dir=job_dir, inputs=inputs, events=events,
                                              settings=service.settings, llm=service.llm, request=request)
            service._store(case, job, result)
            job.status = "done"
            case.audit("AGT", f"{label}: done")
            case.event("done", label, "finished", job.id)
        except Aborted:
            job.status, job.error = "stopped", "stopped by the analyst"
            case.event("error", label, "stopped", job.id)
        except JOB_ERRORS as e:
            job.status, job.error = "failed", str(e).split("\nResume with")[0][:500]
            case.audit("SYS", f"{label} failed: {job.error}")
            case.event("error", label, job.error, job.id)
        except Exception as e:  # noqa: BLE001 - an unexpected failure must not leave the job running
            job.status, job.error = "failed", f"unexpected error: {type(e).__name__}: {e}"[:500]
            traceback.print_exc()
            case.audit("SYS", f"{label} crashed: {job.error}")
            case.event("error", label, job.error, job.id)
        finally:
            job.finished = time.time()
            case.stopping.discard(job.id)
            case.progress.pop(job.id, None)
            case.live = {"agent": "", "kind": "", "text": ""}
            case.save()
            with self.cv:
                if local:
                    self.local_busy = False
                self.cv.notify_all()
