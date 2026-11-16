"""Live-model benchmark of the kentc_agent topic-file compaction runtime.

Run from the project root:
    uv run python examples/compare_memory.py --output docs/memory-comparison-topics.json

Synthetic, seeded histories exclude the cost of generating the historical turns.
Each measured trial runs in a fresh process/workspace; trials run sequentially.
No production source or existing user sessions are modified.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import platform
import re
import resource
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CASES = ("buried_revision", "failed_repair")
SHA = "a39f71c2b830d40e8cc6a9b1f502d734e61a08bf"
ERROR = "E_FRAME_MARKER pipeline/decoder.py:73 expected=0x7E observed=0x00"
COMMON = """Use only the synthetic evidence in this workspace or this session. No network access.
Do not change any evidence or code files. Historical assistant claims are not verification.
Evidence batch bodies were previously read into this session; evidence.log preserves the same
original records and is available to you. Search/read narrowly rather than dumping
it. Cite the record IDs requested below. Return one JSON object, no markdown or commentary.
"""
QUESTIONS = {
    "buried_revision": COMMON + """Reconcile CEDAR-17 production approval history. A later proposal does not
supersede an approved revision; a signed amendment changes only the named field.
What are the currently approved revision, quota, region, and exact full rollback SHA?
Also identify the pending proposal's revision and quota without treating it as approved.
Return keys revision (integer), quota (integer), region, rollback_sha,
pending_revision (integer), pending_quota (integer), evidence_ids (array of record IDs
supporting the approved revision and its amendment).""",
    "failed_repair": COMMON + """Reconcile the decoder repair history. Run `python3 verify.py --strict` now,
then report whether the repair is resolved. Identify which earlier attempts reproduced the
identical decoder error, and keep the cache-path error separate even though its code matches.
Return keys resolved (boolean), last_exit_code (integer), failing_test, recurring_attempts
(array of attempt letters), distinct_error_path, expected_marker, observed_marker,
evidence_ids (record IDs for the recurring decoder errors and distinct cache error).""",
}
EXPECTED = {
    "buried_revision": {
        "revision": 7, "quota": 417, "region": "eu-west-2", "rollback_sha": SHA,
        "pending_revision": 8, "pending_quota": 999,
    },
    "failed_repair": {
        "resolved": False, "last_exit_code": 1, "failing_test": "test_reject_zero_marker",
        "recurring_attempts": ["A", "C"], "distinct_error_path": "pipeline/cache.py:73",
        "expected_marker": "0x7E", "observed_marker": "0x00",
    },
}
RECORD_IDS = {
    "buried_revision": {"APR-07", "AMD-02"},
    "failed_repair": {"ERR-A", "ERR-C", "ERR-D"},
}
VERIFY_SOURCE = '''import sys
from pipeline.decoder import decode

try:
    decode(b"\\x00payload")
except ValueError:
    print("1 passed: test_reject_zero_marker")
    sys.exit(0)
print("FAILED test_reject_zero_marker")
print("E_FRAME_MARKER pipeline/decoder.py:73 expected=0x7E observed=0x00")
sys.exit(1)
'''


def fixture(case: str, workspace: Path) -> tuple[list[dict[str, Any]], str, dict[str, str]]:
    """32 bounded read results: valid completed exchanges, not giant bypassed results."""
    if case == "buried_revision":
        records = {
            0: "REC-06 CEDAR-17 revision=6 state=previously-approved quota=300 region=us-east-1 rollback_sha=" + "1" * 40,
            2: f"APR-07 CEDAR-17 revision=7 state=approved quota=471 region=eu-west-2 rollback_sha={SHA}",
            3: "AMD-02 CEDAR-17 revision=7 signed-amendment=2 quota=417; only quota changes; all other APR-07 fields retained",
            4: "PEND-08 CEDAR-17 revision=8 state=proposal-not-approved quota=999 region=eu-central-1 rollback_sha=" + "8" * 40,
        }
        record_row = 62  # Beyond the compactor's bounded tool-result prefix.
    else:
        records = {
            0: f"ERR-A Attempt=A command=python3 verify.py --strict exit_code=1\n{ERROR}",
            2: "CLAIM-B Attempt=B assistant-claim='fixed; happy-path smoke passed'; no strict verification recorded",
            3: f"ERR-C Attempt=C command=python3 verify.py --strict exit_code=1\n{ERROR}",
            4: "ERR-D Attempt=D separate-condition cache lookup\nE_FRAME_MARKER pipeline/cache.py:73 expected=0x7E observed=0xFF",
        }
        record_row = 2  # In the bounded prefix: the old summarizer gets the error evidence.
    messages: list[dict[str, Any]] = [{
        "role": "user", "content": "Archive these operational evidence batches for later reconciliation; do not infer approval or repair success yet."
    }]
    blocks = []
    line = 1
    for batch in range(32):
        rows = [f"Batch {batch:02d}: archived operational evidence; original ordering is preserved."]
        for row in range(80):
            if batch in records and row == record_row:
                rows.extend(records[batch].splitlines())
            else:
                rows.append(f"Sample {batch:02d}-{row:03d}: routine telemetry remained stable; this entry records no approval or test verdict.")
        block = "\n".join(rows) + "\n"
        # The configured production big-result route starts at 3,000 estimated tokens.
        assert len(block) / 4 + 4 < 3000
        count = len(rows)
        call = {"id": f"archive_{batch:02d}", "type": "function", "function": {
            "name": "read", "arguments": json.dumps({"path": "evidence.log", "offset": line, "limit": count})
        }}
        messages.append({"role": "assistant", "content": f"Inspect archived batch {batch:02d}.", "tool_calls": [call]})
        messages.append({"role": "tool", "tool_call_id": call["id"], "content": block})
        blocks.append(block)
        line += count
    messages.append({"role": "assistant", "content": "Evidence archive complete. Approval and repair outcomes have not been reconciled."})
    corpus = "".join(blocks)
    (workspace / "evidence.log").write_text(corpus)
    if case == "failed_repair":
        (workspace / "pipeline").mkdir()
        (workspace / "pipeline" / "decoder.py").write_text(
            'def decode(frame):\n    if not frame:\n        raise ValueError("empty frame")\n    return frame[1:]\n'
        )
        (workspace / "verify.py").write_text(VERIFY_SOURCE)
    hashes = {str(p.relative_to(workspace)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in workspace.rglob("*") if p.is_file()}
    return messages, corpus, hashes


class Meter:
    """Observe the real client, including foreground compression requests."""
    def __init__(self, client: Any) -> None:
        self.client = client
        self.calls: list[dict[str, Any]] = []
        self.lock = threading.Lock()
        self.origin = time.monotonic()

    def info(self, *, refresh: bool = False) -> Any:
        return self.client.info(refresh=refresh)

    def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        system = str(messages[0].get("content", ""))
        kind = "foreground"
        if system.startswith("You are a context summarization assistant"):
            kind = "summary"
        start = time.monotonic()
        record: dict[str, Any] = {"kind": kind, "started_s": start - self.origin,
                                  "first_delta_s": None, "first_content_s": None}
        with self.lock:
            self.calls.append(record)
        callback = kwargs.pop("on_delta", None)

        def delta(channel: str, text: str) -> None:
            if text:
                elapsed = time.monotonic() - start
                if record["first_delta_s"] is None:
                    record["first_delta_s"] = elapsed
                if channel == "content" and record["first_content_s"] is None:
                    record["first_content_s"] = elapsed
            if callback is not None:
                callback(channel, text)
        try:
            reply = self.client.chat(messages, on_delta=delta, **kwargs)
            record.update(finish=reply.finish, tool_calls=[c["function"]["name"] for c in reply.tool_calls],
                          prompt_tokens=reply.usage.prompt_tokens if reply.usage else None,
                          completion_tokens=reply.usage.completion_tokens if reply.usage else None)
            return reply
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            record["elapsed_s"] = time.monotonic() - start


def decode_answer(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char == "{":
            try:
                value, _ = decoder.raw_decode(text[index:])
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                pass
    return {}


def grade(case: str, answer: str, tools: list[dict[str, Any]], workspace: Path,
          hashes: dict[str, str]) -> dict[str, Any]:
    value = decode_answer(answer)
    checks = {}
    for key, expected in EXPECTED[case].items():
        actual = value.get(key)
        if key == "recurring_attempts" and isinstance(actual, list):
            actual = sorted(actual) if all(isinstance(item, str) for item in actual) else actual
        checks[key] = type(actual) is type(expected) and actual == expected
    cited = value.get("evidence_ids", [])
    checks["evidence_ids"] = isinstance(cited, list) and all(isinstance(item, str) for item in cited) and RECORD_IDS[case].issubset(cited)
    checks["fixtures_unchanged"] = all((workspace / p).is_file() and hashlib.sha256((workspace / p).read_bytes()).hexdigest() == digest
                                         for p, digest in hashes.items())
    if case == "failed_repair":
        checks["live_verification"] = any(
            item["name"] == "bash" and "verify.py" in str(item["args"]) and
            "FAILED test_reject_zero_marker" in item["result"] and
            ("[exit code 1]" in item["result"] or re.search(r"(?m)^EXIT=1$", item["result"]) is not None)
            for item in tools
        )
    return {"pass": all(checks.values()), "checks": checks, "parsed": value}


def totals(calls: list[dict[str, Any]]) -> dict[str, Any]:
    return {kind: {
        "calls": len(selected := [c for c in calls if c["kind"] == kind]),
        "prompt_tokens": sum(c.get("prompt_tokens") or 0 for c in selected),
        "completion_tokens": sum(c.get("completion_tokens") or 0 for c in selected),
        "usage_missing_calls": sum(c.get("prompt_tokens") is None for c in selected),
        "request_wall_s": sum(c["elapsed_s"] for c in selected),
    } for kind in ("foreground", "summary")}


def worker(case: str, trial: int) -> dict[str, Any]:
    from kentc_agent.adapters import llm as llm_module
    from kentc_agent.adapters import tools as tools_module
    from kentc_agent.adapters.session import Session
    from kentc_agent.agent.loop import Agent
    from kentc_agent.config import Settings
    from kentc_agent.ports import Events

    class Observer(Events):
        def __init__(self) -> None:
            self.tools: list[dict[str, Any]] = []
            self.projections: list[dict[str, Any]] = []
            self.statuses: list[str] = []
            self.current: dict[str, Any] = {}

        def tool_start(self, agent: str, name: str, args: dict[str, Any]) -> None:
            self.current = {"name": name, "args": args}

        def tool_end(self, agent: str, name: str, result: str, error: bool) -> None:
            shown = result[:8000].replace(str(workspace), "<workspace>").replace(getpass.getuser(), "<user>")
            self.tools.append({**self.current, "name": name, "error": error, "result": shown})

        def compaction(self, agent: str, before: int, after: int) -> None:
            self.projections.append({"kind": "summary", "before": before, "after": after})


        def status(self, agent: str, text: str) -> None:
            self.statuses.append(text)

    settings = Settings(temperature=0, reasoning_effort="none", sub_effort="none",
                        max_output_tokens=2048, max_turns=8, request_timeout=180,
                        trust_env=False, trace=True)
    meter = Meter(llm_module.LLMClient(settings))
    model = meter.info()
    events = Observer()
    result: dict[str, Any] = {"case": case, "trial": trial,
                              "model": model.id, "context_window": model.context_window}
    agent = None
    with tempfile.TemporaryDirectory(prefix="memory-comparison-") as temporary:
        workspace = Path(temporary)
        history, corpus, hashes = fixture(case, workspace)
        result.update(corpus_sha256=hashes["evidence.log"], corpus_chars=len(corpus),
                      seeded_messages=len(history), baseline_peak_rss_mib=peak_rss())
        session = Session(workspace / "session.jsonl")
        t0 = time.monotonic()
        for message in history:
            session.append(message)
        result["seed_append_s"] = time.monotonic() - t0
        ctx = tools_module.ToolContext(workspace, settings, meter, events)
        t0 = time.monotonic()
        agent = Agent(ctx, session=session, tools=[tools_module.CORE_TOOLS[name] for name in ("read", "bash")])
        result["agent_init_s"] = time.monotonic() - t0
        result["initial_context_estimate"] = agent.context_tokens()
        meter.origin = time.monotonic()
        answer = ""
        try:
            answer = agent.run(QUESTIONS[case])
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        result["answer_wall_s"] = time.monotonic() - meter.origin
        result["grade"] = grade(case, answer, events.tools, workspace, hashes)
        result["answer"] = answer
        agent.close()
        result["answer_plus_close_s"] = time.monotonic() - meter.origin
        result["peak_rss_mib"] = peak_rss()
        result["calls"] = meter.calls
        result["usage"] = totals(meter.calls)
        foreground = [c for c in meter.calls if c["kind"] == "foreground"]
        result["first_foreground_delta_s"] = next((c["started_s"] + c["first_delta_s"] for c in foreground if c["first_delta_s"] is not None), None)
        final_calls = [c for c in foreground if c.get("finish") and not c.get("tool_calls") and c["first_content_s"] is not None]
        result["answer_first_content_s"] = final_calls[-1]["started_s"] + final_calls[-1]["first_content_s"] if final_calls else None
        result["tool_calls"] = events.tools
        result["projections"] = events.projections
        result["statuses"] = events.statuses
    return result


def peak_rss() -> float:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / (1024 * 1024 if sys.platform == "darwin" else 1024)


def summarize(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in CASES:
        samples = [r for r in results if r["case"] == case]
        if not samples:
            continue
        row = {"case": case, "trials": len(samples),
               "passed": sum(r["grade"]["pass"] for r in samples)}
        for key in ("answer_wall_s", "answer_first_content_s", "answer_plus_close_s", "peak_rss_mib", "seed_append_s"):
            values = [r[key] for r in samples if r.get(key) is not None]
            row[f"median_{key}"] = statistics.median(values) if values else None
        for kind in ("foreground", "summary"):
            for key in ("calls", "prompt_tokens", "completion_tokens"):
                row[f"median_{kind}_{key}"] = statistics.median(r["usage"][kind][key] for r in samples)
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--trial", type=int, default=1)
    args = parser.parse_args()
    if args.worker:
        args.output.write_text(json.dumps(worker(args.case, args.trial), ensure_ascii=False, indent=2))
        return
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    results: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(),
        "python": sys.version, "repeats": args.repeats,
        "protocol": {"order": "sequential fresh processes, one per trial",
                     "history": "32 seeded completed read exchanges, each below the 3000 estimated-token big-result threshold",
                     "history_profile": "Bulk seeded/imported transcript; history-generation and compression costs before the measured run are excluded. Not a steady-state throughput benchmark.",
                     "settings": {"temperature": 0, "reasoning_effort": "none", "sub_effort": "none",
                                "max_output_tokens": 2048, "max_turns": 8, "reserve_tokens": 16384,
                                "keep_recent_tokens": 20000, "tools": ["read", "bash"]},
                     "memory": "foreground compression with consolidated local topic files; ordinary read/bash tools",
                     "rss": "client process lifetime peak; excludes model server; fresh process per trial"},
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="memory-comparison-results-") as directory:
        for case in CASES:
            for trial in range(1, args.repeats + 1):
                child_output = Path(directory) / "trial.json"
                command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--case", case,
                           "--trial", str(trial), "--output", str(child_output)]
                completed = subprocess.run(command, capture_output=True, text=True, timeout=600)
                if completed.returncode:
                    raise RuntimeError(f"{case}/{trial}: {completed.stderr}")
                result = json.loads(child_output.read_text())
                if results and any(r["model"] != result["model"] or r["context_window"] != result["context_window"] for r in results):
                    raise RuntimeError("Deployment changed during the benchmark; do not combine these trials")
                matching = [r for r in results if r["case"] == case]
                if matching and matching[0]["corpus_sha256"] != result["corpus_sha256"]:
                    raise RuntimeError("Case inputs differ between trials")
                results.append(result)
                report["summary"] = summarize(results)
                args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
                print(json.dumps({"case": case, "trial": trial,
                                  "passed": result["grade"]["pass"], "answer_s": round(result["answer_wall_s"], 3),
                                  "close_s": round(result["answer_plus_close_s"], 3),
                                  "usage": result["usage"]}), flush=True)
    print(json.dumps(report["summary"], indent=2), flush=True)


if __name__ == "__main__":
    main()
