# Topology: Research Paper Input

Use this flow when the input is a paper, preprint, technical report, thesis, benchmark paper, or academic PDF.

## Reasoning Topology

```text
research question
  -> assumptions
  -> method / algorithm
  -> experimental design
  -> evidence and results
  -> limitations
  -> implications
  -> invalidation tests
```

## Required Analysis Emphasis

- Problem statement and why it matters.
- Definitions and formal objects.
- Method or algorithm steps.
- Experimental setup: datasets, models, baselines, metrics, controls.
- Results: headline numbers, variance, ablations, case studies.
- Limitations and ethics.
- Distinguish demonstrated results from design recommendations.
- Related-work candidates must not be presented as validated winners unless evaluated.

## Output Preferences

Add or emphasize:

- `analysis/core-thought-model.md`
- `analysis/evidence-map.md`
- `analysis/boundaries-and-invalidation.md`
- `knowledge/algorithm-reference.md` when the paper proposes an algorithm.
- `knowledge/implementation-notes.md` when the paper can inform implementation.
- `knowledge/example-code.py` only as conceptual unless production details are sourced.

## Boundary Checks

- What is directly evaluated?
- What is recommended but not evaluated?
- What is only related work?
- What data or benchmark limits generalization?
- What source code or artifact is linked but not audited?

## Invalidation Tests

- A method claim is weakened if local tasks violate the paper's assumptions.
- A benchmark conclusion is weakened if a new model/task family changes the ranking.
- A design recommendation is unproven until tested as an intervention.

