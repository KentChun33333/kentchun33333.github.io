# Prompt v8 — Agent Workforce and Progressive Result Assembly

## Objective

Create `ter-bank-multi-agent-flow-v8.html` as a standalone evolution of v7. Preserve v7 unchanged and retain the fictional Orchid Meridian Trading case, BANK styling, three-page analyst journey, seven evidence sources, recommendation/provenance placement above Refinement, micro reports, reset, print, autoplay, and compact icon-only animation navigation.

V8 must make agent work immediately understandable without filling either animation panel at frame start. The left panel is a compact workforce roster inspired by the supplied reference. The right panel progressively assembles structured results, one component at a time.

Never expose private chain-of-thought. For the active agent, show an auditable **reasoning summary** containing only its assigned task, source, action/tool, decision rationale, output, confidence or validation state, and next handoff.

## Reference-derived visual direction

Use the reference as information-architecture inspiration, not artwork to reproduce.

- Present a vertical `Agent workforce` list with small icon/initial badges, agent name, capability, and a clear active/completed/queued/idle status.
- Highlight only the active agent row with a restrained BANK-red tint and pulse.
- Expand a compact dialogue beneath the active row. Label its content `TASK`, `ACTION`, `REASONING SUMMARY`, and `OUTPUT / HANDOFF`.
- Keep completed agents compact; do not leave their working dialogue open.
- Use green status dots for completed work, red/amber for active work, and grey for queued/idle agents.
- Keep the workforce panel narrower than the main structured-results canvas.

## Animation 1 — four progressive source-processing stages

All seven sources remain represented, but related work is grouped so every presenter click advances the story.

### Frame 1 — Short-document parsing

- Activate the unified `Document Intelligence Agent`.
- Show it parsing the commercial invoice, two-page supply contract, and customs declaration as one short-document batch.
- Present OCR and VLM as tools used by this agent in the main canvas, with a lightweight direct-text/layout path for digitally legible pages.
- In the main canvas, reveal the action first, then publish the three document results one by one.
- Retain invoice value/goods/counterparty, contract terms/gap, and customs HS-code conflict.

### Frame 2 — Long-document OCR + VLM

- Keep the same unified `Document Intelligence Agent` active; do not create a separate OCR/VLM workforce agent.
- Process the 12-page KYC profile and 8-page bill of lading.
- Clearly state `Reading long documents in reconstructed page order` and `Mapping tables, stamps and cargo regions`.
- Reveal KYC and shipping results separately, including the low-confidence cargo overwrite signal.
- Make OCR + LLM reading and VLM layout reasoning the primary visual workbench in the main canvas.

### Frame 3 — Email context

- Activate `Context Agent`.
- State `Extracting customer explanation, named entities, chronology and attachment gaps from email`.
- Reveal thread reconstruction, then the unsupported-credit-note result.

### Frame 4 — Internal-data extraction

- Activate `Data Analyst / Internal Data Agent`.
- Show two distinct actions and two staged outputs:
  1. `Querying and extracting related transaction data`.
  2. `Querying customer profile and related-client profile data`.
- Treat XLSX/ledger and bank profile data as structured SQL work, not OCR/VLM work.
- End this frame with a compact orchestrator handoff stating that the seven-source case memory is ready.
- Change `External Web Agent` from queued to ready only after both SQL results are published.
- State that simulated Nature of Business and adverse-news checks are unlocked for the investigation animation.
- Do not create a separate `Evidence QA · Normalizing the complete evidence package` frame.

## Main canvas behavior

At the beginning of every frame, show only:

1. the retained-results strip from earlier frames; and
2. a concise active-work header naming the active agent and current task.

Then use short staggered animation to reveal:

1. current action/tool;
2. first structured result;
3. subsequent result(s);
4. validation status or handoff.

The reveal must stop within the current frame. Only a presenter click or autoplay timer may advance to the next frame. When the next frame opens, collapse prior processing detail into compact retained-result chips.

### Mandatory frame-to-frame continuity

- Treat every animation as a stateful sequence, not a collection of independent scenes.
- Before finalizing a frame, compare it with the frame immediately before and after it.
- Every non-terminal `OUTPUT / HANDOFF`, `NEXT DELEGATION`, owner, queued state and main-canvas handoff must name the exact agent that becomes active in the next frame and the exact task that agent performs.
- The active dialogue, workforce status, workflow/progress strip, main-canvas cards and retained-result chips must describe the same current state and next state.
- Use only the stable workforce names and abbreviations defined below. Do not reintroduce legacy or phantom roles such as `KYC Agent`, `Flow Agent`, `Transaction Agent`, `ENT Agent`, `INV Agent` or a separate OCR/VLM agent; express those activities as tasks owned by the appropriate stable agent.
- If the next frame keeps the same agent active, state the next task explicitly. If the current frame is terminal, label the output as a human-review, filing or report decision rather than implying another agent frame.
- Audit all three animations from first frame to last frame after implementation. No visible handoff may contradict the next frame’s active agent, task, status or result.

## Rich document-scanning theatre

Preserve the progressive v8 information design, but restore the most compelling v7-style document animation inside the **main canvas**.

### Short-document stage

- Begin with a compact three-file intake tray for invoice, contract and customs declaration.
- Animate the current file rising from the tray into a scanner.
- Run a visible red scan beam over the page while text and table regions become highlighted.
- Show a small live file counter such as `FILE 1 / 3` and a parser status that changes from `READING` to `KEYS FOUND`.
- Publish invoice, contract and customs result cards one at a time after the scan component appears.
- Keep the story accurate: this is direct text/layout parsing for short, digitally legible files, not the long-document OCR pipeline.

### Long-document stage

- Reuse and refine the v7 visual language: stacked pages, continuously moving OCR beam, live page/token counters, animated VLM region boxes, and file-level validation checks.
- Show OCR and VLM working side by side before results appear.
- Visually distinguish the two documents being processed: 12-page KYC profile and 8-page bill of lading.
- The VLM map should call out profile grids, table regions, stamps and the cargo-description box.
- Validation checks should animate in sequence and visibly flag the low-confidence cargo-region overwrite.
- After the theatre appears, publish KYC and shipping results separately and retain their confidence/provenance.

### Motion constraints

- Scanning motion continues while the frame is held, but it must not advance the presentation automatically.
- Keep scan effects purposeful and readable; avoid decorative particles that do not explain the work.
- Respect `prefers-reduced-motion` and keep mobile layouts usable by stacking the OCR, VLM and validation workbenches.
- Do not restore v7’s low-value `LIVE FRAME` footer sentence.

## Workforce roster

Use this stable roster across all three animations:

- `OR` — Orchestrator: plans, delegates and synthesizes.
- `DI` — Document Intelligence Agent: owns document parsing, OCR + LLM reading, VLM layout reasoning and key-value extraction.
- `CT` — Context Agent: reconstructs email context and claims.
- `DA` — Data Analyst: runs transaction/profile SQL and rankings.
- `ER` — Entity Resolver: resolves exact entities, jurisdictions and directors.
- `EW` — External Web Agent: runs simulated NOB and adverse-news searches.
- `QA` — Evidence QA: validates citations, confidence and source convergence.
- `RN` — Risk + Narrative: converts validated findings into report language.

For collaborating stages, highlight the lead agent and show collaborators in the active dialogue or as a small status annotation. Never expand more than one reasoning dialogue at a time.

### Talking-dialogue behavior

- Style the expanded active-agent dialogue as a familiar speech bubble attached to the agent icon.
- Reveal its message naturally, word by word, as if the agent is talking.
- Show a small animated typing indicator before the first words appear.
- Reveal `TASK`, `ACTION`, `REASONING SUMMARY`, and `OUTPUT / HANDOFF` in sequence rather than displaying the full bubble immediately.
- Keep the final message visible after typing completes.
- Restart the word-by-word animation whenever the presenter enters a new frame.
- For reduced-motion users, show the complete dialogue immediately.

## Animation 2 — six-frame investigation

Keep the existing six-stage story: orchestrator scope, customer/profile baseline, transaction extraction and counterparty ranking, Aster Peak entity/Web resolution with NOB loop-back, source convergence/QA, and validated STR finding formation.

Render every stage through the same workforce roster. The main canvas must still reveal its components progressively and retain previous results as chips.

## Animation 3 — five-frame refinement

Keep the existing five-stage story: analyst scope, counterparty #2 isolation, director and simulated adverse-news resolution, relationship/validation review, and final report update.

Render every stage through the same workforce roster. Preserve the distinction between bank facts, registry facts and an unverified simulated news lead.

## Content and footer requirements

- Remove all low-value small footer prose and animation legends.
- Keep only frame count, progress bar, progress dots, Exit, Previous, Replay and compact icon-only Next/Finish.
- Recommendation and provenance must appear once above Refinement; remove any duplicate placement.
- Recommendation copy remains `FILE STR · HIGH` with the established escalation wording.

## Visual, accessibility and technical requirements

- Light panels, white agent rows, subtle dotted texture, restrained BANK red, green completion and grey queue states.
- No dark-grey progressive-routing block.
- No page-level horizontal overflow.
- Stack panels on mobile; keep agent status, active dialogue and controls readable.
- Native buttons, visible focus styling, dynamic Next/Finish `aria-label` and tooltip, and reduced-motion support.
- Clearly label all simulated registry/news content and fictional data.
- Keep all CSS, JavaScript and case data in one HTML file with no backend dependency.

## Acceptance criteria

1. Prompt v8 and HTML v8 exist; v7 is unchanged.
2. Animation 1 has four grouped stages while visibly accounting for all seven sources.
3. The left panel is a compact icon-based workforce list, not a node-routing diagram.
4. Only the active agent expands a structured reasoning dialogue; hidden chain-of-thought is never shown.
5. Frame 1 begins sparse and publishes invoice, contract and customs results one by one.
6. Long-document work is a separate OCR+VLM stage for KYC and bill of lading.
7. Email context and internal-data SQL are separate, explicit stages.
8. Transaction SQL and profile/related-client SQL are distinct actions and outputs.
9. External Web Agent remains queued until the two Internal Data SQL results are published.
10. Completed processing collapses into retained-result chips on later frames.
11. Investigation remains six frames; refinement remains five frames.
12. Recommendation/provenance appears once above Refinement.
13. Low-value animation footer prose is absent.
14. All controls, refinement, recommendation update, micro reports, reset and printing continue to work.
15. The short-document stage visibly scans a three-file tray before publishing three results.
16. The long-document stage includes animated stacked pages, OCR beam, live page/token counters, VLM region mapping and sequential validation checks.
17. No standalone Evidence QA normalization frame exists in Animation 1.
18. The active-agent speech bubble reveals its structured summary word by word and remains readable after completion.
19. Document Intelligence Agent is the only document-processing workforce role; OCR and VLM appear as its tools in the main canvas.
20. No workforce role or visible status is labelled `External Intelligence`; the role is consistently `External Web Agent`.
21. Every non-terminal handoff, next-delegation label, owner and queued state matches the exact active agent and task in the following frame across all three animations; terminal frames point to a human/report decision.
22. No legacy or phantom agent labels appear in the animation story when a stable workforce role owns that work.
23. JavaScript parsing, complete click-through, desktop/mobile rendering, horizontal overflow and browser console output are verified before delivery.
