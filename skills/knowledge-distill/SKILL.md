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

## Guarded skill-evolution hook (GSE & Grilling)

Trigger this hook when the user explicitly asks to modify, optimize, evolve, or add a reusable rule to a skill, or when deliverable critique reveals a reusable process defect. Never mutate a persistent skill file automatically. Follow the complete specification in [reference/guarded-skill-evolution.md](reference/guarded-skill-evolution.md).

Before modifying any skill or rule:

1. **Conduct Decision-Frontier Elicitation ("Grilling").**
   - Walk the dependency design tree without premature questions. The next frontier $F_t$ contains only decisions whose prerequisites are settled.
   - **Round 01 (Root Intent):** Establish the true objective, beneficiary, and downstream decision.
   - **Round 02 (First Frontier):** Identify the observed gap, collect failure traces, and register non-negotiable hard invariants.
   - **Round 03 (Derived Frontier):** Attribute the true failure owner, define the minimum meaningful gain $\delta$, and bound the permitted edit scope.
   - **Round 04 (Confirmation Gate):** Synthesize the answers into a testable Change Contract and obtain explicit user confirmation before touching files.
   - **Cost-aware stopping rule:** Stop asking when $\text{ExpectedDecisionValue}(F_t) \le \text{interaction cost}$. If the user already provided the required criteria, acknowledge them directly—never manufacture an unnecessary interview.
2. **Strictly Separate Facts from Decisions.**
   - **Agent-investigated facts:** The agent must inspect execution traces, logs, git history, tools, routing delivery fingerprints, and file structures directly. Never ask the user for facts the agent can ascertain from the environment.
   - **User-owned decisions:** Elicit intended utility, trade-offs between competing metrics, acceptable risk tolerance, and hard invariants from the user.
3. **Attribute the True Failure Owner.**
   Diagnose the failure across the 8 candidate owners: `skill` (procedural gap), `routing` (delivery failure), `tool` (adapter/parser bug), `data` (malformed input), `model` (carrier capability limit), `evaluator` (scoring artifact), `spec` (unresolved user trade-off), or `noise` (non-reproducible run).
   - If owner is `routing` or `tool`, repair that layer directly and **keep the skill intact** (do not bloat instructions to mask tool or routing bugs).
   - If owner is `spec`, clarify via the decision frontier.
   - If owner is `noise` or unproven, retain the incumbent and monitor.
   - Proceed to skill revision **only** when the procedural instruction itself is causal.
4. **Draft and Validate a Falsifiable Change Contract.**
   Produce a structured contract (`problem`, `objective`, `invariants`, `proposed_change`, `minimal_scope`). Validate it with `python3 skills/knowledge-distill/scripts/task_contract.py validate-change-contract <change-contract.yaml>`.
5. **Enforce Paired 4-Slice Evaluation Before Promotion.**
   For substantial changes, generate a sandboxed candidate $s' = s_0 + \Delta$ following [the cross-evolve workflow](../cross-evolve-skill/skill.md). Evaluate incumbent and candidate under identical seeds, tools, and model conditions across:
   - *Source repair* (triggering cases),
   - *Target generalization* (unseen held-out tasks),
   - *Regression preservation* (existing capabilities & hard invariants),
   - *Challenge cases* (edge/boundary inputs).
   Promote $s'$ only if lower confidence bound improvement exceeds $\delta$, critical regression rate $\le \rho$, and all hard invariants hold. Record the outcome in [reference/skill-evolution-ledger.md](reference/skill-evolution-ledger.md).

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

When the requested output is an interactive research-insight HTML artifact, also read [reference/web-insight-artifact.md](reference/web-insight-artifact.md). When the study proposes or compares a framework with multiple components, controls, or ablations, apply the contribution-simulator standard in [reference/contribution-simulator.md](reference/contribution-simulator.md). Use a descriptive kebab-case filename rather than `index.html` unless the user explicitly requests a site root.

## Automation and Code Engine

Use the bundled Python engine in `scripts/engine.py` to accelerate execution and eliminate manual errors:

- `python3 skills/knowledge-distill/scripts/engine.py scaffold <raw_dir> <project_dir>` — automatically catalog raw sources into `data-cooked/source-index.md` and generate template cooked stubs.
- `python3 skills/knowledge-distill/scripts/engine.py diagram --input "..." --module "..." --output "..."` — format aligned 3-column ASCII stacking contract diagrams.
- `python3 skills/knowledge-distill/scripts/engine.py manifest <project_dir>` — compile `knowledge/manifest.json` for downstream agents.
- `python3 skills/knowledge-distill/scripts/engine.py guard <project_dir>` — run automated quality gate and citation integrity checks.
- `python3 skills/knowledge-distill/scripts/engine.py evaluate <project_dir> --write` — score output on 7 IQ dimensions and save `analysis/iq-training-evaluation.md`.
- `python3 skills/knowledge-distill/scripts/engine.py audit-all <project_dir> --write` — execute full guardian, evaluation, and manifest pipeline.
- `python3 skills/knowledge-distill/scripts/task_contract.py validate <task-config.json>` — validate deliverable-to-skill and deliverable-to-evaluator bindings.
- `python3 skills/knowledge-distill/scripts/task_contract.py validate-change-contract <change-contract.json|yaml>` — validate Guarded Skill Evolution change contract, failure owner, and invariants.
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

Apply [reference/quality-gates.md](reference/quality-gates.md) before delivery. Run `python3 skills/knowledge-distill/scripts/engine.py audit-all <project_dir> --write` to verify structural contracts, zero hallucinated citations, absence of forbidden mermaid markdown blocks, and high token density. For interactive HTML, also run the validation and interaction checks required by the web-artifact reference and any selected demo-building skill. Declare whether a contribution simulator is included or not applicable; the guardian validates the declaration, evidence-status labeling, and required simulator marker.

When user feedback reveals a reusable process failure, follow [reference/feedback-evolution.md](reference/feedback-evolution.md) and update [reference/skill-evolution-ledger.md](reference/skill-evolution-ledger.md).
