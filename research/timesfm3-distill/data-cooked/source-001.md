# Cooked Source: source-001

- Raw file: `data-raw/sources.md` (Google Research TimesFM-3 launch post entry)
- Type: HTML article
- Parser: direct web extraction
- Parsed at: 2026-09-02
- Confidence: high
- Notes: Architecture and benchmark statements are author claims; exact benchmark values are presented primarily as plots.

---

TimesFM-3 is a 330M-parameter, zero-shot multivariate forecaster pretrained on more than one trillion real and synthetic time points. It accepts multiple targets, past-only covariates, and past-future covariates. Each series is normalized separately and split into contiguous patches of 32 steps. A target or past-covariate token comes from one patch; a past-future covariate token concatenates current and future patches as a lookahead signal.

The transformer operates on a time × variate grid. Causal temporal attention runs horizontally within one series and only sees past tokens. Full variate attention runs vertically across all series at the same time location. These mechanisms alternate through the transformer stack.

For inference, masked placeholders cover the future horizon. Targets and past-only covariates are masked there, while known future covariates remain visible. Alternating attention fills all future patches in a single forward pass. The model emits a point forecast and nine quantiles from 0.1 through 0.9 for every target and horizon step.

The post reports top average rank among pretrained foundation models on GIFT-Eval, FEV-Bench, and TIME, for point and probabilistic metrics. This is a benchmark claim, not a guarantee for every dataset.
