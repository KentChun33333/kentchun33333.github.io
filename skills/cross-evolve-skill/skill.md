---
name: cross-evolve-skill
description: Self-optimizing engine and methodology for evolving, scaling, and adapting codebase skills.
---

# Cross-Evolve Skill

This module implements the self-optimization logic and policy for evolving workspace skill assets. It defines how the agent autonomously audits, adapts, tests, and promotes skill updates across the codebase safely and systematically.

---

## Core Philosophy

1. **Maximize Knowledge Delta**: A skill must inject expert decision-making logic, guardrails, and non-obvious trade-offs. Avoid explaining basic language concepts, standard library methods, or generic patterns (zero token waste).
2. **Isolation First (Sandbox)**: Never modify production rules or active prompt contracts directly. All optimization candidates must run in isolated sandboxed directories.
3. **Evidence-Led Adaptability**: No adaptation can be promoted without quantitative proof of improvement (e.g., higher validation scores, reduced token footprints, or resolved test failures).
4. **Zero-Regression Safety**: Existing working scenarios, guardrails, and constraints must not be broken by the newly adapted skill.

---

## Multi-Phase Self-Evolution Workflow

Follow this structured, closed-loop workflow whenever optimizing a skill.

### Phase 1: Benchmark and Baseline Capture
- **Triggers**: Trigger when a user requests optimization, a test case fails, or new playbook edge cases are identified.
- **Trace Collection**: Review recent execution traces and log errors related to the target skill.
- **Baseline Scoring**: Run the existing skill against the current validation suite (or standard test inputs) and record the baseline metrics:
  - **Accuracy / Score**: Success rates, error counts.
  - **Token Volume**: Total tokens consumed by the skill prompt.
  - **Execution Latency**: Time to complete the evaluation run.

### Phase 2: Sandboxed Workspace Isolation
- **Isolation Directory**: Create a temporary folder inside the workspace:
  ```text
  billionary-trader/skillset/cross-evolve-skill/.tmp_evolve_<target_skill>_<timestamp>/
  ```
- **Asset Replication**: Copy the target skill folder's contents (`skill.md`, scripts, tests, assets) to the temporary folder.
- **Independence**: Ensure any local tests run within the sandbox use the sandboxed skill version and do not read/write to the production paths.

### Phase 3: Adaptive Vectors (Generation)
Apply targeted adaptation techniques based on the optimization goals:
- **Redundancy Pruning**: Scan the skill for generic tutorials, explanations, or definitions. Replace them with compact, action-oriented directives.
- **Rule Generalization**: Update the decision logic to accommodate new edge cases or failures observed in the baseline run.
- **Parameter Adaptation**: Refine threshold metrics, DTE ranges, size limits, or priority weights.
- **Structural Formatting**: Refine formatting into tables, checklists, or Mermaid diagrams to make the skill easier for the LLM to parse cleanly and quickly.

### Phase 4: Multi-Dimensional Evaluation
Evaluate the sandboxed candidate using the identical scenarios from Phase 1. Score across three dimensions:

| Dimension | Goal | Metric |
|---|---|---|
| **Functional Score** | Equal or superior performance | Pass/fail rate, accuracy metrics, edge case resolution |
| **Token Efficiency** | Higher information density | Prompt token count reduction (%) |
| **Safety Compliance** | Zero violation of active guardrails | Absence of unauthorized actions or formatting drift |

### Phase 5: Comparative Analysis and Review
- **Diff Generation**: Produce a clean markdown diff showing changes between the baseline and the candidate.
- **Scoring Summary**: Summarize the performance differences (e.g., "+10% accuracy, -15% token usage").
- **Human-in-the-loop (HITL)**: Present the diff and tradeoff analysis to the user. Do not promote any candidate to production without explicit user confirmation.

### Phase 6: Atomic Promotion & Rollback Setup
Once approved:
1. Locate the production folder of the target skill.
2. If a `.prev` folder already exists under that path, delete it (garbage collection of older backups).
3. Move the current active skill folder to `.prev`.
4. Move the sandboxed candidate folder to the active skill folder's path.
5. Run a final verification test on the newly promoted production skill. If any regression is observed, immediately rollback (restore from `.prev`).

### Phase 7: Garbage Collection
- Clean up and delete the temporary `.tmp_evolve_...` directories.
- Confirm only a single `.prev` backup folder remains in the target skill folder.

---

## Anti-Patterns (What NEVER to Do)

- **NEVER** modify a skill directly in the active production folder without first validating it in a sandbox.
- **NEVER** introduce explanations of basic concepts (e.g., "What is an option", "How to write Python") to keep token overhead low.
- **NEVER** bypass manual review and approval gates for production promotion.
- **NEVER** keep multiple legacy backup directories (e.g., `.prev_v1`, `.prev_v2`, `backup_old`). Keep exactly one `.prev` folder per skill.
- **NEVER** perform cross-project modifications during a single skill evolution run unless the user explicitly requests integration updates.
- **NEVER** assume a single metric optimization is sufficient if it degrades safety or increases latency significantly.

---

## Evolution Report Template

When requesting approval for a skill promotion, present the information in this format:

```markdown
### Skill Evolution Report: [Target Skill Name]

#### Performance Comparison
- **Functional Score**: [Baseline Score] -> [Candidate Score] ([change])
- **Token Count**: [Baseline Tokens] -> [Candidate Tokens] ([change])
- **Validation Status**: [PASS / FAIL]

#### Key Changes (Diff Summary)
- [Brief bullet points explaining the additions, modifications, or prunings]

#### Sandboxed Validation Artifacts
- **Diff Path**: `[Path to diff markdown]`
- **Logs**: `[Path to sandboxed run logs]`
```