---
name: evaluate-web-deliverable
description: Evaluate research sites, system demos, and agentic web demos against the exact objective, audience, functions, effects, and profile recorded in a Knowledge Distill task contract. Use for feedback iterations or controlled baseline-versus-candidate comparisons.
---

# Evaluate Web Deliverable

Evaluate the selected artifact, not an abstract idea of a good website. The task contract is authoritative: the objective, audience, required claims, functions, observable effects, and assigned profile define success.

## Freeze comparability

Before a baseline/candidate comparison, freeze:

- input dataset and source revision;
- deliverable entry and evaluation rules;
- evaluation profile version;
- model and tool conditions;
- token, time, and retry budgets.

Reject a comparison when these differ. Evaluate each deliverable separately even when one task produces several files.

## Select the assigned profile

Read only the matching profile in [references/profiles.md](references/profiles.md). Profile definitions and weights are machine-readable in [references/profiles.json](references/profiles.json).

## Run three evaluation layers

1. **Deterministic preflight** — structure, required content, unique IDs, accessibility hooks, responsive metadata, and contract bindings.
2. **Behavioral observation** — operate every requested function and record whether its promised effect is deliberately and visibly produced. Use a browser when behavior cannot be proven statically.
3. **Quality judgment** — score only the dimensions in the assigned profile, citing visible artifact or source evidence for each score.

Use [references/judgment-schema.json](references/judgment-schema.json) for behavioral observations and quality scores. A result without behavioral observations and evidence-backed rubric scores is provisional and cannot promote a skill.

## Automate scoring

```bash
python3 skills/evaluate-web-deliverable/scripts/evaluate_web.py audit \
  --contract task-config.resolved.json \
  --deliverable <deliverable-id> \
  --artifact path/to/output.html \
  --judgment path/to/judgment.json \
  --write evaluation.json
```

Compare two completed evaluations:

```bash
python3 skills/evaluate-web-deliverable/scripts/evaluate_web.py compare baseline.json candidate.json
```

The candidate wins only if both evaluations share a contract fingerprint and profile, all hard gates pass, and its total score is higher. User feedback can inform the next iteration, but changing rules creates a new contract revision rather than rewriting the previous result.
