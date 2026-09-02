# Feedback-Driven Skill Evolution

Use this when the user critiques a completed distillation.

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

1. Patch the current output first.
2. Patch the skill only when feedback generalizes.
3. Record skill changes in `reference/skill-evolution-ledger.md`.

## Skill Evolution Ledger

```md
| Date | Feedback | Skill Rule Added | Files Updated |
|---|---|---|---|
```


