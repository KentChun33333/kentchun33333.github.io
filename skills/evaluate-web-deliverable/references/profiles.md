# Evaluation Profiles

## `research-site-v1`

Prioritize fidelity and argument quality. Verify that the thesis serves the named audience, major claims have inspectable evidence, mechanisms are explained rather than asserted, uncertainty remains visible, and interactions improve comparison or traceability.

Hard failures include an unsupported major claim, hidden or fabricated provenance, or a requested evidence interaction that produces no observable effect.

## `system-demo-v1`

Prioritize system correctness and demonstrability. Verify component responsibilities and relationships, one complete input-to-output path, meaningful alternate behavior, and alignment between the explanation, animation, and resulting state.

Hard failures include a materially incorrect architecture path or a requested control that changes decoration without demonstrating the promised system effect. When explicit input, model, and output tensor contracts are part of the task, also verify that the desktop architecture keeps them visible as left → middle → right and that narrow layouts preserve input → model → output order; hiding a boundary behind model-step interaction is a traceability failure.

## `agentic-demo-v1`

Prioritize workflow integrity and human authority. Verify persistent case identity, valid state transitions, bounded agent responsibilities, visible receipts/provenance, explicit simulated-data labeling, replay stability, and a real human decision gate.

Hard failures include presenting a recommendation as a human decision, implying fixture activity is live, or allowing a consequential transition before its required review.

## Scoring behavior

All rubric dimensions use a 0–5 scale:

- `0`: absent or contradicts the contract;
- `1`: materially deficient;
- `2`: partial with major gaps;
- `3`: adequate and demonstrable;
- `4`: strong with minor gaps;
- `5`: complete, clear, and evidence-backed.

Weights differ by profile. A higher score is meaningful only under the same profile and contract fingerprint.
