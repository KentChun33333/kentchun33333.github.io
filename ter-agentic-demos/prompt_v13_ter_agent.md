# Prompt v13 — Compact Review Controls and Case Detail Export

## Objective

Create `ter-bank-multi-agent-flow-v13.html` as a standalone evolution of v12. Preserve v12 unchanged and retain its complete three-page journey, evidence processing, human correction, investigation, refinement, historical review, appendices, PDF export, autoplay and Partial Exit-to-Full Exit storyline.

## Required changes

1. Add a dedicated `CIF ID` column to the Page 1 historical-cases table. Add a CIF search field above the table that filters rows immediately and shows a clear no-match state.
2. Replace the `ANIMATION 1`, `ANIMATION 2` and `ANIMATION 3` kicker labels with the common title `AGENT UNDER THE SCENE`. Keep the frame-specific main titles unchanged.
3. Add `Download detail (.zip)` beside Page 3 `Export`. The ZIP must contain the rendered report, structured case JSON, evidence manifest, decision trace and a short README. Support live and historical cases.
4. Move the Page 3 Refinement controls into a fixed bottom-right floating component. Make it foldable with a clearly labelled toggle and accessible expanded state. Keep it usable on mobile and exclude it from print/PDF output.
5. Add `Approve recommendation` directly below the Page 3 recommendation section. Record the approval in the decision trace and visually lock the approved state. A recommendation change from Partial Exit to Full Exit requires a new approval.
6. Put `Financial Crime Operations · Multi-Agent TER / STR Studio` on one line and reduce the global header height for a more compact presentation.

## Follow-up changes

7. Add `Lookback date` and optional `Related entity` inputs to Page 1 case identity. Preserve both values in the case-detail ZIP.
8. Consolidate Page 2 analyst correction rationale and reusable extraction guidance into one `Analysis feedback` input. Use the single value in the human correction, decision trace and reusable case insight.
9. Convert Refinement from a bottom-right floating component into a fixed, foldable left panel with a larger input area.
10. Let each animation settle into a static completed last frame. Stop dialogue and decorative motion after completion. For Animation 1, process the long documents once and hold the visible terminal state at `B/L · PAGE 8 / 8` instead of looping or becoming empty.

## Acceptance criteria

- v12 files remain unchanged; v13 HTML and prompt exist separately.
- CIF search filters only the historical table and Detail continues to open the correct original case.
- All three animation modes display `AGENT UNDER THE SCENE`.
- ZIP generation produces a case-named `.zip` without affecting PDF export.
- Refinement floats and folds without covering the recommendation, and historical review does not show live refinement controls.
- Recommendation approval is traceable and resets after decision escalation.
- Page 1 exposes and exports the lookback date and optional related entity.
- Page 2 contains only one analyst-feedback textarea.
- The Refinement drawer is fixed on the left and remains foldable.
- All three animations retain populated final-frame content without continuing motion.
- Animation 2 keeps its assembled evidence relationship graph visible at the top of the final validation frame.
- JavaScript parses successfully and the new controls have working event handlers.
