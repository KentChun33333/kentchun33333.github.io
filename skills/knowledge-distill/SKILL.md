---
name: knowledge-distill
description: Distill code repositories, papers, and mixed source corpora into evidence-grounded knowledge artifacts that expose workflow, mechanisms, dependencies, components, algorithms, code references, boundaries, and reusable implementation lessons. Use for technical research studies and named AI-research insight HTML pages; do not use for surface-level summaries.
---

# Knowledge Distill

Turn raw sources into compact, traceable knowledge. Flow comes first, terminology second, evidence always, and recommendations only after boundaries and invalidation conditions are explicit.

## Select the input topology

- For a code repository, read [reference/topology-code-repo.md](reference/topology-code-repo.md).
- For a paper, read [reference/topology-paper.md](reference/topology-paper.md).
- For a heterogeneous corpus, read [reference/topology-heterogeneous-corpus.md](reference/topology-heterogeneous-corpus.md).

When the requested output is an interactive research-insight HTML artifact, also read [reference/web-insight-artifact.md](reference/web-insight-artifact.md). Use a descriptive kebab-case filename rather than `index.html` unless the user explicitly requests a site root.

## Execute the distillation

Follow [reference/core-loops.md](reference/core-loops.md): discover, define the cook specification, cook sources with stable IDs, analyze the runtime flow and dependencies, produce reusable knowledge, then evolve the skill when review exposes a general failure.

For code repositories, verify claims against implementation rather than filenames or README prose. Required analysis includes:

- entrypoints and runtime order;
- data and control flow;
- module ownership and contracts;
- algorithmic mechanisms and state transitions;
- dependencies, failure modes, tests, and extension points;
- exact code paths and small source-grounded snippets when they improve transfer.

Distinguish demonstrated implementation, inference, recommendation, planned behavior, and open questions. Give each major recommendation an invalidation test.

## Validate

Apply [reference/quality-gates.md](reference/quality-gates.md) before delivery. For interactive HTML, also run the validation and interaction checks required by the web-artifact reference and any selected demo-building skill.

When user feedback reveals a reusable process failure, follow [reference/feedback-evolution.md](reference/feedback-evolution.md) and update [reference/skill-evolution-ledger.md](reference/skill-evolution-ledger.md).
