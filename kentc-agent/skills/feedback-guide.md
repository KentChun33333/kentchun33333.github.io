---
description: Guide the user through providing structured feedback and save it to the workspace feedback/ folder.
---

Help the user turn their thoughts into clear, actionable feedback and save it in the workspace `feedback/` folder.

## Workflow

1. **Pre-fill from context**: Extract any details the user already gave (target feature/file, issue, or suggestion). Only ask for what is missing or unclear.
2. **Guide concisely**: Ask short, focused questions to clarify:
   - **Category**: `bug`, `ux-friction`, `feature-request`, `agent-behavior`, `praise`, or `other`
   - **Target / Context**: Which file, feature, or workflow this relates to
   - **Summary**: One-sentence title
   - **Details**: What happened vs. what was expected (for bugs/friction), or what is desired and why (for improvements)
   - **Priority** *(optional)*: `low`, `medium`, `high`, or `blocker`
   - **Suggested Action** *(optional)*: Concrete next step or workaround
   Keep it lightweight—do not force optional fields if the user just wants to leave a quick note.
3. **Save to workspace**: Write the feedback as a Markdown file at `feedback/YYYY-MM-DD-<short-kebab-slug>.md` (append `-2`, `-3`, etc. if that filename already exists; never overwrite existing feedback).

Use this Markdown structure:

```markdown
---
date: YYYY-MM-DD
category: <category>
priority: <priority or unspecified>
target: <component, file, or workflow>
status: open
---

# <Summary>

## Details
<Clear description of the feedback, including actual vs. expected behavior if applicable.>

## Suggested Action
<Concrete next step, or "None specified.">
```

4. **Confirm**: Verify the file was saved and tell the user the exact path.
