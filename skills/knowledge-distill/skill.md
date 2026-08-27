# Knowledge Distill Skill

> **Audience**: Analysts · Researchers · Product Managers · Engineers · Business Leaders  
> **Purpose**: Convert raw sources into clear, evidence-grounded knowledge artifacts with traceable reasoning, boundaries, and reusable outputs.  
> **Worked Example**: [example/walkthrough.md](example/walkthrough.md)

This main skill is intentionally short. Load the referenced modules only as needed.

## Core Principle

Knowledge distillation follows this priority order:

1. Flow first: understand the real workflow, lifecycle, system movement, or thought process.
2. Terms second: extract vocabulary only after flow gives terms operational meaning.
3. Evidence always: do not invent missing facts; mark weak, contradictory, or absent evidence.
4. Boundaries before recommendations: distinguish demonstrated results, inferences, design implications, and open questions.

## Output Location

For `agent-learner`, write outputs under:

```text
openmemo/agent-learner/output/[project-folder]/
```

Use the folder contract in [reference/folder-contract.md](reference/folder-contract.md).

## Choose The Input Topology

Select the topology before analysis. Different inputs require different reasoning structure.

| Input condition | Use topology | Reasoning focus |
|---|---|---|
| Code repo / implementation folder | [reference/topology-code-repo.md](reference/topology-code-repo.md) | Entrypoints, modules, runtime flow, contracts, tests, extension points |
| Research paper / technical report | [reference/topology-paper.md](reference/topology-paper.md) | Question, assumptions, method, experiments, evidence, limitations, implications |
| Heterogeneous corpus: PDFs, text, email, chats, reports | [reference/topology-heterogeneous-corpus.md](reference/topology-heterogeneous-corpus.md) | Source clustering, timeline, actor intent, contradictions, insight synthesis |

If the input mixes topologies, pick the dominant one and add secondary sections from the others.

## Standard Loops

Follow the six-loop process in [reference/core-loops.md](reference/core-loops.md):

1. Discover.
2. Define cook spec.
3. Cook raw sources.
4. Analyze.
5. Produce reusable knowledge.
6. Evolve the skill from feedback when review reveals a generalizable failure.

## Quality Gates

Use [reference/quality-gates.md](reference/quality-gates.md) before finalizing.

Minimum requirements:

- Stable source IDs.
- Cooked sources with provenance.
- Flow, dependency, terminology, evidence map.
- Boundary and invalidation analysis for practical recommendations.
- Read order for multi-file outputs.
- IQ-style evaluation when the user asks for critique or quality review.
- Activation/adherence scorecard for agent, harness, skill, memory, tool, or long-horizon execution topics.

## Feedback Evolution

When user feedback exposes a recurring process failure, use [reference/feedback-evolution.md](reference/feedback-evolution.md):

- Capture feedback.
- Classify the error pattern.
- Patch the current output.
- Patch this skill only if the rule generalizes.
- Record the skill change in a ledger.

## Example And Visuals

- **Worked Example**: [example/walkthrough.md](example/walkthrough.md) illustrates the full 5-loop execution, showing cooked output, flow analysis, and dependencies.
- **Charts & Diagrams**: Mermaid diagrams are forbidden; all charts must use clean ASCII art. For overall workflows, use a stacked layout with input data contracts on the left, core modules in the center, and output data contracts on the right (`input -> module -> output`). See [example/walkthrough.md](example/walkthrough.md) for a concrete layout.
- Diagrams are visual companions and must not introduce unsupported claims.
- Example code must clearly mark frozen assets, updated assets, trainable assets, omitted mechanisms, and whether it is conceptual or implementation-ready.

