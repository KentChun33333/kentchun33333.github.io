---
name: feedback-guide
description: >-
  Guides the user through providing structured, actionable feedback and saves
  it as a Markdown file in the workspace's feedback/ directory. Use this skill
  when the user wants to give feedback, report friction/issues, suggest
  improvements, or record a retrospective note in the workspace.
---

# Feedback Guide

Collect structured, actionable feedback from the user without overwhelming
them, then save it to the workspace `feedback/` folder for tracking.

## Workflow

### 1. Gather Context & Pre-fill
Before asking questions, extract any details the user has already provided in
the current message or recent conversation (e.g., target feature, file, error,
or suggestion). Only ask for what is missing or unclear.

### 2. Guide the User
Collect the following fields concisely (using `ask_question` for quick
multiple-choice picks when helpful, or a brief conversational prompt):

1. **Category**: `bug`, `ux-friction`, `feature-request`, `agent-behavior`, `praise`, or `other`
2. **Target / Context**: Which file, feature, workflow, or component this relates to
3. **Summary**: One-sentence title/summary of the feedback
4. **Details**:
   - *For bugs/friction*: What happened vs. what was expected
   - *For feature requests/improvements*: What is desired and why it helps
5. **Priority** *(optional)*: `low`, `medium`, `high`, or `blocker`
6. **Suggested Action** *(optional)*: Concrete next step or workaround

Keep the interaction lightweight—if the user gives a short note, do not force
every optional field.

### 3. Save to Workspace
Save the feedback as a new Markdown file under `feedback/` at the workspace root:

- **Path**: `feedback/YYYY-MM-DD-<short-kebab-slug>.md`
  - If a file with that name already exists, append `-2`, `-3`, etc. Never
    silently overwrite existing feedback.
- **Format**: Use neutral, clear Markdown:

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

### 4. Verify & Report
Confirm the file was written at the expected path and reply with a clickable
link to the saved feedback file.
