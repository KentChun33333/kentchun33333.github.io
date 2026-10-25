---
description: Extract key values from one document, each with its location and a confidence score.
---

Read the document named by the `file` input with `read`.

- Extract only what the document states.
- Every value carries its location (page, sheet + row, slide, e-mail part, paragraph).
- Confidence is 0-100: how sure you are the value is read correctly and complete.
- Read the file once. Re-read it only with a precise question when a value is unclear.
- Keep strings short; no repetition of the inputs.

When `feedback` is given, the analyst says the previous answer (the `previous` input) was wrong or incomplete.
Re-read the document for those points (read with a precise question) and correct them. Keep the other values
unless they are also wrong.
