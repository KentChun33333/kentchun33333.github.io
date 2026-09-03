# Component dependencies

- Input adapter owns shape and horizon contracts. Bad alignment invalidates all later stages. [source-003]
- Per-variate normalization precedes shared transformer processing so series with unlike scales can coexist. [source-001]
- Lookahead token construction depends on future covariates actually being known across the horizon. [source-001]
- Temporal attention preserves chronology; variate attention carries cross-series information. Both are required for the full multivariate mechanism. [source-001]
- The quantile head depends on the final target representations and returns nine uncertainty bands, not calibrated guarantees. [source-001, source-003]
