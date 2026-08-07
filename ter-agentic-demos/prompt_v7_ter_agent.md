/Users/kentchiu/.zshenv:.:1: no such file or directory: /Users/kentchiu/.cargo/env
# Prompt v7 — Progressive Evidence-to-STR Agent Workflow

## Objective

Create `ter-bank-multi-agent-flow-v7.html` as a new standalone evolution of v6. Preserve v6 unchanged and retain the fictional Orchid Meridian Trading TER / STR scenario, neutral BANK branding, three-page analyst journey, seven prepared evidence sources, editable evidence review, investigation refinement, printing, replay, reset, and single-file HTML architecture.

The v7 experience must make the investigation story easier to present. It should show how different source types activate the correct specialist agent, how normalized key values accumulate in shared case memory, and how the Web agent becomes available only after sufficient customer, transaction, document, and email context exists.

Never expose private or unrestricted model chain-of-thought. The main canvas may show concise, evidence-grounded reasoning summaries: task, query/action, source used, result, confidence, validation status, and next workflow decision.

## Required v7 changes

### 1. Compact animation navigation

Across every animation mode:

- Replace the large text-based **Next frame →** control with a compact icon-only button.
- Use a clear right-arrow icon while another frame is available and a clear completion icon on the final frame.
- Keep an accessible `aria-label` and tooltip that dynamically change between “Next frame” and “Finish animation”.
- Preserve Previous, Replay, Exit, progress dots, click-controlled advancement, autoplay, keyboard accessibility, and the behavior where the final frame remains available for review.

### 2. Recommendation and provenance beside analyst refinement

On Page 3, expand the existing one-line recommendation status into a complete decision-summary component placed immediately above **Refinement** in the right-hand panel. It must contain:

- label: `RECOMMENDATION`;
- decision: `FILE STR · HIGH`;
- explanation: `The cross-source goods, business-profile, counterparty and flow indicators support escalation for STR filing consideration.`;
- label: `PROVENANCE STATEMENT`;
- statement: `Seven uploaded sources, bank-held profile data, transaction records and simulated open-web results were reconciled. Human corrections, instructions and evidence gaps are retained in the decision trace.`

When targeted refinement completes, update the recommendation explanation to acknowledge the newly supported counterparty #2 exposure while preserving the open-source validation caveat.

Remove the original Recommendation and Provenance sections from the report body so the content appears only once in the interactive Page 3 layout.

### 3. Progressive source-to-agent storyline

Redesign the animation’s left panel as a dynamically constructed evidence workflow rather than a static network. The story must be understandable without reading the main canvas.

#### Source routing

- **Email → Context Agent**
  - reconstruct message threads and chronology;
  - extract customer explanations, named entities, stated purpose, and unsupported claims.
- **Document → Document Agent**
  - use VLM for layout, tables, stamps, signatures, and spatial relationships;
  - when a contract or document is long, add OCR + LLM long-document reading;
  - normalize extracted key values with source references and confidence.
- **Database → Internal Data Agent**
  - show SQL query actions for related transactions;
  - show a separate SQL query for customer profile and related-client profile data;
  - return structured transaction, customer, and relationship facts.
- **Shared key-value memory → Web Agent**
  - keep the Web agent visibly locked or queued until the required normalized key values are ready;
  - then activate Nature of Business verification and adverse-news search using resolved entity names and context;
  - clearly label all registry and news results as simulated fictional data.

#### Dynamic behavior

- Begin with the orchestrator and available source lanes, not every specialist at once.
- Add agent nodes only when their input is ready and their task is delegated.
- Animate newly constructed nodes and connections.
- Highlight one active agent or the active collaborating group; show completed agents in a stable completed state and future agents as queued or locked.
- Display each active agent’s simplified action, such as `read email context`, `VLM layout map`, `OCR + LLM long read`, `SQL: related transactions`, `SQL: customer profile`, `normalize key values`, `NOB verification`, or `adverse-news search`.
- Make the workflow visibly more complete as frames advance. Completed nodes and outputs remain visible so the audience can understand accumulated evidence.
- Preserve meaningful loop-back behavior when newly resolved facts reopen an earlier mismatch test.

### 4. Progressive main work-product canvas

The right canvas remains dominant and must update component by component as agents work:

1. show the current structured task and source action;
2. show a concise reasoning/action summary, never private chain-of-thought;
3. reveal the extracted or queried result;
4. retain completed results as compact evidence-memory chips or result cards;
5. remove or collapse temporary processing details once an agent finishes;
6. show the next decision, validation, or agent handoff.

The retained result trail should progress through examples such as:

- customer profile established;
- email explanation captured;
- document key values normalized;
- related transactions ranked;
- counterparty discovered and resolved;
- Web checks enabled;
- NOB contradiction supported;
- citations validated;
- STR finding formed.

## Animation-specific expectations

### Animation 1 — Seven-source processing

- Keep exactly seven source frames.
- Route each file through the correct source lane and specialist workflow.
- The email frame must visibly use the Context Agent.
- Document frames must visibly use Document Agent + VLM, adding OCR + LLM where long-page handling applies.
- The account-statement/database frame must visibly show Internal Data Agent SQL queries for transactions and profile context.
- Show normalized key-value memory filling across the seven frames.
- Do not activate Web research before required identifiers and profile/transaction/document key values are ready.

### Animation 2 — Six-frame investigation

- Keep exactly six frames and the v6 evidence narrative.
- Begin with ORCH only, then progressively construct Internal Data, Document/VLM, Context, Entity, Web, QA, Risk, and Narrative nodes as required.
- Make Web activation an explicit consequence of normalized key values becoming ready.
- Retain the Aster Peak discovery, entity resolution, NOB loop-back, source convergence, validation, and finding formation.
- Keep counterparty #2 queued for human-directed follow-up.

### Animation 3 — Human-directed refinement

- Preserve the counterparty #2 investigation and its five frames.
- Highlight the active collaborating group as transaction isolation, director resolution, Web research, relationship reconstruction, and report update proceed.
- Retain the distinction between bank facts, registry facts, and an unverified simulated adverse-news allegation.

## Visual and interaction principles

- Keep the left workflow smaller than the right work-product canvas.
- Use restrained movement to communicate assignment, node construction, active work, completion, shared-memory updates, and handoffs.
- Avoid decorative agent motion without a workflow meaning.
- Use stable visual states for `queued`, `active`, `challenge`, `complete`, and `locked`.
- Keep text concise enough for a live presentation.
- Maintain responsive behavior; on narrow screens the workflow and canvas may stack, but controls and active content must remain visible without page-level horizontal overflow.
- Maintain semantic native controls, visible focus states, ARIA labels for icon-only controls, and reduced-motion compatibility.

## Acceptance criteria

1. A new v7 prompt and v7 HTML exist; v6 remains unchanged.
2. Every animation uses a compact icon-only Next/Finish control with a correct dynamic accessible label.
3. The complete Recommendation and Provenance component appears above Refinement on Page 3.
4. Recommendation and Provenance no longer appear in their previous report-body location.
5. Email visibly routes to Context Agent.
6. Documents visibly route to Document Agent + VLM, with OCR + LLM for long documents.
7. Database/internal data visibly runs separate SQL actions for transactions and customer/related-client profiles.
8. Web/NOB/adverse-news work remains locked until normalized key values are ready.
9. Left-panel nodes build progressively, retain completed states, and highlight active collaborators.
10. The main canvas retains compact completed results while temporary action detail is removed or simplified.
11. Animation 1 has seven frames, Animation 2 has six frames, and Animation 3 has five frames.
12. Previous, Replay, Exit, autoplay, refinement, micro reports, reset, print, and final-report rendering continue to work.
13. JavaScript syntax, desktop rendering, mobile rendering, console output, and complete click-through behavior are verified before delivery.
