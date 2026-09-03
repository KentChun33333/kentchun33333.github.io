# Implementation notes

- Treat timestamps and horizon coverage as hard validation, especially for future-known covariates.
- Public examples use `(num_variates, context_length)` arrays and return `(num_targets, horizon)` point arrays plus `(num_targets, horizon, 9)` quantiles. [source-003]
- The public checkpoint configuration reports patch 32, horizon patch 64, 20 layers, dimension 1280, and 16 heads. [source-003]
- The interactive web chart is a deterministic teaching fixture; it must never be labeled as live TimesFM-3 inference.
- Before any real deployment, run rolling-origin backtests and quantile calibration checks, and confirm the current model-weight license permits the intended use.
