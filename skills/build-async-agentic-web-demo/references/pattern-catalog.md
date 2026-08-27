# Pattern catalog

## Contents

1. Queue
2. Evidence intake
3. Review workspace
4. Agent playback
5. Refinement
6. Knowledge comparison
7. Visual system

## Queue

- Combine active and historical cases in one searchable table.
- Use separate columns for status, recommendation, agent work, and next action.
- Route `Detail` from status.
- Keep archived cases read-only and let users copy their context into a new case when useful.
- Collapse intake after successful submission so the queue regains visual priority.

## Evidence intake

- Support both a deterministic `Load demo evidence` action and local file selection.
- Reveal demo files progressively to create believable activity without blocking the user.
- Retain filenames, source type, and provenance in state.
- Disable submission until minimum evidence is ready.

## Review workspace

- Use native `<details>` sections for dense evidence groups.
- Keep primary extraction sections open initially; collapse secondary context.
- Put analyst feedback in a sliding or sticky drawer.
- Pair confidence with source context; confidence alone is not provenance.
- Provide bulk convenience actions such as accepting high-confidence fields while preserving individual review.

## Agent playback

- Use a workforce roster plus a result canvas.
- Give every active agent a visible task, action, reasoning summary, and output/handoff.
- Use three to five frames; more frames usually dilute the story.
- Provide Previous, Next, replay, progress, Exit, and Escape.
- Stop autoplay on manual navigation.
- Fully render the terminal outcome before freezing the final frame.

## Refinement

- Put the recommendation and human response in a foldable drawer.
- Offer suggested instructions without forcing one.
- Accept optional supporting files and retain their names.
- Show that refinement is scoped from the human instruction.
- Return the case to the queue after completion and attach refinement as the latest agent stage.

## Knowledge comparison

For demos about memory, graph knowledge, or enriched context, include a controlled on/off comparison. Keep the same visible inputs and change only the capability under test. Show the downstream difference in findings and recommendation; do not merely change a badge.

## Visual system

- Use CSS custom properties for brand, semantic status, paper, background, borders, and shadows.
- Give the human workspace and “under the scene” agent playback distinct visual treatments.
- Use color and text together for status.
- Prefer CSS/SVG charts over raster screenshots so the demo stays responsive.
- Support `prefers-reduced-motion` and avoid animation as the only carrier of meaning.
