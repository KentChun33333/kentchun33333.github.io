---
name: knowledge-distill
description: Distill code repositories, papers, and mixed source corpora into an evidence-grounded knowledge package, then route requested deliverables to compatible builder and evaluator skills. Use for technical studies and multi-deliverable knowledge workflows; do not use for surface-level summaries.
---

# Knowledge Distill

Turn raw sources into compact, traceable knowledge. Flow comes first, terminology second, evidence always, and recommendations only after boundaries and invalidation conditions are explicit.

## Design principles

Use this operating model:

```text
dataset  ──→ direct LLM baseline ─────────────────────────→ deliverable
   │
   └────→ conditional preparation ─→ knowledge package ─→ specialist builder ─→ deliverable
                 │                                                │
                 └─ native engine / optional Graphify             └─ assigned evaluator
```

The prepared path is a hypothesis, not an assumed improvement. It is better only when the same deliverable evaluated under the same rules scores higher than the direct baseline.

1. **Contract before processing.** Establish input data, objective, audience, deliverables, and evaluation bindings before substantial work. Infer known values and ask only for consequential gaps.
2. **Prepare according to input conditions.** Choose native parsing, optional Graphify, semantic retrieval, or direct reading based on corpus topology and scale. No accelerator is mandatory, and unavailable optional infrastructure must degrade cleanly.
3. **Automate deterministic work.** Use scripts for inventory, parsing, graph extraction, normalization, hashing, validation, and scoring when code can perform the operation reliably. Reserve model context for interpretation and synthesis.
4. **Use one normalized knowledge boundary.** Builders consume `knowledge/manifest.json` and its referenced artifacts rather than repeatedly rereading the raw corpus. Preserve stable source IDs, provenance, confidence, boundaries, and artifact hashes.
5. **Delegate deliverables to specialists.** Knowledge Distill prepares and routes knowledge; it does not absorb the implementation rules of web, diagram, document, presentation, or other builder skills.
6. **Bind one evaluator to every deliverable.** Evaluation selection follows the objective, audience, deliverable type, requested functions, and observable effects. Score multiple deliverables separately; never hide weakness with an aggregate across unlike outputs.
7. **Evaluate intended effects, not feature presence.** A button, animation, chart, or agent label counts only when it deliberately demonstrates the function or effect requested in the contract.
8. **Compare under frozen conditions.** Baseline and candidate must share the input fingerprint, deliverable contract, evaluator version and rules, model/tool conditions, and budgets. Otherwise report results independently rather than claiming improvement.
9. **Use feedback as versioned data.** User feedback can revise the next task contract and guide another build-evaluate iteration. Promote a skill change only when the failure generalizes and held-out tasks improve without regression.
10. **Refine progressively.** Work from high-level topology to detailed mechanisms and then implementation-level evidence. Each pass should increase useful precision without duplicating canonical explanations.

## Skill-modification intent hook

Trigger this hook when the user explicitly asks to modify, optimize, evolve, or add a reusable rule to a skill. Do not trigger it for an ordinary deliverable correction unless the user also asks to change the reusable skill.

Before editing the skill:

1. **Interrogate the intention.** Restate the desired future behavior, the problem it should prevent, the tasks it should apply to, and the tasks it should not affect. Challenge ambiguous universality, hidden exceptions, and whether the request is a personal preference or a generally useful rule. Ask pointed questions only for consequential gaps; do not ask the user to repeat settled intent.
2. **Expose current practice.** Quote or summarize the exact active rule, routing behavior, evaluator expectation, and relevant implementation path. Say whether the requested behavior is absent, weaker, conflicting, or already partially implemented.
3. **Map potential impacts.** Explain likely benefits and trade-offs across task routing, builder outputs, evaluator gates, scripts/tests, backward compatibility, token or execution cost, and unrelated task classes. Identify which files and contracts would change before changing them.
4. **Classify the change.** Treat a change as substantial when it alters skill activation or routing, affects multiple skills or evaluators, changes schemas or automation, weakens a safety/quality gate, requires migration, or may change behavior for unrelated tasks. Everything else may use the bounded direct-patch path.

For a bounded change, present the intention/current-practice/impact assessment, apply the narrow patch, validate the affected skill, and record the change in the evolution ledger.

For a substantial change, read and adapt [the cross-evolve workflow](../cross-evolve-skill/skill.md). Create an isolated version-controlled candidate, freeze and record a baseline, run the same tests or evaluation cases against baseline and candidate, produce a diff and impact report, and request explicit user approval before promotion. Preserve a rollback point and verify the promoted version. Use the workflow's principles; do not copy project-specific paths or destructive backup steps blindly.

The hook is a decision-quality gate, not permission to broaden scope. If the user has already supplied the intention, boundaries, and acceptable impacts, acknowledge those answers and proceed rather than manufacturing an interview.

## Establish the task contract

Before substantial work, create or resolve `task-config.json` using [reference/task-contract.md](reference/task-contract.md). The minimum contract identifies input data, objective, audience, and one or more deliverables. Every deliverable must resolve to an implementation skill and its own evaluation profile through [reference/deliverable-registry.json](reference/deliverable-registry.json).

Use the deterministic helper instead of manually normalizing the contract:

```bash
python3 skills/knowledge-distill/scripts/task_contract.py resolve task-config.json --write task-config.resolved.json
python3 skills/knowledge-distill/scripts/task_contract.py route task-config.resolved.json
```

Ask only for consequential fields that remain missing. Multiple deliverables remain separate jobs with separate outputs and scores.

## Select the input topology

- For a code repository, read [reference/topology-code-repo.md](reference/topology-code-repo.md).
- For a paper, read [reference/topology-paper.md](reference/topology-paper.md).
- For a heterogeneous corpus, read [reference/topology-heterogeneous-corpus.md](reference/topology-heterogeneous-corpus.md).
- For an architecture migration, refactoring, or version diff, read [reference/topology-migration-diff.md](reference/topology-migration-diff.md).

When the selected output is a web deliverable, delegate it to the skill named in the resolved task contract. The `web` skill handles research sites and system demos; `build-async-agentic-web-demo` handles agentic demos. Do not reproduce those implementation instructions inside this skill.

## Automation and Code Engine

Use the bundled Python engine in `scripts/engine.py` to accelerate execution and eliminate manual errors:

- `python3 skills/knowledge-distill/scripts/engine.py scaffold <raw_dir> <project_dir>` — automatically catalog raw sources into `data-cooked/source-index.md` and generate template cooked stubs.
- `python3 skills/knowledge-distill/scripts/engine.py diagram --input "..." --module "..." --output "..."` — format aligned 3-column ASCII stacking contract diagrams.
- `python3 skills/knowledge-distill/scripts/engine.py manifest <project_dir>` — compile `knowledge/manifest.json` for downstream agents.
- `python3 skills/knowledge-distill/scripts/engine.py guard <project_dir>` — run automated quality gate and citation integrity checks.
- `python3 skills/knowledge-distill/scripts/engine.py evaluate <project_dir> --write` — score output on 7 IQ dimensions and save `analysis/iq-training-evaluation.md`.
- `python3 skills/knowledge-distill/scripts/engine.py audit-all <project_dir> --write` — execute full guardian, evaluation, and manifest pipeline.
- `python3 skills/knowledge-distill/scripts/task_contract.py validate <task-config.json>` — validate deliverable-to-skill and deliverable-to-evaluator bindings.
- `python3 skills/knowledge-distill/scripts/task_contract.py route <task-config.json>` — detect whether optional Graphify and semantic retrieval are useful without installing either.
- `python3 skills/knowledge-distill/scripts/graphify_accelerator.py <task-config.json>` — print the optional Graphify execution plan; add `--execute` only after the resolved strategy selects it.

Read [reference/optional-accelerators.md](reference/optional-accelerators.md) only when routing selects Graphify or semantic retrieval.

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

Apply [reference/quality-gates.md](reference/quality-gates.md) before delivery. Run `python3 skills/knowledge-distill/scripts/engine.py audit-all <project_dir> --write` to verify structural contracts, zero hallucinated citations, absence of forbidden mermaid markdown blocks, and high token density. For each deliverable, invoke the evaluation skill and exact profile recorded in the resolved task contract. Compare a baseline and candidate only when the input, requested deliverable, evaluation rules, model conditions, and budget are the same.

When user feedback reveals a reusable process failure, or the user explicitly requests a skill modification, follow [reference/feedback-evolution.md](reference/feedback-evolution.md) and update [reference/skill-evolution-ledger.md](reference/skill-evolution-ledger.md).
