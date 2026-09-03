# Terminology

- **Target:** series whose future values are requested.
- **Past covariate:** auxiliary series observed only in the historical context.
- **Past-future covariate:** auxiliary series known through both context and forecast horizon.
- **Variate:** one channel/series in the multivariate grid.
- **Patch:** contiguous block of 32 time points represented as a token.
- **Causal temporal attention:** attention along time within one variate, restricted to current/past positions.
- **Full variate attention:** attention across series at a shared time position.
- **Zero-shot:** inference without task-specific fine-tuning; it does not mean no pretraining.
- **Quantile forecast:** predicted conditional percentile; nine quantiles span 0.1–0.9.
