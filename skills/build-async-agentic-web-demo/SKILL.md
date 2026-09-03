---
name: build-async-agentic-web-demo
description: Build or refactor polished, standalone agentic web application demos with asynchronous queue-driven workflows, staged multi-agent playback, human review gates, evidence provenance, progressive case states, and refinement loops. Use when creating HTML/CSS/JavaScript prototypes, executive demos, case-management simulations, agent-work animations, document-intelligence experiences, or human-in-the-loop AI product concepts inspired by TER v15 and Wealth Data Intelligence v2.
---

# Build Async Agentic Web Demo

Create a believable product demo in which agent work happens asynchronously and users remain in control. Treat the queue as the source of truth and agent animation as an optional explanation layer.

When invoked from a Knowledge Distill task contract, require deliverable type `agentic-demo`, consume its objective, audience, functions, and observable effects, and evaluate the result with the assigned `agentic-demo-v1` profile. The sibling `web` skill owns category selection; this skill owns agentic-demo implementation.

## Start from the demo contract

Before coding, define:

- User role, decision, and business outcome.
- One representative case with enough evidence to tell a complete story.
- Three to five case states and the human action that advances each state.
- Agent roster, source systems, outputs, and handoffs.
- Which claims are simulated and how the UI labels them.

Read [references/architecture.md](references/architecture.md) before designing the workflow. Read [references/pattern-catalog.md](references/pattern-catalog.md) when selecting UI and animation patterns.

## Build in this order

1. Model the case state machine as data. Keep domain facts outside rendering functions.
2. Build the case queue first. Give every active row distinct status, recommendation, agent-work, and action controls.
3. Build human review surfaces. Use foldable evidence sections, visible provenance, confidence labels, and explicit approval controls.
4. Build the outcome surface. Separate agent recommendation from the human decision and allow a refinement instruction plus optional files.
5. Add agent playback last. Make it replayable and deterministic; never force it into the normal workflow.
6. Add responsive behavior, reduced-motion support, keyboard exits, empty states, and simulated-data notices.

## Choose an example

- Start new domains from `assets/standalone-demo/index.html`. It is the compact, generic implementation of the core state machine.
- Study `assets/ter-v15-full-demo/index.html` for an advanced, production-shaped example with dense evidence review, queue progression, historical reports, exports, modals, agent-network playback, and refinement. Treat its banking brand, scenario, risk logic, and fictional facts as reference content only.

Replace scenario data and copy before changing mechanics. Do not carry financial-crime claims, customer details, or regulated decisions into unrelated domains.

## Preserve the async invariant

When a user submits work:

- Persist or update one case record; do not add duplicates for each stage.
- Return to the queue immediately.
- Show the next status and required human action.
- Attach the latest completed agent stage to `Agent work` for on-demand playback.
- Route `Detail` from case state, not from a hard-coded page sequence.

Keep timers and animation state separate from business state. Cancel outstanding timers when replaying, navigating, or closing playback.

## Make agent work explainable

Represent each frame as data with:

- Active agent and completed/queued agents.
- Task, action, bounded reasoning summary, output, and next handoff.
- Sources consulted and artifacts produced.
- A stable final frame with the complete outcome visible.

Show concise reasoning summaries, not hidden chain-of-thought. Do not imply real API calls, live research, or completed transactions when using fixtures.

## Keep human authority explicit

- Require review before consequential status changes.
- Distinguish `recommendation`, `decision`, and `approvedBy` in state.
- Let users correct evidence without overwriting original values or provenance.
- Treat refinement as a new scoped run with its own files and audit event.
- Disable conflicting actions while an operation is in flight.

## Verify before delivery

Run:

```bash
python scripts/validate_demo.py path/to/demo.html
```

Then follow [references/quality-gates.md](references/quality-gates.md). Test the full happy path, replay every agent stage, use Back/Escape at every layer, resize to mobile width, and confirm the final frame remains populated.

## Source lineage

This skill distills reusable patterns from:

- TER multi-agent flow v15 at commit `666c63a`.
- Wealth Data Intelligence v2 at commit `1bcfb09`.

Use the patterns, not the domain claims or branding. Preserve previous demo versions when evolving an existing numbered prototype.
