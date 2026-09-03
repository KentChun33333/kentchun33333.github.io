# Feedback log

| Feedback | Affected Output | Failure Pattern | Severity | Skill Update Needed? | Correction |
|---|---|---|---|---|---|
| When Input → Model → Output tensor contracts exist, use a left–middle–right layout. | `timesfm3-system-demo` and future system demos | The contract existed, but reusable guidance did not guarantee that all three regions remain the primary persistent architecture during interaction. | Medium | Yes; the rule generalizes to tensor-based system explainers. | Require persistent input-left, model-middle, output-right desktop layout; synchronize interactions across regions; stack semantically on narrow screens. |
