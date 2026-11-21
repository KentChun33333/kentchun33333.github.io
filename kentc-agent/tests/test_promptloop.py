"""Acceptance tests for the unified PromptLoop FSM engine in kentc_agent.workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kentc_agent.adapters.llm import Reply, Usage
from kentc_agent.promptloop import BUNDLED, Runner, WorkflowError, load, resolve_inputs

from .conftest import FakeLLM


def test_all_bundled_workflows_load_cleanly():
    files = sorted(BUNDLED.glob("*.yaml"))
    names = {f.stem for f in files}
    assert {"coding-loop", "case-review", "ter-case-review", "rm-client-insight",
            "docs-first-insight", "web-first-insight", "pdf-brief"} <= names
    for f in files:
        wf = load(f)
        assert wf.entry in wf.states
        assert any(s.kind == "gate" for s in wf.steps), f"{f.name} should end with a deterministic exit_gate"


def test_prompt_state_cannot_bypass_exit_gate_to_done(tmp_path: Path):
    wf_path = tmp_path / "bypass.yaml"
    wf_path.write_text(
        """
name: bypass-test
entry: build
states:
  build:
    prompt: "do work"
    routes:
      default: DONE
  exit_gate:
    gate: true
    validators:
      - expr: "true"
    routes:
      passed: DONE
      failed: build
""",
        encoding="utf-8",
    )
    with pytest.raises(WorkflowError, match="cannot route directly to DONE"):
        load(wf_path)


def test_coding_loop_pure_fresh_sessions_test_fail_improve_and_pass(make_ctx, tmp_path: Path):
    # Create a tiny test script that fails until `fixed.txt` exists
    check_py = tmp_path / "check.py"
    check_py.write_text(
        "from pathlib import Path\nimport sys\n"
        "sys.exit(0 if Path('fixed.txt').is_file() else 1)\n",
        encoding="utf-8",
    )
    wf_path = tmp_path / "loop.yaml"
    wf_path.write_text(
        """
name: mini-coding-loop
entry: build
runtime:
  max_cycles: 10
  max_retries_per_state: 3
  no_progress_limit: 3
tools: []
states:
  build:
    prompt: "Implement feature"
    routes:
      default: test
  test:
    prompt: "Check tests"
    validators:
      - name: run_check
        command: "python3 check.py"
    routes:
      passed: review
      failed: improve
  improve:
    prompt: "Fix test failure: {{ steps.test.evidence | json }}"
    routes:
      default: test
  review:
    prompt: "Independently review"
    format: json
    schema:
      verdict: "approved|issues_found"
    validators:
      - name: approved_check
        expr: "step_data.verdict == 'approved'"
    routes:
      passed: exit_gate
      failed: improve
  exit_gate:
    gate: true
    validators:
      - name: final_check
        command: "python3 check.py"
    routes:
      passed: DONE
      failed: improve
""",
        encoding="utf-8",
    )

    seen_prompts: list[str] = []
    call_idx = 0

    def script(messages, tools):
        nonlocal call_idx
        call_idx += 1
        user_text = messages[-1]["content"]
        seen_prompts.append(user_text)
        if call_idx == 1:
            return Reply(content="BUILD_SECRET_THOUGHT: implemented v1", finish="stop")
        if call_idx == 2:
            # Agent falsely claims tests passed, but runtime validator runs check.py -> exit_code 1!
            return Reply(content="All tests passed!", finish="stop")
        if call_idx == 3:
            # Improve creates fixed.txt
            (tmp_path / "fixed.txt").write_text("ok", encoding="utf-8")
            return Reply(content="fixed the issue", finish="stop")
        if call_idx == 4:
            return Reply(content="tests re-checked", finish="stop")
        return Reply(content='{"verdict": "approved"}', finish="stop")

    wf = load(wf_path)
    runner = Runner(wf, make_ctx(FakeLLM(script)), {}, tmp_path / "run")
    state = runner.run()
    runner.close()

    assert state["status"] == "DONE"
    transitions = [(h["from"], h["event"], h["to"]) for h in state["history"]]
    assert transitions == [
        ("build", "default", "test"),
        ("test", "failed", "improve"),       # objective exit_code=1 overrode agent's false "All tests passed!"
        ("improve", "default", "test"),
        ("test", "passed", "review"),
        ("review", "passed", "exit_gate"),
        ("exit_gate", "passed", "DONE"),
    ]
    # 100% pure fresh sessions: review must NOT see build's private conversation history
    assert "BUILD_SECRET_THOUGHT" not in seen_prompts[-1]
    sessions = list((tmp_path / "run" / "sessions").glob("*.jsonl"))
    assert len(sessions) == 5
    # Monotonic event log persisted
    events = [json.loads(line) for line in (tmp_path / "run" / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    assert events[-1]["status"] == "DONE"


def test_no_progress_detection_pauses_loop(make_ctx, tmp_path: Path):
    wf_path = tmp_path / "stuck.yaml"
    wf_path.write_text(
        r"""
name: stuck-loop
entry: test
runtime:
  max_cycles: 10
  max_retries_per_state: 5
  no_progress_limit: 2
tools: []
states:
  test:
    prompt: "Run failing test"
    validators:
      - name: always_fail
        command: "python3 -c 'import sys; sys.stderr.write(\"same error\"); sys.exit(2)'"
    routes:
      passed: DONE
      failed: test
""",
        encoding="utf-8",
    )
    wf = load(wf_path)
    runner = Runner(wf, make_ctx(FakeLLM(lambda m, t: Reply(content="tried", finish="stop"))), {}, tmp_path / "run")
    state = runner.run()
    runner.close()
    assert state["status"] == "PAUSE"
    assert state["cycles"] == 2
    assert any(h["event"] == "no_progress" for h in state["history"])


def test_token_budget_exhaustion_pauses_and_crash_reconciles_on_resume(make_ctx, tmp_path: Path):
    wf_path = tmp_path / "budget.yaml"
    wf_path.write_text(
        """
name: budget-loop
entry: s1
runtime:
  max_cycles: 10
  max_total_tokens: 100
tools: []
states:
  s1:
    prompt: "step 1"
    routes:
      default: s2
  s2:
    prompt: "step 2"
    routes:
      default: DONE
""",
        encoding="utf-8",
    )
    wf = load(wf_path)
    llm = FakeLLM(lambda m, t: Reply(content="ok", finish="stop", usage=Usage(prompt_tokens=80, completion_tokens=40)))
    run_dir = tmp_path / "run"
    runner = Runner(wf, make_ctx(llm), {}, run_dir)
    state = runner.run()
    runner.close()
    assert state["status"] == "PAUSE"
    assert state["total_tokens"] == 120
    assert "s2" not in state["steps"]

    # Simulate crash reconciliation: mark s2 in_flight and raise token cap
    state["status"] = "running"
    state["current_state"] = "s2"
    state["in_flight"] = {"execution_id": "exec-0099", "state": "s2", "started": 1.0}
    (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

    wf.runtime.max_total_tokens = 1000
    runner2 = Runner(wf, make_ctx(llm), {}, run_dir)
    resumed = runner2.run()
    runner2.close()
    assert resumed["status"] == "DONE"
    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(e["type"] == "reconciled_crash" for e in events)


def test_per_state_lazy_skill_loading(make_ctx, tmp_path: Path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "alpha.md").write_text("ALPHA_SKILL_BODY", encoding="utf-8")
    (skills_dir / "beta.md").write_text("BETA_SKILL_BODY", encoding="utf-8")

    wf_path = tmp_path / "skills_wf.yaml"
    wf_path.write_text(
        """
name: skills-wf
entry: first
tools: []
states:
  first:
    skills: [alpha]
    prompt: "do first"
    routes:
      default: second
  second:
    skills: [beta]
    prompt: "do second"
    routes:
      default: DONE
""",
        encoding="utf-8",
    )
    systems: list[str] = []

    def script(messages, tools):
        systems.append(messages[0]["content"])
        return Reply(content="done", finish="stop")

    wf = load(wf_path)
    runner = Runner(wf, make_ctx(FakeLLM(script)), {}, tmp_path / "run")
    state = runner.run()
    runner.close()
    assert state["status"] == "DONE"
    assert "ALPHA_SKILL_BODY" in systems[0] and "BETA_SKILL_BODY" not in systems[0]
    assert "BETA_SKILL_BODY" in systems[1] and "ALPHA_SKILL_BODY" not in systems[1]
