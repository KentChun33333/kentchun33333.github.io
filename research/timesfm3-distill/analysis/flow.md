# Runtime flow

1. Validate targets, context, horizon, and optional covariate lengths. [source-003]
2. Normalize each variate separately and divide it into 32-step patches. [source-001, source-003]
3. Construct regular tokens for targets/past-only covariates and lookahead tokens for past-future covariates. [source-001]
4. Append masked horizon placeholders; keep known future covariate values visible. [source-001]
5. Alternate causal temporal attention and full variate attention through the stack. [source-001]
6. Decode every horizon patch together in one forward pass. [source-001]
7. De-normalize and return point plus nine-quantile forecasts for each target. [source-001, source-003]

Alternate path: without covariates or multiple targets, the same checkpoint can run in univariate mode. A future covariate that is missing or unknowable cannot provide lookahead information.
