# Workflow reference

```text
[Targets + covariates] --> [Validate + normalize]       --> [Aligned normalized arrays]
[Context time points]  --> [Patch + token construction] --> [Time × variate token grid]
[Masked target horizon] --> [Alternating attention]      --> [Contextual target states]
[Target states]         --> [Single-pass forecast head]  --> [Point + 9 quantiles]
```

Canonical details: see `../analysis/core-thought-model.md`. [source-001, source-003]
