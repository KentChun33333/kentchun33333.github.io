# Cooked Source: source-003

- Raw file: `data-raw/sources.md` (official repository and model-card entries)
- Type: Repository documentation and model card
- Parser: direct web inspection
- Parsed at: 2026-09-02
- Confidence: high
- Notes: Public code and weights may change after this snapshot.

---

The public interface accepts a target array shaped `(num_targets, context_length)`, optional past-only covariates shaped `(num_covariates, context_length)`, and optional past-future covariates shaped `(num_covariates, context_length + horizon)`. Forecast outputs have shape `(num_targets, horizon)`; quantiles have shape `(num_targets, horizon, 9)`.

The model card names a Stacked Mixing Transformer with Variate Attention and CPM Iterative RevIN, patch length 32, horizon patch length 64, 20 transformer layers, model dimension 1280, and 16 heads. The checkpoint is about 0.3B parameters.

The public TimesFM-3 weights are under the TimesFM Non-Commercial License v1.0 and are restricted from commercial or production use. The GitHub source code is Apache-2.0; these are distinct licenses.
