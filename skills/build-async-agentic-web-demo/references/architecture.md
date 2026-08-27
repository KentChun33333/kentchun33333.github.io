# Architecture

## Contents

1. Product surfaces
2. State model
3. Transition contract
4. Data and rendering boundaries
5. Simulation boundaries

## Product surfaces

Build three human surfaces and one optional system surface:

1. **Queue and intake** — create work, search cases, see statuses, and resume the required action.
2. **Evidence review** — inspect extraction or research with confidence, provenance, and corrections.
3. **Outcome and refinement** — review the recommendation, inspect supporting analysis, approve or request another run.
4. **Agent work** — replay how the latest stage was produced. This surface explains work; it does not gate navigation.

The queue is the application home and system of record. Every submission returns there.

## State model

Use one serializable application state and one case record per case.

```js
const app = {
  page: "queue",
  selectedCaseId: null,
  playback: { open: false, stage: null, frame: 0, timer: null },
  cases: []
};

const caseRecord = {
  id: "CASE-1042",
  status: "evidence-review",
  statusLabel: "Evidence ready · review required",
  recommendation: "Pending",
  latestAgentStage: "extraction",
  evidence: [],
  corrections: [],
  refinementFiles: [],
  audit: []
};
```

Keep canonical status codes stable and generate display labels separately. Store originals and corrections rather than mutating source evidence.

## Transition contract

| Current state | Human action | Async stage | Next state | Detail route |
|---|---|---|---|---|
| Draft | Submit case | Intake/extraction | Evidence review | Evidence |
| Evidence review | Approve evidence | Investigation | Outcome review | Outcome |
| Outcome review | Request refinement | Refinement | Outcome review | Outcome |
| Outcome review | Approve | None | Approved | Read-only outcome |

Every transition must:

1. Validate the user input.
2. Update the existing case atomically.
3. Append an audit event.
4. Set `latestAgentStage` only when the stage is complete.
5. Return to the queue without opening playback.
6. Render from the updated state.

For a real backend, replace simulated timers with job submission plus polling, Server-Sent Events, or WebSocket updates. Preserve the same state contract so the prototype can graduate without redesigning the UI.

## Data and rendering boundaries

Use data-driven arrays for cases, sources, evidence, agents, frames, charts, and recommendations. Keep these layers separate:

- `scenario`: fixture facts and labels.
- `state`: mutable user/session state.
- `transitions`: validation and case updates.
- `render*`: pure or nearly pure DOM rendering.
- `bindings`: event listeners.
- `playback`: timer lifecycle and frame selection.

Do not bury business decisions in click handlers or infer state from button text.

## Simulation boundaries

Label fixtures and mocked sources. A good notice says what is simulated and what a production integration would do. Avoid fake real-world URLs that could be mistaken for citations; use reserved domains such as `example.com`.

Animations should show observable workflow facts: task, source, action, output, handoff, and status. Never present private chain-of-thought. Use “reasoning summary” for concise, user-facing rationale.
