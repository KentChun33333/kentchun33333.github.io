# Prompt v15 — Trigger Context Review

## Objective

Create `ter-bank-multi-agent-flow-v15.html` as a standalone evolution of v14. Preserve every earlier version unchanged and retain v14’s queue-driven flow, evidence, OpenWeb review, investigation, refinement, report, export and animation behavior. Add a concise Trigger Context section at the top of Page 2.

## Required flow

1. Make the Page 1 new-case intake foldable. It is open initially and collapses after a successful case submission.
2. Rename the historical area to `CASE WORK QUEUE`. The table combines active work with completed historical cases.
3. Add distinct `Status`, `Recommendation`, `Agent work` and `Action` columns.
4. Submitting a new case performs extraction without forcing the animation open. Return to Page 1 and add/update the case row with `Evidence extracted · review required`.
5. `Detail` on that row opens Page 2. Submitting Page 2 performs investigation without forcing animation playback, returns to Page 1 and updates the row to `Investigation complete · STR review required`.
6. `Detail` then opens Page 3. Refinement submission returns to Page 1, updates the decision/status and attaches the Refinement animation to the row. Recommendation approval also returns to Page 1 and marks the case approved.
7. The `Agent work` button opens the latest applicable animation on demand: Extraction, Investigation or Refinement. Both Back and the final-frame completion control return to Page 1.
8. Preserve the static historical cases and their read-only Detail reports. Their archived rows do not need an active animation.

## Acceptance criteria

- v14 and all earlier files remain unchanged; v15 HTML/prompt exist separately.
- The normal workflow never forces an animation between human pages.
- Page 1 is the return point after case submission, Page 2 submission, Page 3 refinement and recommendation approval.
- One active case row progresses through evidence review, STR review and approved states without duplication.
- Detail routes active work to Page 2 or Page 3 according to status.
- Agent Work opens the latest completed agent stage and Back returns to Page 1.
- New-case intake folds and reopens from its summary control.
- CIF search continues to filter active and historical rows.
- Existing v13 animation completion behavior, report export, ZIP download and Page 3 refinement drawer remain functional.
- Investigation and Refinement final frames explicitly reveal every delayed element before freezing and retain a populated three-part terminal outcome strip in both playback locations.
- Page 1 treats Customer Name as optional and places Start Date beside Lookback Date in the same form row; both dates persist in active case data and detail export.
- The Refinement drawer does not display the decision trace; audit events remain retained internally for approval history and detail export.
- Page 3 does not propose Partial Exit, Full Exit or any other account strategy. Its recommendation card is a single `Next Step`: run an additional OpenWeb search to resolve the onward beneficiary and check relevant adverse news.
- The left refinement drawer presents that investigation scope for human review, includes an `Agree & Start Investigation` button, and provides a drag-and-drop multi-document upload zone. Uploaded filenames are retained in the case-detail ZIP manifest.
- Page 2 includes a responsive `OpenWeb Review` section beneath the extraction table. It presents key entity, business-profile and adverse-news findings with confidence/context labels, mocked traceable URLs and an explicit simulated-source notice.
- Page 2 begins with a responsive `Trigger Context` section above Profile and Key Insight Extraction. It summarizes the trigger event, profile deviation, customer explanation, initial evidence gap and routing rationale, while stating that no risk conclusion was made at trigger stage.
- JavaScript parses successfully and all new queue controls have working event handlers.
