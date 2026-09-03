# Folder Contract

## Agent-Learner Output Rule

For `agent-learner`, all knowledge-distill outputs must be placed under:

```text
openmemo/agent-learner/output/[project-folder]/
```

## Standard Project Layout

```text
[project-folder]/
  data-raw/
    urls.txt
    [raw files or source pointers]

  data-cooked/
    source-index.md
    source-001.md
    source-002.md

  analysis/
    discovery.md
    parse-plan.md
    flow.md
    dependency.md
    terminology.md
    core-thought-model.md
    evidence-map.md
    boundaries-and-invalidation.md
    open-questions.md
    iq-training-evaluation.md

  knowledge/
    manifest.json
    read-order.md
    executive-summary.md
    big-picture.md
    domain-reference.md
    workflow-reference.md
    system-model.md
    activation-adherence-scorecard.md
    diagrams/
```

## Rules

- Treat `data-raw/` as immutable.
- Write extracted readable Markdown to `data-cooked/`.
- Write intermediate reasoning to `analysis/`.
- Write reusable artifacts to `knowledge/`.
- Preserve source IDs across every stage.
- Use one canonical explanation per concept; cross-reference instead of duplicating.
- Treat `knowledge/manifest.json` as the stable handoff to deliverable skills. Schema version 2 includes the resolved objective, audience, input fingerprint, deliverable bindings, artifact hashes, citations, and read-order entrypoint when available.
