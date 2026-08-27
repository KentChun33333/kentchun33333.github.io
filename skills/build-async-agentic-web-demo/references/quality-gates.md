# Quality gates

## Workflow

- One active case advances without duplication.
- Each submission returns to the queue and does not force playback open.
- Detail routing matches status.
- Agent work opens the latest completed stage.
- Historical cases remain read-only.
- Search/filter includes active and historical rows.

## Human control

- Consequential recommendations require explicit review.
- Original evidence, corrections, filenames, and audit events are retained.
- Refinement accepts a human instruction and optional documents.
- Conflicting actions are disabled while work is running.

## Playback

- Previous, Next, replay, Exit, Back, and Escape work.
- Replaying cancels old timers.
- Manual navigation stops autoplay.
- Final frames reveal all delayed content and stay populated.
- Agent copy shows bounded reasoning summaries, outputs, and handoffs.

## Trust

- Simulated data and sources are visibly labeled.
- No fixture implies a real transaction, approval, search, or API call.
- Confidence appears with provenance and context.
- Sensitive or regulated scenarios include the appropriate disclaimer.

## Frontend

- HTML and inline JavaScript parse successfully.
- IDs are unique and event targets exist.
- Empty, loading, completed, and error states are represented.
- Layout works at 360 px and desktop widths.
- Focus indicators, labels, keyboard exits, and reduced-motion behavior exist.
- No console errors occur through the full happy path.
