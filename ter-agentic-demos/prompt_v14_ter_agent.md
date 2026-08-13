# Prompt v14 — Queue-Driven Case Workflow

## Objective

Create `ter-bank-multi-agent-flow-v14.html` as a standalone evolution of v13. Preserve every earlier version unchanged, retain the existing evidence, investigation, refinement, report, export and animation content, but replace the forced page-animation-page journey with a Page 1 case-work queue.

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

- v13 files remain unchanged and v14 HTML/prompt exist separately.
- The normal workflow never forces an animation between human pages.
- Page 1 is the return point after case submission, Page 2 submission, Page 3 refinement and recommendation approval.
- One active case row progresses through evidence review, STR review and approved states without duplication.
- Detail routes active work to Page 2 or Page 3 according to status.
- Agent Work opens the latest completed agent stage and Back returns to Page 1.
- New-case intake folds and reopens from its summary control.
- CIF search continues to filter active and historical rows.
- Existing v13 animation completion behavior, report export, ZIP download and Page 3 refinement drawer remain functional.
- Investigation and Refinement final frames explicitly reveal every delayed element before freezing and retain a populated three-part terminal outcome strip in both playback locations.
- JavaScript parses successfully and all new queue controls have working event handlers.
