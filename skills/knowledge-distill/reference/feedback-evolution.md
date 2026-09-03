# Feedback-Driven Guarded Skill Evolution

Use this when the user critiques a completed distillation, reports deliverable defects, or explicitly requests a reusable skill modification.

Always invoke the **Guarded Skill Evolution (GSE) Hook** in `../SKILL.md` and follow [reference/guarded-skill-evolution.md](guarded-skill-evolution.md). Skill evolution is a selective intervention problem—never default to an automatic skill rewrite.

---

## 1. Feedback Triage and Attribution Matrix

Before editing any code or prompt, classify the feedback across the 8 candidate failure owners. Do not assume the skill instructions caused the defect.

Output: `analysis/feedback-log.md`

| Feedback Item | Affected Output / ID | Observed Symptom | True Failure Owner (`skill`, `routing`, `tool`, `data`, `model`, `evaluator`, `spec`, `noise`) | Selected Intervention (`clarify`, `revise-skill`, `repair-other`, `retain`) | Action / Correction |
|---|---|---|---|---|---|

### Attribution Rules:
1. **`tool` or `routing` owner:** If execution failed in a deterministic script, parser, or event trigger, repair the tool or routing directly. **Do not modify the skill** to mask an underlying tool defect.
2. **`spec` owner:** If the feedback reveals conflicting or underspecified requirements, walk the decision-frontier design tree ("Grilling") to clarify rather than guessing.
3. **`noise` owner:** If the failure cannot be reproduced on matched reruns, retain the incumbent and monitor.
4. **`skill` owner:** Proceed to Change Contract generation and paired candidate evaluation only when procedural instructions are genuinely absent or incorrect.

---

## 2. Common Error Patterns

- **Boundary ambiguity:** Unclear what is updated, frozen, demonstrated, inferred, or recommended.
- **Output duplication:** Repeated explanations reduce information density.
- **Evidence weakness:** Claim lacks source ID or confidence label.
- **Missing invalidation:** Recommendation lacks falsification test.
- **Shallow reasoning:** Summary lacks mechanism, causal chain, failure mode, or second-order implication.
- **Oversized output:** Artifact set is larger than useful payload.
- **Code-example ambiguity:** Example does not clarify frozen, updated, trainable, omitted, or conceptual parts.
- **Implementation readiness gap:** Metrics are named but no scorecard or collection schema is provided.

---

## 3. IQ-Style Review Structure

Output: `analysis/iq-training-evaluation.md`

1. **Working-memory scratchpad:** Objective, facts, variables, constraints, hypothesis, confidence.
2. **Independent assessment:** Score key dimensions (Structure, Flow, Provenance, Invalidation, Causality, Density, Executability).
3. **Red-team critique:** Assumptions, weak evidence, duplication, missing boundaries, invalidation gaps.
4. **Revised assessment:** Updated score after critique.
5. **Error journal:** Failure pattern, root cause, failure owner, corrective rule.
6. **Extracted principles:** General rules for future distillations.

---

## 4. GSE Patch Order

1. **Conduct Decision-Frontier Grilling:**
   - Resolve Root Intent (downstream outcome and beneficiary).
   - Investigate facts autonomously (agent checks logs, test cases, code paths).
   - Elicit user constraints and non-negotiable hard invariants.
2. **Diagnose Failure Owner:**
   - Confirm whether the issue is `skill`, `tool`, `routing`, `data`, `model`, `evaluator`, `spec`, or `noise`.
   - If non-skill, repair that component and verify delivery.
3. **Patch Deliverable First:**
   - Patch the specific task output and rerun its assigned evaluator to confirm local satisfaction.
4. **Draft Falsifiable Change Contract:**
   - If and only if the failure generalizes and the owner is `skill`, draft `change-contract.yaml` (`problem`, `objective`, `invariants`, `proposed_change`, `minimal_scope`).
   - Validate with `python3 skills/knowledge-distill/scripts/task_contract.py validate-change-contract <change-contract.yaml>`.
5. **Isolate Sandboxed Candidate ($s' = s_0 + \Delta$):**
   - Apply minimal edits adhering strictly to the contract scope budget.
6. **Paired 4-Slice Empirical Gate:**
   - Run baseline $s_0$ and candidate $s'$ under identical conditions across:
     - *Source repair* (triggering tasks),
     - *Target generalization* (unseen held-out tasks),
     - *Regression preservation* (existing capabilities and hard invariants),
     - *Challenge cases* (boundary and adversarial inputs).
7. **Promotion Verification:**
   - Require lower confidence bound improvement $> \delta$, critical regression rate $\le \rho$, and 100% hard invariant adherence.
   - Present diff and impact analysis for explicit human confirmation.
8. **Record in Evolution Ledger:**
   - Document the promotion in [`reference/skill-evolution-ledger.md`](skill-evolution-ledger.md) with rollback pointers.
