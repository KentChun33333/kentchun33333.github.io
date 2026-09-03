# Named Web Insight Artifact

Use this mode for a source-grounded technical study delivered as standalone HTML.

## Artifact contract

- Write to the user-selected research folder with a descriptive kebab-case filename, for example `deeptutor-agent-native-learning-architecture.html`.
- Preserve the established visual language of sibling research artifacts unless redesign is requested.
- Treat the page as a technical field guide. Do not substitute a generic dashboard, landing page, or queue application for the knowledge content.
- An async case queue may be included only when the user wants an operational workflow demo. The core study must remain directly readable.

## Required information architecture

1. **Summary and thesis** — purpose, one-sentence architecture thesis, evidence basis, and boundaries.
2. **Dependency-aware workflow** — input contract → core module → output contract, followed by a staged interactive animation.
3. **Component deep dive** — switchable Algorithm and Software views.
4. **Implementation path** — exact source files, small code excerpts, runtime effect, and extension point.
5. **Principles and critique** — why it works, failure modes, use/avoid conditions, and invalidation tests.

Avoid repeating one concept across sections. Define it canonically once and cross-reference it elsewhere.

## Workflow animation formula

Adapt the staged research-demo pattern used by sibling artifacts:

- a left rail with ordered stage name, short purpose, and `ACTIVE / DONE / QUEUED` state;
- a right canvas with the current stage's input, mechanism, output, code path, and one distilled insight;
- autoplay that stops on manual control;
- Previous, Next, frame dots, progress, Replay, and a stable populated final frame;
- data-driven frames separated from rendering code;
- reduced-motion support and responsive behavior.

Borrow TER-style agent playback only when it clarifies a genuinely multi-agent or asynchronous handoff. Do not let animation replace the readable workflow.

## Algorithm components

Each algorithm card must include:

- the state or data it consumes;
- ordered steps or decision rule;
- why the mechanism exists;
- simplified pseudocode or formula;
- failure mode or boundary;
- evidence source ID or exact code path.

Whenever the distilled knowledge contains explicit Input → Model → Output tensor contracts, make the data contract the primary page-level architecture structure as well as the component deep-dive structure:

```text
[Input conditions]  -->  [Internal mechanism]  -->  [Output conditions]
```

- Keep input tensors or conditions persistently on the left, the model and its transformations in the middle, and output tensors or conditions persistently on the right at desktop widths.
- Treat this as a layout trigger, not an optional diagram style: steppers, tabs, animations, and component selectors may update the middle region but must not displace or hide either boundary contract.
- Include tensor names, shapes, masks or availability rules, and semantic roles in their corresponding left or right region when the sources define them.
- Put ordered steps, state transitions, explanatory prose, diagrams, and source-shaped code in the center mechanism region.
- Selecting an internal step must highlight its corresponding left-side input and right-side output so the causal transformation remains visible across all three regions.
- Give each collapsed card a compact preview of its initial input condition and final output condition; do not hide the contract entirely behind interaction.
- Give each interactive component three source-grounded example fixtures that cover a normal path, a meaningful alternate/control path, and a boundary or failure path. Let the learner inspect the input before revealing or checking the expected output.
- Clearly label fixture checks as teaching simulations or expected contract behavior unless the artifact actually executes the inspected implementation. Never present a static comparison as a live runtime test.
- On narrow screens, preserve semantic order as input conditions → internal mechanism → output conditions.

Do not invent quantitative metrics. Label conceptual pseudocode as conceptual; label source-shaped excerpts as simplified.

## Software components and code references

Each software card must include:

- module responsibility and ownership boundary;
- exact repository path, linked when the output location makes a relative link possible;
- public protocol, manifest, or key function;
- upstream and downstream dependencies;
- extension or replacement seam;
- a compact code excerpt when it demonstrates behavior better than prose.

Code excerpts must remain faithful to the checked-out source. Omitted lines should be obvious, and the page must not imply a conceptual snippet is runnable production code.

## Evidence and boundary labels

Use explicit labels:

- `IMPLEMENTED` — verified in code;
- `DOCUMENTED` — stated in repository documentation but not independently verified;
- `INFERENCE` — reasoned from multiple verified facts;
- `RECOMMENDATION` — transferable design advice;
- `OPEN QUESTION` — unresolved by the inspected sources.

For every major recommendation, state what implementation evidence would weaken or falsify it.

## Validation

- Parse inline JavaScript.
- Verify unique IDs and all event targets.
- Exercise autoplay, manual frame selection, replay, tabs, keyboard exits, and the stable final frame.
- Check desktop and 360px width without horizontal overflow.
- Confirm every displayed code path exists in the inspected checkout.
- Confirm the descriptive output filename and that no replacement `index.html` was introduced.
