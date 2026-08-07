/Users/kentchiu/.zshenv:.:1: no such file or directory: /Users/kentchiu/.cargo/env
# Prompt v8 — Progressive Agent Workflow and Staged Result Reveal

## Objective

Create `ter-bank-multi-agent-flow-v8.html` as a new standalone evolution of v7. Preserve v7 unchanged and retain the fictional Orchid Meridian Trading case, BANK styling, three-page analyst journey, seven-source evidence review, six-frame investigation, five-frame refinement, recommendation/provenance placement, micro reports, reset, print, autoplay, and compact icon-only animation navigation.

V8 must reduce the amount of information visible when an animation frame begins. Each frame should first communicate which source and agent are active, then reveal the agent action, then reveal the structured result. Completed processing detail should collapse into compact retained-result indicators when the next frame begins.

Do not expose private chain-of-thought. Show concise operational reasoning summaries only: assigned task, tool/action, source, result, confidence, validation status, and next handoff.

## Reference-derived visual direction

Use the supplied workflow references as inspiration for information architecture, not as artwork to reproduce.

- Prefer a light workflow canvas with subtle dots, simple connected nodes, directional arrows, and clear active/completed states.
- Construct only the current path plus essential completed context. Do not render every possible source and specialist at the beginning.
- Attach small contextual action callouts to the active node, similar to a workflow-builder annotation.
- Keep connectors meaningful: source → active agent → tool/action → normalized result/shared memory → next agent.
- Use restrained colour blocks for source, agent, tool, memory, and result roles.
- Avoid the dark-grey command banner used by v7.

## Required v8 changes

### 1. Staged reveal in Structured Actions and Results

The main animation canvas must no longer appear fully populated at frame start.

For every frame, reveal content in this order:

1. **Active work header** — name the active agent or collaborating group and state its current task in plain language.
2. **Action/tool summary** — show the simplified operation, such as `Extracting KYC document`, `Mapping tables with VLM`, `Reading long contract with OCR + LLM`, `Extracting email context`, `Querying related transaction data`, or `Querying customer and related-client profiles`.
3. **Structured processing component** — reveal the relevant document, email, SQL, entity, Web, validation, or relationship component.
4. **Result** — reveal extracted values, ranked rows, resolved entity, mismatch, validation result, or report update.
5. **Retained result** — when advancing to the next frame, replace the completed processing detail with a compact result chip in the retained-results strip.

Use short staggered reveal animation. The frame still remains under presenter control; the within-frame reveal must not automatically advance to another frame.

### 2. Explicit agent activity labels

Make the current work unmistakable.

- Document Agent: `Extracting [document name]`.
- VLM: `Mapping layout, tables, stamps and signatures`.
- OCR + LLM: `Reading a long document in reconstructed page order`.
- Context Agent: `Extracting customer explanation, entities and chronology from email`.
- Internal Data Agent transaction task: `Querying and extracting related transaction data`.
- Internal Data Agent profile task: `Querying customer profile and related-client profile data`.
- Entity Agent: `Resolving exact entity identity and jurisdiction`.
- Web Agent: `Checking simulated Nature of Business and adverse-news sources`.
- Evidence QA: `Replaying citations and validating material claims`.
- Risk/Narrative group: `Converting validated findings into STR language`.

When an agent completes, change the activity from a live verb to a compact completed result.

### 3. Simplify Progressive Agent Workflow

Remove the dark `PROGRESSIVE EVIDENCE ROUTING / ROUTE … SOURCE` banner.

Replace the left panel with a light workflow-builder-style canvas:

- subtle dotted background;
- one current source node;
- one active agent node or compact active collaboration group;
- an optional tool/action node such as VLM, OCR + LLM, SQL, registry or Web search;
- a normalized-result/shared-memory node;
- directional connectors between visible nodes;
- a small action callout attached to the active agent explaining what it is doing;
- newly added nodes animate into place;
- the active path pulses or highlights;
- completed nodes remain compact and future nodes do not appear until required.

At the first extraction frame, show only:

- the current KYC source;
- Document Agent;
- VLM/OCR + LLM action;
- an empty or starting result-memory node.

Do not show Email, Database, Context Agent, Internal Data Agent or Web Agent before their workflow step is reached.

### 4. Source-specific progressive paths

#### Document frames

`Document source → Document Agent → VLM`.

For long documents, extend the current path with `OCR + LLM`. Show a callout such as `Extracting key values from 12 pages` and update the result memory when complete.

#### Email frame

`Email source → Context Agent → Context extraction → Result memory`.

Show customer explanation, named entities, chronology and evidence gaps progressively.

#### Internal-data frame

`Internal database → Internal Data Agent → SQL transaction query → SQL profile query → Result memory`.

Clearly show both operations:

- extracting related transaction data;
- extracting customer and related-client profile data.

Do not label the account statement as OCR/VLM work in the main canvas when the intended story is structured internal-data extraction.

#### Web activation

Only add Web Agent after normalized customer, document, email and internal-data keys are ready. Its visible actions are simulated NOB verification and adverse-news search.

### 5. Remove low-value footer text

Remove all small explanatory footer sentences inside animation pages, including:

- `LIVE FRAME · OCR continues paging, VLM regions keep reasoning and the investigation agent keeps challenging until the presenter advances.`
- autoplay/pause explanatory sentences in the animation footer;
- `QUEUED → ACTIVE → COMPLETE · RESULTS RETAINED` and similar tiny legend text.

Keep only controls, the progress bar, progress dots, frame count, and meaningful workflow/status content.

## Animation behavior

### Animation 1 — Seven-source processing

- Keep exactly seven frames.
- Frames 1–5 progressively process document evidence.
- Frame 6 progressively processes email through Context Agent.
- Frame 7 uses Internal Data Agent and separate transaction/profile SQL actions.
- Web becomes available only after the final normalized key-value set is ready.

### Animation 2 — Six-frame investigation

- Keep exactly six frames.
- Progressively reveal ORCH scope, profile SQL, transaction SQL/ranking, entity/Web resolution, source convergence/QA, and STR finding formation.
- Construct only the nodes required in the current frame.
- Preserve the Aster Peak discovery and NOB loop-back story.

### Animation 3 — Five-frame refinement

- Keep exactly five frames.
- Progressively reveal counterparty #2 isolation, entity/director resolution, simulated Web search, relationship reconstruction, validation gap, and report update.

## Visual and accessibility requirements

- Keep the left workflow panel smaller than the main result canvas.
- Avoid page-level horizontal overflow.
- On mobile, stack the workflow and result panels and keep current action, controls, and active node visible.
- Retain the compact icon-only Next/Finish control with dynamic `aria-label` and tooltip.
- Use native buttons, visible focus styling and reduced-motion support.
- Clearly label simulated registry/news data and fictional content.
- Keep all CSS, JavaScript and case data in one HTML file with no backend dependency.

## Acceptance criteria

1. A new v8 prompt and v8 HTML exist; v7 remains unchanged.
2. The dark progressive-routing banner is removed.
3. Frame 1 starts with only the current source, active document agent/tool path and starting result memory.
4. Main-canvas content reveals sequentially rather than appearing fully populated immediately.
5. Document, VLM, OCR+LLM, Context, Internal Data, Entity, Web, QA and Risk/Narrative work use explicit activity labels.
6. The Internal Data frame visibly performs distinct transaction and customer/related-client profile queries.
7. Email and database agents do not appear before their frames.
8. Web Agent does not appear before normalized identifiers and context are ready.
9. Completed processing collapses into retained-result chips on subsequent frames.
10. All low-value animation footer/legend sentences are removed.
11. Animation counts remain seven, six and five.
12. Previous, Replay, Exit, autoplay, Next/Finish, refinement, recommendation update, micro reports, reset and printing continue to work.
13. JavaScript parsing, complete click-through, desktop rendering, mobile rendering, horizontal overflow and browser console output are verified before delivery.
