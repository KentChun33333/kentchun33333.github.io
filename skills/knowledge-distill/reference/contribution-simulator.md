# Contribution Simulator Standard

Use this pattern in an interactive research-insight page when the study proposes or compares a framework containing at least two components, controls, mechanisms, or ablations and makes a claim about their individual or joint contribution.

The simulator lets a reader inspect a counterfactual:

> What changes when this component is enabled, removed, combined with another component, or tested under a different scenario?

It is a learning and experiment-design surface. It is not evidence by itself.

## Applicability gate

Include a simulator when all three conditions hold:

1. The artifact makes a contribution claim about a method or architecture.
2. At least two meaningful components or conditions can be varied.
3. The resulting comparison improves causal understanding beyond static prose or a small table.

Mark it `not-applicable` when the artifact is primarily a descriptive implementation trace, single-mechanism explanation, historical summary, or source review with no defensible counterfactual. Supply a concise rationale in the required metadata. Do not invent artificial toggles to satisfy the pattern.

## Minimum interaction contract

The simulator must provide:

- one baseline configuration;
- two to four meaningful component or guardrail controls;
- at least two scenario, task-type, or operating-condition choices when contribution depends on context;
- a clearly named selected condition or configuration;
- an outcome vector showing both benefit and trade-off;
- a short interpretation explaining the mechanism behind the displayed change;
- a persistent evidence-status disclosure;
- reset or baseline recovery when the state space is not immediately obvious.

Choose outcomes that match the study. Typical dimensions include task utility, decision accuracy, reliability, regression or safety risk, cost, latency, user burden, and complexity. Do not default to generic business-dashboard metrics.

## Evidence-status contract

The simulator root must carry one of these values:

| Status | Permitted use |
|---|---|
| `empirical` | Values are computed from the study's released or inspected results. Link the data or source IDs. |
| `source-reported` | Values reproduce a cited source. Identify the source and avoid implying independent verification. |
| `hypothesis` | Values or directions represent preregistered expectations to be tested. Label them as projected, not observed. |
| `conceptual` | The simulator teaches qualitative relationships. Prefer ordinal or categorical outcomes over precise numbers. |

Never blend statuses silently. If some outcomes are empirical and others projected, label them at the metric level in addition to the root status.

Do not display precise percentages for a conceptual relationship. Hypothesis-mode percentages are acceptable only when the page states that they are illustrative projections and the values are used to communicate directional expectations rather than claimed findings.

## Causal design

Each control must correspond to a real intervention described in the study. Define the baseline and the effect of each intervention before implementing the UI.

For a two-component framework, prefer a factorial surface:

| Condition | Component A | Component B |
|---|---:|---:|
| Baseline | Off | Off |
| A only | On | Off |
| B only | Off | On |
| Full method | On | On |

If the paper claims interaction or synergy, the simulator must make the joint condition inspectable. Do not implement every effect as an additive score adjustment when the underlying hypothesis is conditional or interactive.

For each scenario, define:

```text
visible context
hidden or controlled condition
baseline behavior
component-level mechanism
expected or measured outcome vector
trade-off
```

The interpretation should explain *why* a metric changes. A moving bar without a causal explanation is decoration, not knowledge distillation.

## Recommended data model

Keep state and projections separate from rendering code:

```js
const simulator = {
  evidenceStatus: "hypothesis",
  baseline: { elicitation: false, versionGate: false },
  scenarios: {
    ambiguous: {
      label: "Ambiguous true defect",
      conditions: {
        "00": { action: "revise proxy", outcomes: {/* ... */} },
        "10": { action: "clarify then revise", outcomes: {/* ... */} },
        "01": { action: "compare wrong target", outcomes: {/* ... */} },
        "11": { action: "clarify, revise, verify", outcomes: {/* ... */} }
      },
      interpretation: "Requirement recovery changes what the version gate measures."
    }
  }
};
```

Use labels and outcomes appropriate to the artifact rather than copying this example mechanically.

## Visual and accessibility requirements

- Keep controls adjacent to the outcomes they affect.
- Show the selected state in text, not color alone.
- Use native buttons, selects, and form controls where possible.
- Provide visible focus states and keyboard operation.
- Announce updated outcomes through an `aria-live` region when the change is otherwise difficult to perceive.
- Preserve control → outcome → interpretation order on narrow screens.
- Avoid motion that obscures comparison; respect `prefers-reduced-motion`.
- Ensure risk and cost use an explicit “lower is better” label when necessary.

## Validation checklist

- Metadata declares `included` or `not-applicable`.
- `included` artifacts contain exactly one primary `[data-contribution-simulator]` root.
- The root contains a valid `data-evidence-status`.
- The evidence status is visible to the reader on an element marked `data-evidence-disclosure`, not only stored as metadata.
- Every control produces a meaningful, reversible state change.
- The baseline can be recovered.
- Every displayed metric has a defined direction and provenance/status.
- Joint configurations match the stated factorial or ablation design.
- Hypothetical and conceptual values are never presented as findings.
- The simulator works at desktop and 360px width without horizontal overflow.
- The page remains understandable if JavaScript fails.

## Common failure modes

- **False precision:** invented percentages appear empirical.
- **Decorative toggles:** controls animate the page without changing a research interpretation.
- **Additive fiction:** all component effects are summed even though the claim depends on interaction.
- **Hidden baseline:** the reader cannot reconstruct what “improvement” is relative to.
- **Benefit-only display:** performance rises while cost, risk, or user burden is omitted.
- **Universalized scenario:** one request type is used to imply that a component helps every context equally.
- **Simulator replaces evidence:** an interactive projection is discussed as though the experiment has already been run.
