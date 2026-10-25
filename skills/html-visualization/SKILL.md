---
name: html-visualization
description: Build standalone interactive HTML explanations of system architecture, ordered workflows, and agent handoffs. Use for HTML visualizations, sequence diagrams with playback, and reusable visual explanation assets. Preserve supplied chart styles and distinguish explanatory simulations from live systems.
---

# HTML Visualization

Create a self-contained HTML artifact that explains the requested mechanism through readable content and purposeful interaction. Save locally unless the user requests hosting. Prefer inline CSS, JavaScript, and SVG so the artifact works from a file URL without a server or external dependencies.

## Choose the representation

Use sequence diagrams for ordered interactions, dependency networks for non-linear relationships, and state diagrams for lifecycle behavior. Preserve a supplied visual style.

The user's house sequence style uses a white 16:9 diagram, neutral participant headers, amber dashed lifelines, teal activation bars, pastel phase bands, numbered solid calls, and dashed returns. Use the [Pi swarm HTML asset](assets/pi-agent-swarm-sequence.html) for this style and read [sequence playback](references/sequence-playback.md) when adapting it.

## Model the explanation

- Separate participants, scenarios, frames, and input/mechanism/output descriptions from rendering and controls. Keep domain content out of generic rendering functions.
- Keep the full workflow readable without playback. Explain what enters each stage, what it does, and what comes out.
- Ground factual behavior in supplied code or primary sources. Label proposed workflows and illustrative behavior. Animation does not prove runtime behavior, performance, or correctness.
- Show concurrency through overlapping work and dependency changes. Separate agent contexts do not imply filesystem isolation.
- Include an alternate or failure path when it clarifies a supported distinction; do not add unrelated simulations.

## Interaction and delivery

Make controls change the explanation visibly: step navigation, clickable handoffs, replay, or scenario comparison. Playback is opt-in, stops on manual navigation and at the final frame, and respects reduced-motion preferences. Use semantic controls, keyboard-operable diagram messages, visible focus, and concise live status.

On narrow screens, provide a readable ordered trace or contract cards rather than shrinking every diagram label. Keep document width within the viewport. Printing should preserve the complete explanation.

Validate inline JavaScript, unique IDs, and resource links. Use an available browser to exercise navigation, playback interruption, final state, scenario changes, failure paths, keyboard access, desktop/narrow layouts, and reduced motion. State any unavailable verification rather than claiming it passed.

Save reusable examples in `assets/` and link them here. References should explain adaptation, not transient session results. Preserve prior examples unless replacement is requested.
