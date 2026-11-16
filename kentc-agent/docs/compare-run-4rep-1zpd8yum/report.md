# v1 vs current v2: 4-repetition comparison

Raw data: [memory.json](memory.json), [str.json](str.json), [str.artifacts/](str.artifacts/), [environment.md](environment.md),
console logs, `models-before/after.json`, `source-before/after.json`.

## Protocol and validity

- `docs/compare.md` main comparison: 4 repetitions per suite, sequential, order alternated by the harnesses.
  Commands: `compare_memory.py --repeats 4`; `str_benchmark.py --variants original,topics --repeats 4 --persons 40 --seed 7 --max-turns 80 --timeout 10800`.
- v1 = `src/kentc_agent/`; v2 = `src/kentc_agent_new_mem/` with #1 verify guidance, #2 chunked-write retry,
  #6 identical-repeat guard, #7 search-aware truncation (#3 removed). Both have the budget notice.
- Complete: memory 16/16 trials, STR 8/8. No source drift (all hashed files identical before/after).
  Same model, `n_ctx` 62,536 and case hash in every trial. Total wall time 4.2 h. Server cache not controlled.

## Memory suite (8 calls, read/bash)

| Case | v1 pass | v2 pass | Calls, median v1 / v2 | Prompt tokens, median v1 / v2 |
|---|---|---|---|---|
| buried_revision | 4/4 | 4/4 | 7.5 / 8 | 176,252 / 190,803 |
| failed_repair | 1/4 | 4/4 | 8 / 4 | 181,700 / **98,681** |

All three v1 failures are `live_verification` only: v1 ran the real `verify.py --strict`, saw exit 1, and printed
`EXIT:1` / `EXIT_CODE=1`; the unchanged rubric accepts only `EXIT=1` or `[exit code 1]`. **Substantively both
versions are 8/8.** The real difference is efficiency on failed_repair: v2 needs half the calls and tokens.

## STR suite (40 persons, 80 calls)

| Rep | v1 overall (A / B / C) | v2 overall (A / B / C) | Paired |
|---|---|---|---|
| 1 | 0.931 (0.72 / 1.00 / 1.00) | 0.933 (0.83 / 1.00 / 0.92) | tie |
| 2 | 0.642 (0.67 / 1.00 / 0.08), no HTML | 0.812 (0.72 / 0.96 / 0.67) | v2 |
| 3 | 0.663 (0.75 / 1.00 / 0.08), `IncompleteReply`, no HTML | 0.380 (0.33 / 0.25 / 0.61) | v1 |
| 4 | 0.000, no files | 0.310 (0.50 / 0.39 / 0.03), no HTML | v2 |
| **Median** | **0.652** (0.69 / 1.00 / 0.08) | **0.596** (0.61 / 0.68 / 0.64) | v2 2 · v1 1 · tie 1 |
| Mean | 0.559 | 0.609 | |

Cost (median): calls 82 / 83.5; wall 1,597 s / 1,801 s; prompt tokens 2.30 M / 2.26 M.

### Failure classification

- **v1**: no report in 3/4 runs. Rep 3 died at the output limit (`IncompleteReply`); rep 4 wrote nothing
  (10 identical repeated calls); rep 2 wrote only `findings.json`. Key actor correct whenever findings exist.
- **v2**: no run died at the output limit (length retries 2/6/0/2, all recovered). Rep 3 named the company
  **C07** as key actor (reasoning error) and used free-text roles. Rep 4 had the right actor but wrote
  `key_actor` as a sentence and free-text roles, so the findings contract failed (B 0.39). Rep 4 wrote no HTML.
- Repeat guard (#6) fired 13 times in v2 rep 2 (status events); identical-call counts in the raw logs are
  attempts, not context copies.

## Decision

**Inconclusive overall; a clear trade-off.** v2 is more reliable at delivering (HTML 3/4 vs 1/4, no output-limit
deaths, C median 0.64 vs 0.08) and cheaper on short recovery tasks; v1 is more reliable on the findings contract
and key-actor identification (B median 1.00 vs 0.68).

Risk to check next: pre-change v2 followed the findings contract in 2/2 runs; current v2 broke it in 2/4.
[推論] #1's "generate derived files from structured data with a script" may push the model to invent its own
schema. Next experiment: STR ×4 with v2 minus #1 only (single-variable ablation), and a contract check
(`findings.json` keys/types) added to the verification guidance if #1 stays.
