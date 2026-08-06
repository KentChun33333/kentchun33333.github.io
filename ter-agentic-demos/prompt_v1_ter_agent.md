/Users/kentchiu/.zshenv:.:1: no such file or directory: /Users/kentchiu/.cargo/env
# Prompt v1 — BANK Multi-Agent TER / STR Demonstration

Create a second, standalone single-file HTML demonstration for an agent-assisted bank-compliance Trigger Event Report (TER) and Suspicious Transaction Report (STR) workflow. Use a neutral BANK visual schema—red, white and warm grey; compact professional typography; strong evidence traceability—and clearly label the experience as a fictional concept demo. Use a generic BANK wordmark with no real financial-institution branding.

## Core experience

Design a modern, presentation-ready three-page workflow with three full-screen, click-controlled multi-agent animations. The interface must be easy to follow in a live demonstration, with a compact human workspace and a visually expressive agent layer. Every animation must advance one frame at a time using Previous, Next, Replay and Exit controls. A frame must remain on screen until the presenter advances it, but its contents should animate dynamically when entered: agents activate in parallel, evidence packets travel between nodes, confidence bars grow, source rows highlight and findings assemble visually.

Do not portray the system as one agent completing one task after another. Show coordinated working groups with an orchestrator, document agents, profile/KYC agent, transaction agent, entity-resolution agent, open-web research agent, network agent, risk agent and evidence QA agent. Their messages should include agreements, challenges, confidence changes and traceable source references.

## Page 1 — Compact intake and evidence upload

Collect editable CIF, customer name and TER case ID. Include a compact drag-and-drop/upload area populated with seven fictional documents: KYC/CDD profile, commercial invoice, supply contract, bill of lading, customs declaration, customer email and account statement. Include an open-web-search enablement switch.

The main demonstration case is Orchid Meridian Trading, internally classified as an office-stationery wholesaler. The documents and transactions should form a coherent trade-based money-laundering scenario.

After the user starts processing, launch Animation 1: a frame-by-frame document-processing workflow. Each frame should clearly show which original document is being read, several agents working together, the extracted key-value fields, exact source excerpt, confidence score and why confidence is high or low. Show the confidence mechanism as a combination of OCR/read quality, field agreement and cross-source consistency. Include a visible contradiction: the invoice states premium copy paper while the bill of lading and customs declaration indicate CNC cutting equipment / HS 8461.50.

## Page 2 — Human review of extracted evidence

Show the bank-held customer profile beside editable proposed extraction values. Prioritise the low-confidence fields. The analyst must be able to edit a proposed value, inspect the original-document excerpt, enter a correction rationale, accept high-confidence values and approve the reviewed evidence set.

The key low-confidence item should be Shipping goods, initially extracted as “CNC cutting equipment” at approximately 74% confidence because of source-image quality and the contradiction with the invoice. Make the provenance and original-document attachment obvious.

After approval, launch Animation 2: a multi-agent cross-investigation and STR-drafting workflow. Dynamically build two principal red flags:

1. Nature-of-business mismatch: the bank profile says office stationery, while a reproducible simulated open-web search and counterparty registry indicate industrial machinery activity.
2. Major transaction counterparty mismatch: a material USD 301,760 payment to Aster Peak FZE is inconsistent with the customer’s stated NOB and expected USD 45,000 monthly turnover.

Show the source-to-finding logic visually: KYC table row, transaction table row, invoice, bill of lading, customs HS code, registry URL and a two-level transaction graph. The report must not appear until the evidence working group converges and evidence QA confirms the citations.

## Page 3 — Final STR review and iterative refinement

Present a readable STR report with a narrative, transaction summary, recommendation and no more than five key risks. Each red flag must be foldable and include a visual explanation of exactly which source records support it. Include a traceable open-web result and a focused transaction table.

Provide a human review input with a demonstration suggestion such as: “Check the abnormal counterparty’s directors and adverse-news links.” When submitted, launch Animation 3: a frame-by-frame targeted refinement workflow. The entity, web-research, network, risk and QA agents should:

- resolve Aster Peak FZE’s director, Adrian Koh;
- match the same director to a joined company, Vale Industrial Holdings;
- find a simulated adverse-news article linking that joined company to procurement fraud allegations;
- distinguish verified bank data from open-source leads and preserve the validation gap;
- add a new foldable key risk, “Director-linked adverse-news exposure,” with an explicit confidence score and source trail;
- revise the STR narrative and recommendation visibly after the presenter finishes the animation.

## Interaction and quality requirements

- Use realistic fictional data that remains consistent across documents, transactions, web results and report text.
- Include clear fictional-data and simulated-source labels; do not imply a production system belonging to any real bank.
- Keep each page compact and free of conventional tab navigation.
- Use smooth page transitions and purposeful micro-animation, but respect click-controlled pacing.
- Make replay available for all three animations from the relevant page.
- Make the report printable through the browser’s Print / Save PDF function.
- Use accessible native buttons, inputs, textareas and disclosure elements.
- Keep all CSS, JavaScript and dummy data in one HTML file, with no backend dependency.
- Verify JavaScript syntax, frame persistence, replay, editable extraction review, risk disclosure behaviour and report refinement.
