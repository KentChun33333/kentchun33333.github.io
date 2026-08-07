# Prompt v2 — Orchestrator-Led BANK TER / STR Investigation Workspace

## Objective

Upgrade the existing standalone three-page BANK TER / STR concept demo into a more enterprise-ready, presentation-friendly investigation workspace. Preserve the fictional Orchid Meridian Trading case, the neutral BANK branding, the seven-document extraction demonstration, the human evidence-review step, the final STR refinement, and the single-file HTML implementation.

The redesign must make the investigation animation easier to follow while more accurately portraying multi-agent collaboration. The user should first understand the business outcome and investigation process, then see how an orchestrator dynamically brings specialist agents into the work.

Do not expose unrestricted model chain-of-thought. Show structured operational actions, evidence discoveries, confidence changes, source joins, validation results, and human approval points.

## Reference-informed product principles

Use four conceptual layers, but avoid showing all four as competing permanent panels:

1. **Executive outcome layer** — a compact strip at the top communicates the case, status, risk, confidence, elapsed time, evidence reviewed, and estimated analyst time saved.
2. **Business workflow layer** — a stable process communicates where the case is: Intake → Evidence → Analysis → Validation → Decision → Report.
3. **Work-product layer** — the dominant canvas shows what the investigation is producing: customer baseline, transaction ranking, entity resolution, source mismatch, relationship flow, validated finding, and draft report.
4. **Technical observability layer** — agent topology and structured execution states support the explanation without overwhelming it. Do not restore the removed “Evidence and Agent Events” column or a permanent backend agent room.

The interface should feel like a serious analyst workstation: dense but legible, restrained motion, minimal gradients, clear hierarchy, stable status colours, traceable tables, evidence cards and relationship diagrams. Avoid robot avatars, decorative neon effects and meaningless moving lines.

The existing case ID `TER-2026-00418` and Orchid Meridian Trading data remain the default demo case. The attached `SG-AML-2026-01842` outcome strip is a layout and information-hierarchy reference, not an instruction to replace the established case data. For the existing case, demonstrate comparable fields such as:

- Case: TER-2026-00418
- Status: Analysis running / Analyst review required / Ready for filing consideration
- Risk: Provisional high / High
- Confidence: dynamically updated, ending at the validated report score
- Elapsed time: simulated run time
- Evidence reviewed: reconcile seven uploaded documents with internal, transaction, registry and open-web evidence items
- Estimated analyst time saved: a clearly labelled simulated estimate

## Preserve the three-page human workflow

### Page 1 — Intake, upload and document processing

Keep the compact CIF, customer name and TER case ID inputs, seven prepared documents and simulated open-web-search switch.

Keep Animation 1 as the click-controlled, seven-frame OCR/VLM/file-investigation workflow. Each source must show:

- long-page OCR scanning, reading order and page/token progression;
- VLM layout reasoning over headers, tables, stamps, signatures and spatial relationships;
- file-investigation checks for oversimplification, missing detail, self-conflict or suspicious patterns;
- extracted values, source excerpt, confidence fusion and low-confidence explanations.

The contradiction remains: the invoice says premium copy paper, while the bill of lading and customs record show CNC cutting equipment / HS 8461.50.

### Page 2 — Human evidence review and orchestrator-led investigation

Keep editable extracted fields, the original-document attachment, confidence components, correction rationale and approval action.

After approval, replace the current static-feeling investigation network with an orchestrator-led, dynamically assembled working group. The animation remains click-controlled, but motion continues within each frame until the presenter advances.

Use a two-area composition:

- **Left: dynamic investigation topology.** Begin with the ORCH orchestrator only. The orchestrator selects a standard investigation stage, delegates work and adds only the agents needed for that stage. Newly added agents visibly connect, exchange structured evidence packets, challenge or validate a result, then remain, return to standby or hand control back to ORCH.
- **Right: dominant investigation work product.** Show the current customer table, transaction ranking, entity result, mismatch matrix, evidence join, graph or finding. This canvas must be larger than the topology and should explain the investigation even if the viewer ignores the animation.

Do not show a permanent “Evidence and Agent Events” panel. Do not stream free-form messages such as “Agent 1 thinks…” or “Agent 2 disagrees…”. Use concise operational events embedded in the relevant work product, for example:

- Customer profile retrieved · 18 records returned
- Transaction population ranked · 1,842 transactions processed
- New counterparty name discovered · Aster Peak FZE
- Registry identity resolved · exact name and jurisdiction match
- NOB mismatch test reopened · three independent source classes disagree with KYC
- Material claims validated · 7 of 7 citations supported

## Animation 2 — Six-frame iterative investigation loop

Keep six presenter-controlled frames, but make the left network and right work product materially different in every frame.

### Frame 1 — Orchestrator opens the standard investigation plan

- Start with ORCH as the only active node.
- ORCH lays out the stable business sequence: Client review → Transaction review → Mismatch review → Independent validation → Finding.
- Display the current stage as running; later stages are queued.
- Create a scoped hypothesis, not a conclusion: activity may not fit the stated business.
- Show which evidence classes are available and which are still required.

### Frame 2 — Client review establishes the internal baseline

- ORCH adds the KYC/Profile agent.
- KYC retrieves the internal customer profile: office-stationery wholesaler, expected USD 45,000 per month.
- KYC publishes a structured baseline to shared case memory.
- ORCH checks baseline completeness and advances to transaction review.
- The right canvas shows the customer profile and the limitations of the declared NOB.

### Frame 3 — Transaction review discovers a new name

- ORCH adds FLOW/Transaction and materiality support.
- FLOW ranks counterparties and identifies Aster Peak FZE as counterparty #1 at USD 301,760; Vale Industrial Holdings is counterparty #2 at USD 118,400.
- The major payment is joined to invoice OM-771.
- Aster Peak FZE becomes a newly discovered entity requiring resolution.
- ORCH dynamically adds the Entity agent and routes the new name for verification.
- The canvas shows the ranked transaction table and the reason for prioritising counterparty #1 without treating value alone as suspicious.

### Frame 4 — Entity discovery causes a loop back to mismatch review

- Entity and Web agents resolve Aster Peak FZE and capture a reproducible simulated registry URL.
- External activity is industrial machinery trading and CNC equipment.
- ORCH detects that this new fact changes the earlier assessment and visibly loops the workflow back to Mismatch review.
- ORCH adds Document and Customs agents to compare KYC, invoice, bill of lading, customs HS code and external registry activity.
- Animate evidence packets flowing back into the mismatch test rather than simply progressing left to right.

### Frame 5 — Multiple sources establish the NOB mismatch

- KYC, Document, Customs, Web and Transaction agents work as a temporary investigation group.
- The dominant canvas shows a source matrix:
  - CORE-KYC: office stationery wholesaler;
  - invoice OM-771: premium copy paper;
  - bill of lading SG-9381: CNC cutting equipment;
  - customs CD-2088: HS 8461.50 machinery;
  - Aster Peak registry: industrial machinery trader;
  - payment ledger: USD 301,760 to Aster Peak FZE.
- The group distinguishes nominal agreement from material contradiction.
- The mismatch becomes supported only after independent source convergence.
- ORCH hands the proposed finding to Evidence QA / Validation.

### Frame 6 — Validation forms the STR finding

- Add QA/Validation, Risk and Narrative agents.
- QA replays citations and reports supported material claims, open gaps and source classes.
- Risk promotes the supported NOB/counterparty mismatch and rapid onward movement into key risks.
- Narrative assembles the STR language from validated findings.
- Show the explicit reasoning path as work-product provenance: baseline → rank → discover entity → loop back → compare → validate → form finding.
- Keep Vale Industrial Holdings / counterparty #2 visibly queued for human-directed follow-up rather than prematurely promoting it to a risk.

## Page 3 — Final STR review, refinement and restart

Keep the readable STR narrative, transaction table, printable PDF action, no more than five foldable risks, source-to-finding explanations and human-directed refinement.

Retain the targeted counterparty #2 flow:

- isolate the USD 118,400 payment to Vale Industrial Holdings;
- confirm no supporting invoice or contract was supplied;
- resolve Adrian Koh as a director and common link with Aster Peak FZE;
- direct a visible, reproducible simulated web query;
- find the simulated procurement-fraud adverse-news lead;
- preserve the distinction between bank facts, registry facts and an unverified open-source allegation;
- add “Counterparty #2 adverse-news and common-director exposure” with an explicit confidence score and source trail;
- dynamically revise the narrative, recommendation, transaction evidence and decision trace.

Add a clearly labelled **Start new case** button on the final page. When clicked, it should:

- close any open animation and stop active timers;
- return to Page 1 with a smooth transition;
- reset the workflow stages, refinements, decision trace, confidence state and report additions;
- restore the seven prepared demo documents and default editable case values;
- avoid reloading the browser or leaving stale counterparty #2 findings behind;
- optionally ask for confirmation only if the analyst has unsaved edits.

## Interaction and presentation rules

- Keep Previous, Next, Replay and Exit controls for every animation.
- A frame remains visible until the presenter advances it.
- Animate state transitions that carry meaning: agent assignment, delegation, evidence retrieval, new-entity discovery, workflow loop-back, source comparison, validation and finding formation.
- The stable business workflow must remain visually distinct from the changing agent topology.
- The work-product canvas should occupy roughly two-thirds to three-quarters of the animation width.
- Agent nodes must not all appear at once. Add specialists when ORCH delegates the relevant task.
- Use shared case memory as a visible handoff mechanism, not as a raw chat transcript.
- Every material conclusion must link to realistic fictional evidence.
- Clearly label simulated registry/news sources and fictional data.
- Maintain responsive layout and keyboard-accessible native controls.
- Keep all CSS, JavaScript and data in the existing single HTML file with no backend dependency.

## Acceptance criteria

1. The final page includes a working Start new case action that fully resets the demo.
2. Investigation Animation 2 has exactly six click-controlled frames.
3. Frame 1 begins with only ORCH active; specialist agents appear dynamically as work is delegated.
4. The left topology visibly changes in every frame and illustrates delegation, collaboration and handback.
5. The right canvas shows a distinct, useful work product in every frame.
6. Aster Peak FZE is first discovered through transaction review, resolved externally, and routed back into a reopened NOB mismatch test.
7. The mismatch finding is not formed until KYC, transaction, document, customs and external registry facts converge and QA validates the citations.
8. Counterparty #2 remains queued in Animation 2 and is promoted only after human-directed refinement on Page 3.
9. No permanent event-ledger or backend-agent-room panel is reintroduced.
10. No raw chain-of-thought is displayed; only structured operational events and evidence-grounded findings are shown.
11. Replay, Previous, Next, Exit, PDF printing, evidence disclosures and report refinement still work.
12. JavaScript syntax, full reset behaviour, frame persistence, responsive layout and browser runtime are verified after implementation.

