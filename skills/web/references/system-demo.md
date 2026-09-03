# System Demo

Use when the audience needs to understand what a system does, how its parts cooperate, and what changes when an input or control changes.

## Required outcome

The viewer should be able to trace at least one complete input-to-output path and deliberately trigger every effect promised by the task contract.

## Model before rendering

Represent these separately:

- inputs and preconditions;
- components and ownership boundaries;
- data or control edges;
- state transitions;
- outputs and externally observable effects;
- failure or alternate path.

Prefer a staged flow for ordered execution, a dependency network for non-linear relationships, and a state machine for lifecycle behavior. Include one normal path and one meaningful alternate or failure path when supported by the evidence.

## Tensor contract layout

When the source or task defines explicit input, model, and output tensor contracts, make that contract the primary architecture layout:

```text
[Input tensors]  -->  [Model / transformation]  -->  [Output tensors]
```

- At desktop widths, keep input tensors persistently on the left, the model and ordered transformations in the middle, and output tensors persistently on the right.
- Do not replace the three regions with a stepper, carousel, tabs, or a single changing card. Those interactions may control or annotate the middle region while both boundary contracts remain visible.
- Show tensor names, shapes, availability or masking rules, and semantic roles at the boundary where they enter or leave the model.
- When a control changes a tensor, update or highlight the affected left input, the responsible middle transformation, and the resulting right output together.
- On narrow screens, stack in semantic order: input → model → output. Do not reorder for visual novelty.
- If no meaningful tensor or data contract exists, choose the topology that best explains the system instead of forcing this layout.

## Required evaluation emphasis

- architecture and relationship correctness;
- complete input-to-output trace;
- component boundaries and state transitions;
- requested controls and observable effects;
- consistency between labels, animation, and explanatory text;
- responsive and reduced-motion behavior;
- persistent left–middle–right tensor-contract layout when the task defines input, model, and output tensors.

A control that changes only color or progress without demonstrating the requested system effect does not satisfy the contract. A tensor-contract demo that hides either boundary during model exploration also fails the intended traceability requirement.
