---
name: web
description: Build source-grounded interactive HTML deliverables selected by a task contract, specifically research sites, system explainers, and agentic workflow demos. Use when distilled knowledge must become a purpose-built web artifact rather than a generic website.
---

# Web Deliverables

Turn a supplied knowledge package and task contract into an offline-capable web artifact. Preserve evidence, optimize the presentation for the stated audience and objective, and implement only interactions that clarify the content or demonstrate a requested effect.

## Select one web category per deliverable

- `research-site`: explain a thesis, evidence, mechanisms, limitations, and implications. Read [references/research-site.md](references/research-site.md).
- `system-demo`: expose architecture, data/control flow, components, state changes, and observable effects. Read [references/system-demo.md](references/system-demo.md).
- `agentic-demo`: demonstrate agents, queues, handoffs, tool evidence, human review, and asynchronous state. Use the sibling `build-async-agentic-web-demo` skill and read [references/agentic-demo.md](references/agentic-demo.md).

Do not blend categories merely to add visual variety. If the task requests multiple categories, create multiple deliverables with separate output paths and evaluation rules.

## Consume the contract

Require these resolved fields before building:

- input knowledge-package path;
- objective and audience;
- selected web category and output path;
- required claims, evidence links, functions, and observable effects;
- category-specific evaluation profile.

Ask only for fields that cannot be inferred safely. Do not ask the user to restate information already present in the sources or conversation.

## Shared implementation rules

1. Model content and demonstrations as data before rendering them.
2. Keep source claims, inferred explanations, and simulated behavior visibly distinct.
3. Make every requested function produce a user-observable state change; decorative controls do not count.
4. Provide readable content without requiring animation. Interaction may reveal, compare, trace, filter, or replay it.
5. Use a stable final state, deterministic fixtures, keyboard access, reduced-motion support, and a responsive narrow-screen layout.
6. Keep domain facts out of generic rendering functions so the example can be adapted without carrying stale claims.
7. Validate against the exact evaluation profile assigned to this deliverable. Do not substitute generic website quality criteria.

## Examples

Inspect only the selected category example:

- [examples/research-site.html](examples/research-site.html) — evidence-led technical study.
- [examples/system-demo.html](examples/system-demo.html) — controllable system-flow explanation.
- [examples/agentic-demo.html](examples/agentic-demo.html) — compact queue and human-review demonstration.

Examples demonstrate structure and interaction contracts, not reusable facts or branding. Replace their content completely.

## Verify

Run:

```bash
python3 skills/web/scripts/validate_examples.py <output.html> --category <category>
```

Then apply the evaluator skill named in the task contract. Deterministic validation is a precondition, not the complete quality judgment.
