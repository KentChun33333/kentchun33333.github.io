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
- For an architecture migration, refactoring, or version diff, read [reference/topology-migration-diff.md](reference/topology-migration-diff.md).

When the requested output is an interactive research-insight HTML artifact, also read [reference/web-insight-artifact.md](reference/web-insight-artifact.md). When the study proposes or compares a framework with multiple components, controls, or ablations, apply the contribution-simulator standard in [reference/contribution-simulator.md](reference/contribution-simulator.md). Use a descriptive kebab-case filename rather than `index.html` unless the user explicitly requests a site root.

## Automation and Code Engine

Use the bundled Python engine in `scripts/engine.py` to accelerate execution and eliminate manual errors:

- `python3 skills/knowledge-distill/scripts/engine.py scaffold <raw_dir> <project_dir>` — automatically catalog raw sources into `data-cooked/source-index.md` and generate template cooked stubs.
- `python3 skills/knowledge-distill/scripts/engine.py diagram --input "..." --module "..." --output "..."` — format aligned 3-column ASCII stacking contract diagrams.
- `python3 skills/knowledge-distill/scripts/engine.py manifest <project_dir>` — compile `knowledge/manifest.json` for downstream agents.
- `python3 skills/knowledge-distill/scripts/engine.py guard <project_dir>` — run automated quality gate and citation integrity checks.
- `python3 skills/knowledge-distill/scripts/engine.py evaluate <project_dir> --write` — score output on 7 IQ dimensions and save `analysis/iq-training-evaluation.md`.
- `python3 skills/knowledge-distill/scripts/engine.py audit-all <project_dir> --write` — execute full guardian, evaluation, and manifest pipeline.

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

Apply [reference/quality-gates.md](reference/quality-gates.md) before delivery. Run `python3 skills/knowledge-distill/scripts/engine.py audit-all <project_dir> --write` to verify structural contracts, zero hallucinated citations, absence of forbidden mermaid markdown blocks, and high token density. For interactive HTML, also run the validation and interaction checks required by the web-artifact reference and any selected demo-building skill. Declare whether a contribution simulator is included or not applicable; the guardian validates the declaration, evidence-status labeling, and required simulator marker.

When user feedback reveals a reusable process failure, follow [reference/feedback-evolution.md](reference/feedback-evolution.md) and update [reference/skill-evolution-ledger.md](reference/skill-evolution-ledger.md).
