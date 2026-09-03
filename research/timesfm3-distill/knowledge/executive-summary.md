# Executive summary

TimesFM-3 is best understood as masked completion over a time × series grid. It normalizes and patches every series, exposes known future covariates, alternates attention along time and across variates, then predicts the entire target horizon in one pass. It returns both a point estimate and nine quantiles. [source-001, source-003]

The architectural details unique to version 3 currently come from the Google Research launch post, model card, and public code—not a dedicated TimesFM-3 paper. The original TimesFM paper explains the patched decoder lineage. [source-001, source-002, source-003]
