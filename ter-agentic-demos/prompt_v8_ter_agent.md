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

## Animation 1 — five progressive source-processing stages

All seven sources remain represented, but related work is grouped so every presenter click advances the story.

### Frame 1 — Short-document parsing

- Activate `Document Intelligence`.
- Show it parsing the commercial invoice, two-page supply contract, and customs declaration as one short-document batch.
- Use direct text/layout parsing; do not overstate OCR/VLM work.
- In the main canvas, reveal the action first, then publish the three document results one by one.
- Retain invoice value/goods/counterparty, contract terms/gap, and customs HS-code conflict.

### Frame 2 — Long-document OCR + VLM

- Activate `OCR + VLM`.
- Process the 12-page KYC profile and 8-page bill of lading.
- Clearly state `Reading long documents in reconstructed page order` and `Mapping tables, stamps and cargo regions`.
- Reveal KYC and shipping results separately, including the low-confidence cargo overwrite signal.

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

### Frame 5 — Evidence normalization and Web handoff

- Activate `Evidence QA` with the Orchestrator coordinating.
- Normalize keys, replay material citations, preserve low-confidence fields, and publish the complete case-memory package.
- Only now change `External Intelligence / Web Agent` from queued to ready.
- State that simulated Nature of Business and adverse-news checks are unlocked for the investigation animation.

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

## Workforce roster

Use this stable roster across all three animations:

- `OR` — Orchestrator: plans, delegates and synthesizes.
- `DI` — Document Intelligence: parses short documents and key values.
- `OV` — OCR + VLM: reads long documents and reasons over layout.
- `CT` — Context Agent: reconstructs email context and claims.
- `DA` — Data Analyst: runs transaction/profile SQL and rankings.
- `ER` — Entity Resolver: resolves exact entities, jurisdictions and directors.
- `XI` — External Intelligence: runs simulated NOB/adverse-news searches.
- `QA` — Evidence QA: validates citations, confidence and source convergence.
- `RN` — Risk + Narrative: converts validated findings into report language.

For collaborating stages, highlight the lead agent and show collaborators in the active dialogue or as a small status annotation. Never expand more than one reasoning dialogue at a time.

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
2. Animation 1 has five grouped stages while visibly accounting for all seven sources.
3. The left panel is a compact icon-based workforce list, not a node-routing diagram.
4. Only the active agent expands a structured reasoning dialogue; hidden chain-of-thought is never shown.
5. Frame 1 begins sparse and publishes invoice, contract and customs results one by one.
6. Long-document work is a separate OCR+VLM stage for KYC and bill of lading.
7. Email context and internal-data SQL are separate, explicit stages.
8. Transaction SQL and profile/related-client SQL are distinct actions and outputs.
9. Web/External Intelligence remains queued until evidence normalization completes.
10. Completed processing collapses into retained-result chips on later frames.
11. Investigation remains six frames; refinement remains five frames.
12. Recommendation/provenance appears once above Refinement.
13. Low-value animation footer prose is absent.
14. All controls, refinement, recommendation update, micro reports, reset and printing continue to work.
15. JavaScript parsing, complete click-through, desktop/mobile rendering, horizontal overflow and browser console output are verified before delivery.
