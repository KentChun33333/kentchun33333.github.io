# Feedback-Driven Skill Evolution

Use this when the user critiques a completed distillation or one of its deliverables.

Also use it when the user explicitly requests a reusable skill modification. In that case, run the **Skill-modification intent hook** in `../SKILL.md` before editing: establish intention and exclusions, expose current practice, map potential impacts, and classify the change as bounded or substantial.

For substantial changes, use an isolated version-controlled candidate following the principles in `../../cross-evolve-skill/skill.md`. Freeze the baseline and evaluation conditions, compare the candidate under the same conditions, present the diff and impact analysis, and obtain explicit user approval before promotion. For bounded changes, a narrow direct patch is acceptable after the intent and impact review, followed by validation and ledger entry.

## Feedback Capture

Output:

- `analysis/feedback-log.md`

Suggested table:

```md
| Feedback | Affected Output | Failure Pattern | Severity | Skill Update Needed? | Correction |
|---|---|---|---|---|---|
```

## Error Patterns

- Boundary ambiguity: unclear what is updated, frozen, demonstrated, inferred, or recommended.
- Output duplication: repeated explanations reduce density.
- Evidence weakness: claim lacks source ID or confidence label.
- Missing invalidation: recommendation lacks falsification test.
- Shallow reasoning: summary lacks mechanism, causal chain, failure mode, or second-order implication.
- Oversized output: artifact set is larger than useful payload.
- Code-example ambiguity: example does not clarify frozen, updated, trainable, omitted, or conceptual parts.
- Implementation readiness gap: metrics are named but no scorecard or collection schema is provided.

## IQ-Style Review

Output:

- `analysis/iq-training-evaluation.md`

Structure:

1. Working-memory scratchpad: objective, facts, variables, constraints, hypothesis, confidence.
2. Independent assessment: score key dimensions.
3. Red-team critique: assumptions, weak evidence, duplication, missing boundaries, invalidation gaps.
4. Revised assessment: updated score after critique.
5. Error journal: failure pattern, root cause, corrective rule.
6. Extracted principles: general rules for future distillations.

## Patch Order

1. Run the skill-modification intent hook when reusable skill behavior is explicitly in scope.
2. Record feedback against the affected deliverable ID and its current evaluation profile.
3. Convert requested functions or effects into explicit evaluation rules for the next contract revision.
4. Patch the current output first and rerun that deliverable's assigned evaluator.
5. Patch the builder or evaluator skill only when the failure generalizes across tasks.
6. For substantial or controlled evolution, keep held-out tasks separate and compare the isolated candidate against the baseline under one frozen contract fingerprint.
7. Present the candidate diff and impact analysis and obtain explicit approval before promoting a substantial change.
8. Record generalized skill changes in `reference/skill-evolution-ledger.md`.

Do not average scores across different deliverable types or profile versions. User feedback is valid optimization data, but a preference observed on one artifact is not evidence of generalization until it improves held-out tasks without regression.

## Skill Evolution Ledger

```md
| Date | Feedback | Skill Rule Added | Files Updated |
|---|---|---|---|
```
