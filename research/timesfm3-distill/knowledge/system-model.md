# System model

Input contract: target `(T, C)`; optional past-only `(P, C)`; optional past-future `(F, C+H)`; positive horizon `H`. Core: per-variate normalization → 32-step patches → residual projection → alternating causal-temporal/full-variate transformer → horizon head. Output: point `(T, H)` and quantiles `(T, H, 9)`. [source-001, source-003]
