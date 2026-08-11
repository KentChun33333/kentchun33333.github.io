# Prompt v12 — Explainable Partial-to-Full Exit Escalation

## Objective

Create `ter-bank-multi-agent-flow-v12.html` as a standalone evolution of v11. Preserve v11 unchanged and retain the current visual UI, fictional Orchid Meridian Trading case, BANK styling, three-page analyst journey, seven evidence sources, recommendation placement above Refinement, appendix reports, reset, export, autoplay, and compact icon-only animation navigation.

V12 must make both the evidence story and the change in exit decision immediately understandable. The left panel remains a compact workforce roster. The right panel progressively assembles structured results, while Page 3 clearly explains why the initial outcome is Partial Exit and what new evidence changes it to Full Exit.

Remove the `CONCEPT DEMO · FICTIONAL DATA` label from the global header. Reuse that top-right space for short, page-aware controls: Page 1 has no controls, Page 2 shows `← Back`, and Page 3 shows `New`, `← Back`, and `Export`. Put an animation-level `← Back` control in the animation header at upper right, and remove the `AUTO-PLAY · MANUAL CONTROL AVAILABLE` caption. Backward navigation must mirror the forward journey by sector: `Page 1 → Animation 1 → Page 2 → Animation 2 → Page 3 → Animation 3 → updated Page 3`. Therefore Page 2 Back opens the final frame of Animation 1, initial Page 3 Back opens the final frame of Animation 2, updated Page 3 Back opens the final frame of Animation 3, and each animation-header Back returns to the page immediately before that animation. Keep frame-level Previous for movement within an animation. Do not duplicate these controls in page headings or the animation footer. On Page 3, label the primary refinement action `Run Refinement`.

Give Page 1 a concise title that frames it as the place to start a new case or reopen a previous review; do not add an explanatory paragraph beneath it. Keep the two intake cards with uppercase headings `CASE IDENTITY` and `EVIDENCE UPLOAD`. The evidence area must be visually empty initially and the extraction button disabled; do not render a `No evidence loaded` message. Add a compact `Auto` button that loads the seven prepared demo files one by one with visible progress and a short arrival animation. Keep extraction disabled until all seven sources are ready. Choosing or dropping local files must cancel any active auto-load and populate the evidence state directly.

Give Page 2 and Page 3 equally concise headings with one plain-language explanatory paragraph. Page 2 explains human correction before investigation; Page 3 explains final review of the narrative, risks and evidence trail.

## V12 Page 2 evidence-review layout

- Remove the persistent `Original-document attachment` side panel and its Bill of Lading preview.
- Use one full-width review workspace: bank-held baseline first, followed by the proposed key-value extraction register.
- Use uppercase Page 2 section titles: `PROFILE`, `KEY INSIGHT EXTRACTION`, and `ANALYST FEEDBACK`.
- Add a fourth `Source document` column to every extraction row. Show the exact source filename, source type/agent, confidence and a compact `View raw` action.
- Opening a source action displays that raw mock file in a modal for human verification, including the source excerpt, extracted fields and confidence factors. Closing the modal returns to the same extraction row without changing its value.
- Keep extracted values directly editable and retain the confidence and human-edit states.
- Place `Analyst correction rationale & reusable insight` below the extraction register. Capture both the case-specific correction rationale and an additional reusable extraction instruction supplied by the human.
- Do not show a `Recall in future extractions` control or an insight-scope selector. Save any non-empty reusable instruction automatically into case memory and record it in the decision trace.
- Move Page 2 helper descriptions from visible captions into native hover tooltips on the corresponding uppercase section titles, including PROFILE, KEY INSIGHT EXTRACTION and ANALYST FEEDBACK.
- Apply the same hover-help pattern on Page 1: move the CASE IDENTITY, EVIDENCE UPLOAD and CASE HISTORY descriptions into native title tooltips and remove their visible helper lines.
- Label the Page 1 simulated entity-registry and adverse-news switch `Web Research`.
- Do not show the `Your agent workforce` label above the animation roster; keep only the active-agent status indicator.

Add a `CASE HISTORY` table below the Page 1 intake cards with one completed case per row. Show the case/customer, the person who created it, creation date, final recommendation and a `Detail` button. Include three fictional cases with visibly different outcomes, but do not show a separate `3 COMPLETED CASES` count. Detail opens a case-specific, read-only Page 3 report. Historical review must not show Refinement or the animation Back control. Replace those controls with `Copy to New Case`, which returns to Page 1 with the historical customer identity and prior-case reference populated and an empty evidence area ready for new or additional documents. Do not show a copied-case banner.

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

### Frame 1 — Email context

- Activate `Context Agent` first.
- Show a machine-learning TER trigger model receiving either email or document inputs and detecting a potential trigger event.
- Use a recognizable envelope icon—not only `EML` text—for the email input and Context Agent roster badge.
- Make the primary visual read `Email / Document → Event understanding`; place the `TER TRIGGER MODEL · Potential trade anomaly detected · Email + document inputs routed for context review` card underneath as supporting context.
- Route the ML trigger result into Context Agent; the model detects and routes, while Context Agent understands and explains the TER context.
- State `Understanding the TER trigger event from ML-routed email and document signals`.
- Reveal what happened, who is involved, the event chronology and the unsupported-credit-note gap.
- Hand the email context and evidence gap to Data Analyst.

### Frame 2 — Internal-data analysis

- Activate `Data Analyst / Internal Data Agent` after Context Agent.
- Show two distinct actions and two staged outputs:
  1. `Querying and extracting related transaction data`.
  2. `Querying customer profile and related-client profile data`.
- Treat XLSX/ledger and bank profile data as structured SQL work, not OCR/VLM work.
- Hand the analyzed transaction/profile baseline to Document Intelligence Agent.
- Change `External Web Agent` from queued to ready after both SQL results are published.

### Frame 3 — Short-document parsing

- Activate the unified `Document Intelligence Agent`.
- Show it parsing the commercial invoice, two-page supply contract, and customs declaration as one short-document batch.
- Present VLM as the only reading tool used by this agent in the short-document main canvas. Do not show OCR in this frame.
- In the main canvas, reveal the action first, then publish the three document results one by one.
- Retain invoice value/goods/counterparty, contract terms/gap, and customs HS-code conflict.

### Frame 4 — Long-document OCR → LLM → Validate

- Keep the same unified `Document Intelligence Agent` active; OCR and LLM are tools, not separate workforce agents.
- Process the 12-page KYC profile and 8-page bill of lading.
- Present the main-canvas sequence explicitly as `OCR → LLM → Validate`; do not show VLM in this frame.
- OCR scans pages and reconstructs reading order; LLM structures profile fields, tables, stamps and cargo-description content; Validate tests page order, field agreement and the low-confidence cargo overwrite signal.
- Keep the animated scanner, live page/token counters and validation checks, but do not add separate KYC/Bill-of-Lading published-result cards or a duplicate Document Intelligence handoff beneath the workbench.
- Use the left-panel `OUTPUT / HANDOFF` as the authoritative summary for this frame.
- End with the complete seven-source case memory handed to Orchestrator for investigation.
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

Preserve the progressive v12 information design and the current document animation inside the **main canvas**.

### Short-document stage

- Begin with a compact three-file intake tray for invoice, contract and customs declaration.
- Animate the current file rising from the tray into a scanner.
- Run a visible red scan beam over the page while text and table regions become highlighted.
- Show a small live file counter such as `FILE 1 / 3` and a parser status that changes from `READING` to `KEYS FOUND`.
- Publish invoice, contract and customs result cards one at a time after the scan component appears.
- Keep the story accurate: the VLM reads text, tables, clauses, stamps, layout and source regions from short, digitally legible files; OCR appears only in the long-document pipeline.

### Long-document stage

- Reuse and refine the v7 visual language: stacked pages, continuously moving OCR beam, live page/token counters, animated LLM extraction fields, and file-level validation checks.
- Show the exact sequence `OCR → LLM → Validate`.
- Visually distinguish the two documents being processed: 12-page KYC profile and 8-page bill of lading.
- The LLM workbench should structure profile grids, table content, stamps and the cargo-description field from the OCR output.
- Validation checks should animate in sequence and visibly flag the low-confidence cargo-region overwrite.
- Do not repeat the completed KYC/Bill-of-Lading results or handoff below the workbench; the active-agent dialogue carries the frame output and next handoff.

### Motion constraints

- Scanning motion continues while the frame is held, but it must not advance the presentation automatically.
- Keep scan effects purposeful and readable; avoid decorative particles that do not explain the work.
- Respect `prefers-reduced-motion` and keep mobile layouts usable by stacking the OCR, LLM and validation workbenches.
- Do not restore v7’s low-value `LIVE FRAME` footer sentence.

## Workforce roster

Use this stable roster across the extraction and refinement animations:

- `OR` — Orchestrator: plans, delegates and synthesizes.
- `DI` — Document Intelligence Agent: owns document parsing, OCR + LLM reading, VLM layout reasoning and key-value extraction.
- `CT` — Context Agent: reconstructs email context and claims.
- `DA` — Data Analyst: runs transaction/profile SQL and rankings.
- `ER` — Entity Resolver: resolves exact entities, jurisdictions and directors.
- `EW` — External Web Agent: runs simulated NOB and adverse-news searches.
- Give External Web Agent a distinct, clearly visible blue `WEB` logo badge in the workforce roster, including when it is active.
- `QA` — Evidence QA: validates citations, confidence and source convergence.
- `RN` — Risk + Narrative: converts validated findings into report language.

For Animation 2, show a focused dynamic roster of Orchestrator, Investigation Agent and External Web Agent. Investigation Agent owns cross-checking, target ranking, mismatch analysis, risk validation and the terminal key-risk/red-flag summary. External Web Agent performs the selected entity deep dive. Do not rerun or display Data Analyst because transaction, profile and document data are already available from Animation 1.

For collaborating stages, highlight the lead agent and show collaborators in the active dialogue or as a small status annotation. Never expand more than one reasoning dialogue at a time.

### Talking-dialogue behavior

- Style the expanded active-agent dialogue as a familiar speech bubble attached to the agent icon.
- Reveal its message naturally, word by word, as if the agent is talking.
- Show a small animated typing indicator before the first words appear.
- Reveal `TASK`, `ACTION`, `REASONING SUMMARY`, and `OUTPUT / HANDOFF` in sequence rather than displaying the full bubble immediately.
- Keep the final message visible after typing completes.
- Restart the word-by-word animation whenever the presenter enters a new frame.
- For reduced-motion users, show the complete dialogue immediately.
- Increase the smallest animation text, especially workforce capabilities, statuses, structured dialogue labels/body text, evidence-card labels and network annotations. Maintain hierarchy while avoiding 6–8px body copy on desktop.
- The right-side `Structured actions and results` canvas must begin directly with the frame-specific result. Do not repeat `Retained results` or `Active work` strips because the workforce panel already communicates state and active ownership.

## Animation 2 — four-frame dynamic investigation

1. Orchestrator hands the ready evidence case to Investigation Agent without repeating data extraction.
2. Investigation Agent cross-checks customer, transaction and document evidence, ranks entities by mismatch/materiality/evidence gaps, and selects the highest-risk entity or client for deep dive.
3. External Web Agent searches the selected entity’s core business activity and adverse-news signals using traceable simulated queries. Preserve negative searches and unconfirmed leads as validation gaps.
4. Investigation Agent reconciles internal and open-web evidence, confirms plain-language mismatches, identifies key risks and red flags, distinguishes supported findings from open gaps, and hands the validated outcome to human review.

In Frame 4, add a prominent three-step conclusion path and make it correction-aware: `Human-approved shipping value → Independent customs + open-web challenge → Validated risk`. Redraw the evidence network as a directional chain that joins the CORE-KYC stationery baseline and copy-paper invoice to the customer, follows the USD 301,760 payment to Aster Peak FZE, and then keeps three evidence branches distinct: the analyst-approved Shipping goods value, customs HS 8461.50 cutting-machine classification, and External Web Agent confirmation of Aster Peak's industrial-machinery business. Use distinct colors and an explicit legend for baseline evidence, payment flow, human input, customs conflict and web validation.

Use the same visible red-flag icon for the `INDEPENDENT CUSTOMS` and `OPEN-WEB VALIDATION` badges in Frame 4. Keep the source labels and evidence statements unchanged.

## V12 human-correction propagation

- The `Shipping goods` field in Proposed key-value extraction remains directly editable.
- When its value differs from the agent proposal `CNC cutting equipment`, mark the row `HUMAN EDIT` and preserve the exact analyst-entered wording.
- Record the before/after correction and optional analyst rationale in the decision trace when evidence is approved.
- Propagate the approved value into target selection, the Frame 4 correction banner, conclusion path, evidence network, cross-source comparison, risk explanation, Page 3 report and Nature-of-business appendix.
- Show the Page 3 correction banner only when the analyst actually changes Shipping goods. Do not render an `Agent extraction approved` banner for the unchanged proposed value.
- Never overwrite or relabel customs evidence with the human-edited shipping value. Customs remains the independent `HS 8461.50 · cutting machines` source, and open-web research remains a separate counterparty-business source.
- If the edited shipping value still describes machinery, explain that customs and open web corroborate it. If it no longer describes machinery, treat the human value as an outlier challenged by customs and open web; do not silently force convergence.

In Frame 4, show only the two supported finding cards: `Nature-of-business mismatch` and `Rapid onward movement`. Do not add a separate `Why Partial Exit / Ultimate recipient not yet resolved` card; the recommendation panel owns that rationale.

The left panel contains Orchestrator, Investigation Agent and External Web Agent. The active dialogue and handoff must visibly move between those agents. The main canvas progressively animates cross-checking, risk-ranked target selection, open-web deep dive and terminal evidence/risk reconciliation. Retain previous results as chips.

## Animation 3 — five-frame refinement

Use a five-stage escalation story:

1. The analyst asks the agents to trace the USD 204,300 rapid onward payment and identify its ultimate recipient.
2. Data Analyst reconstructs the two-hop flow: Orchid Meridian → Aster Peak FZE → Vale Industrial Holdings within 24 hours.
3. Entity Resolver and External Web Agent confirm Vale Industrial’s exact identity, common controller with Aster Peak, and a two-source simulated adverse-news match.
4. Evidence QA joins the transaction path, registry control link and attributed adverse-news sources into one auditable escalation chain.
5. Risk + Narrative explains why the new evidence changes the recommendation from Partial Exit to Full Exit.

Render every stage through the same workforce roster. Preserve the distinction between verified bank transactions, registry facts and attributed simulated adverse-news allegations. Make the before/after decision threshold explicit in the final frame.

## Page 3 decision storyline

- Before refinement, show a yellow `PARTIAL EXIT` recommendation.
- The initial report contains exactly two risk disclosures: `Nature-of-business mismatch` and `Rapid onward movement`.
- Do not render a duplicate `REPORT DECISION · Partial Exit` block inside the initial report body; the right-hand recommendation panel is the sole initial decision summary.
- Make the nature-of-business conflict self-explanatory wherever it appears in the animation: define the expected stationery trade as paper, pens and office supplies; define CNC equipment as computer-controlled machinery used to cut and shape metal (including aluminium); and show the comparison explicitly as `Office stationery ≠ computer-controlled metal-cutting machines`.
- Do not show `Major counterparty mismatch` as a separate initial risk; its underlying facts may support the NOB and flow analysis without being duplicated as a third finding.
- Explain why the exit is partial in assertive, risk-based language: the office-stationery profile cannot explain CNC machinery trading, and rapid onward movement creates credible trade-based money-laundering and layering risk, so trade finance must be exited now. Retain only restricted, enhanced-monitored non-trade servicing because the current evidence establishes product-level misconduct rather than relationship-wide exposure. Present fund tracing and linked-controller screening as required next steps, not as an open question.
- Make the Page 3 Partial Exit recommendation and its two supporting rationale cards responsive to the analyst-approved `Shipping goods` value. If the human value still indicates machinery, quote it and explain that it directly conflicts with the stationery profile. If it does not indicate machinery, quote it and explain that independent customs classification and open-web counterparty evidence challenge the human value; preserve the conflict rather than forcing convergence. In both branches, keep the recommendation Partial Exit until refinement verifies relationship-wide exposure.
- Use the bank's standard STR structure in the main Page 3 report. Keep `Executive narrative` visible, followed by foldable `TRIGGER`, `BACKGROUND`, `REVIEW`, and `JUSTIFICATION AND KEY RISKS` sections. Trigger explains the TER trigger context. Background uses bullets for entity details, SGD account `5952757454001`, LNS account `5012261745`, opening dates, corporate NOB, and sole director/shareholder. Review separates `KYC REVIEW` from `TRANSACTION REVIEW`, and groups transaction tables by type such as `REPAYMENT` and `DIRECT TRANSFER`; place the former material-transaction content here. The final section goes directly into the evidence-backed key-risk cards without introductory justification blocks, a redundant `KEY RISKS AND SUPPORTING EVIDENCE` heading, or a duplicated recommendation. Keep the single authoritative recommendation in the right-side decision panel.
- Stack the recommendation rationale vertically at every viewport width: Proven Risk or Unresolved Conflict first, a downward transition second, and Proportionate Action last. Do not use two narrow horizontal columns for these explanations.
- Do not show a provenance statement in the Page 3 recommendation panel.
- After refinement, reveal `Hidden major-counterparty adverse-news exposure` as a distinct third risk supported by the verified two-hop payment, exact entity/control resolution and attributed adverse-news match.
- Change the recommendation to a red `FULL EXIT` and explain that the new evidence expands the concern from a product-level trade-finance issue to relationship-wide exposure.
- Use a visible before/after decision comparison so the escalation is easy to present and audit.
- In the report header, use only `Suspicious Transaction Report`; remove `Agent-assisted draft`.
- Keep the report itself firm. Before refinement, show a single `REPORT DECISION · Partial Exit` block; do not show an `OPEN QUESTION`, `Who received the onward funds?`, or tentative follow-up wording inside the report.

## Content and footer requirements

- Remove all low-value small footer prose and animation legends.
- Keep supporting text readable across all three pages and all animation frames. Do not use 6–8px body copy; labels, captions, evidence annotations, table text and report content should remain legible at normal desktop zoom.
- Keep only frame count, progress bar, progress dots, Exit, Previous, animation-header Back and compact icon-only Next/Finish.
- Recommendation and provenance must appear once above Refinement; remove any duplicate placement.
- Recommendation starts as yellow `PARTIAL EXIT` and changes to red `FULL EXIT` only after refinement completes.

## Appendix report requirements

- Use the visible name `Appendix report`; do not call it a micro report.
- The report structure is: executive conclusion, evidence chain, an optional key-transactions table, and external references when present.
- Treat the evidence chain as the authoritative evidence summary. Do not add a separate Evidence register because it duplicates the chain.
- Make the evidence chain easy to understand with numbered evidence points and mock file links whose displayed names match the seven files loaded at the beginning of the demo.
- When a risk relies on transactions, add a compact table with `Name`, `Amount` and `When` columns.
- Do not display raw `bank://` or `evidence://` protocol strings.
- Put external HTTP(S) links only in a `References` section at the bottom of the appendix report, never inside the evidence chain.
- Do not include the Case/Risk rating/Confidence/Review status metadata strip.
- Do not include a `Limitations and next action` section.
- Apply the same structure to modal and printable appendix reports.

## Visual, accessibility and technical requirements

- Light panels, white agent rows, subtle dotted texture, restrained BANK red, green completion and grey queue states.
- No dark-grey progressive-routing block.
- No page-level horizontal overflow.
- Stack panels on mobile; keep agent status, active dialogue and controls readable.
- Native buttons, visible focus styling, dynamic Next/Finish `aria-label` and tooltip, and reduced-motion support.
- Clearly label all simulated registry/news content and fictional data.
- Keep all CSS, JavaScript and case data in one HTML file with no backend dependency.
- The Page 3 `Export` action must first open a print/PDF preview containing the main STR followed by every generated appendix report. The preview provides `Download PDF` and `Print / Save PDF` actions. Use compact flowing layout without forced blank pages or oversized gaps between the main report and appendices. PDF download uses an off-screen export clone, the case ID in the filename, and browser print only as a fallback when the client-side PDF exporter cannot load.

## Acceptance criteria

1. Prompt v12 and HTML v12 exist; v11 is unchanged.
2. Animation 1 has four grouped stages while visibly accounting for all seven sources.
3. The left panel is a compact icon-based workforce list, not a node-routing diagram.
4. Only the active agent expands a structured reasoning dialogue; hidden chain-of-thought is never shown.
5. Frame 1 begins with Context Agent email extraction; Frame 2 performs Data Analyst SQL analysis; Document Intelligence Agent owns Frames 3 and 4.
6. Long-document work is a separate `OCR → LLM → Validate` stage for KYC and bill of lading, with no VLM label in that frame.
7. Email context and internal-data SQL are separate, explicit stages and occur before document-intelligence processing.
8. Transaction SQL and profile/related-client SQL are distinct actions and outputs.
9. External Web Agent remains queued until the two Internal Data SQL results are published.
10. Completed processing collapses into retained-result chips on later frames.
11. Investigation has four dynamic frames; refinement remains five frames.
12. Recommendation/provenance appears once above Refinement.
13. Low-value animation footer prose is absent.
14. All controls, refinement, recommendation update, appendix reports, reset and printing continue to work.
15. The short-document stage visibly scans a three-file tray before publishing three results.
16. The long-document stage includes animated stacked pages, OCR beam, live page/token counters, LLM structured extraction and sequential validation checks.
17. No standalone Evidence QA normalization frame exists in Animation 1.
18. The active-agent speech bubble reveals its structured summary word by word and remains readable after completion.
19. Document Intelligence Agent is the only document-processing workforce role; OCR and VLM appear as its tools in the main canvas.
20. No workforce role or visible status is labelled `External Intelligence`; the role is consistently `External Web Agent`.
21. Every non-terminal handoff, next-delegation label, owner and queued state matches the exact active agent and task in the following frame across all three animations; terminal frames point to a human/report decision.
22. No legacy or phantom agent labels appear in the animation story when a stable workforce role owns that work.
23. JavaScript parsing, complete click-through, desktop/mobile rendering, horizontal overflow and browser console output are verified before delivery.
24. Animation 1 frame 2 ends after the OCR/LLM/Validate workbench; it does not repeat KYC/Bill-of-Lading result cards or a Document Intelligence handoff in the main canvas.
25. Appendix reports use the evidence chain as the only evidence summary; no duplicate Evidence register or limitations section is rendered.
26. Transaction-related appendix reports show Name, Amount and When, while external links appear only under References at the bottom.
27. Initial Page 3 recommendation is yellow Partial Exit and shows only Nature-of-business mismatch and Rapid onward movement.
28. The initial decision clearly states that the hidden onward-payment recipient is unresolved, preventing Full Exit.
29. Refinement traces USD 204,300 from Aster Peak to Vale Industrial, resolves common control and finds an attributed two-source adverse-news match.
30. After refinement, Page 3 and the final animation frame visibly compare Partial Exit with red Full Exit and explain the threshold change.
31. Animation 1 Frame 1 visibly shows `Email or document input → ML TER trigger model → Context Agent`, with the Context Agent explaining the trigger event.
32. External Web Agent uses a distinct blue `WEB` logo badge in its animation roster.
33. The report heading excludes `Agent-assisted draft`, and the pre-refinement report contains no open-question block.
34. Editing `Shipping goods` visibly changes its review-row state to `HUMAN EDIT` and preserves the exact analyst-entered value and rationale in the decision trace.
35. The approved Shipping goods value propagates through target selection, Frame 4, the final report and the Nature-of-business appendix without overwriting customs or open-web evidence.
36. Both correction branches are supported: machinery wording is corroborated at the category level, while non-machinery wording remains a visible outlier challenged by customs and open web.
37. The concept-demo label is absent; compact page-aware controls occupy the top-right header area with no duplicates in page headings.
38. Animation Back sits in the animation header and returns to the page immediately before that animation; the animation footer contains only exit, previous, progress/dots and next/finish navigation.
39. The Structured actions and results canvas contains neither Retained results nor Active work strips.
40. Animation workforce and evidence text is visibly larger while preserving desktop and mobile layout integrity.
41. Page 1 has a concise title without explanatory body copy and uses uppercase `CASE IDENTITY` and `EVIDENCE UPLOAD` card titles.
42. Evidence starts visually empty with no empty-state message, extraction is disabled, and `Auto` loads the seven prepared demo sources before extraction can begin.
43. Page 2 and Page 3 each have a concise title and explanation appropriate to their review stage.
44. Page 1 lists three completed historical cases in a table with case/customer, creator, creation date, final recommendation and Detail action.
45. Historical cases open a case-specific, read-only Page 3 report without Refinement or animation Back.
46. `Copy to New Case` returns historical identity context to Page 1 while clearing evidence so additional documents can be uploaded for a fresh review, without showing a copied-case banner.
47. Page 2 has no persistent Original-document attachment panel; the extraction register spans the available width.
48. Every extraction row includes its source document and a working `View raw` action that opens the correct mock file.
49. The human can provide a case-specific correction rationale plus a reusable extraction instruction without selecting a scope.
50. Any non-empty reusable instruction is stored automatically in case memory and written to the decision trace before investigation, without a recall toggle.
51. Page 1 Auto load reveals the seven prepared evidence files sequentially, shows numeric loading progress and enables extraction only after the final file arrives.
52. Editing Shipping goods changes the Page 3 Partial Exit recommendation copy and supporting rationale cards, with distinct machinery and non-machinery explanations.
53. Page 3 recommendation rationale cards use a full-width vertical sequence with risk above action.
54. Export opens a print/PDF preview showing the main STR and all appendix reports, then supports case-named PDF download or native print without forced blank zones.
55. Hidden live and historical Page 3 control panels are strictly mutually exclusive; the historical Final Decision and Reopen controls never appear in a live report.
56. Page 3 follows the standard STR structure: visible Executive narrative plus foldable Trigger, Background, Review and Justification and Key Risks sections; Review visibly separates KYC from repayment/direct-transfer transaction review.
57. The smallest meaningful text across intake, evidence review, animations and the final report is readable at normal desktop zoom.
