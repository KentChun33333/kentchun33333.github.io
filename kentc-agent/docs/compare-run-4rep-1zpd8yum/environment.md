# Environment

- Comparison: v1 `original` (`src/kentc_agent/`) vs current v2 `topics` (`src/kentc_agent_new_mem/`, with items #1 verify guidance,
  #2 chunked-write retry, #6 identical-repeat guard, #7 search-aware truncation; #3 removed). Both include the budget notice.
- Protocol: `docs/compare.md`, 4 repetitions per suite, sequential, variant order alternated by the harnesses.
- Model: `huihui-v2-swift-qwen3.8-flash-next-iq3_s`, `meta.n_ctx` 62,536, `http://127.0.0.1:8081/v1` (see models-before.json).
- Python/platform: 3.13.5 macOS-27.0.1-arm64-arm-64bit-Mach-O
- Source: 68 files hashed in source-before.json (re-checked after the run).
- Preflight: v2 tests 42 passed; STR self-check empty 0.0 / oracle 1.0 / naive 0.7357.
- Server cache/thermal state: not controlled.
