# IQ-Style Review — Component Data Contracts

## Working-memory scratchpad

- Objective: make every component legible as a causal transformation.
- Fixed structure: input conditions on the left, internal mechanism in the center, output conditions on the right.
- Evidence: the skill already required this topology for system workflows; component interaction failed to preserve it.
- Hypothesis: persistent synchronized contracts reduce the effort needed to understand preconditions, state transitions, and downstream guarantees.
- Confidence: high for structural clarity; user testing is still the final judge of explanatory quality.

## Independent assessment

| Dimension | Before | Revised |
|---|---:|---:|
| Structure reasoning | 2/5 | 5/5 |
| Output duplication | 4/5 | 4/5 |
| Reasoning depth | 4/5 | 5/5 |
| Evidence boundaries | 5/5 | 5/5 |
| Practical transfer | 3/5 | 5/5 |

## Red-team critique

- A horizontal three-box strip technically contained input and output, but users had to reparse it on every step and could not see the full component contract.
- Step navigation competed with the mechanism explanation for visual priority.
- Collapsed cards did not expose their contract, so comparison required opening each card.

## Revised assessment and error journal

The revised layout keeps the full contract visible, synchronizes selected inputs and outputs with the center transformation, and previews the first input/final output on every card. The corrective rule is: interaction may reveal detail, but it must not conceal the component's causal boundary.

## Extracted principle

For technical component explanations, use interaction to animate the transformation inside a stable data contract—not to replace the contract.

## Scenario-fixture extension

The contract is now tested pedagogically with three cases per component: normal behavior, a meaningful alternate/control branch, and a boundary or failure case. Inputs remain visible before the learner reveals expected outputs. Because the page does not invoke a live DeepTutor process, every result is labeled as expected contract behavior rather than runtime execution. This raises practical transfer while preserving the evidence boundary.
