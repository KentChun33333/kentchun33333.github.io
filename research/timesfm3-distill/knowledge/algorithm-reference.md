# Algorithm reference

1. Align all series and validate horizon coverage.
2. Normalize each variate independently.
3. Patch values in contiguous groups of 32.
4. Construct target/past tokens and lookahead past-future tokens.
5. Add masked horizon target tokens.
6. Repeat temporal causal attention and full variate attention across the transformer stack.
7. Map target horizon states to point and 0.1–0.9 quantile predictions.
8. Restore target scales. [source-001, source-003]
