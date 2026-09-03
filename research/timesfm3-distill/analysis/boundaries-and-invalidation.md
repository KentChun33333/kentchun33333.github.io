# Boundaries and invalidation

- There is no dedicated TimesFM-3 paper in the official launch links as of 2026-09-02. Architecture depth beyond the blog, model card, and public implementation should not be inferred.
- Benchmark leadership is an average-rank claim over GIFT-Eval, FEV-Bench, and TIME; it does not establish superiority for every series, metric, horizon, or operating constraint.
- Cross-variate association is not causal identification. A promotion-correlated forecast does not prove the promotion caused demand.
- Known-future covariates help only when they are available and trustworthy at prediction time. Scenario assumptions should be stress-tested.
- Quantile forecasts express modeled uncertainty; calibration should be checked on local holdout data.
- The interactive sales chart is deterministic explanatory simulation, not a live TimesFM-3 inference endpoint.
- Public TimesFM-3 weights are non-commercial/non-production under their current license.

Invalidation test: compare TimesFM-3 against a seasonal naive model and strong task-specific baselines on a leak-free rolling-origin backtest. Reject deployment if local accuracy, calibration, latency, or license requirements fail.
