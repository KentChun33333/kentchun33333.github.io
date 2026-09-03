# Parse plan

| Source | Type | Strategy | Output | Risk |
|---|---|---|---|---|
| source-001 | HTML | Direct article extraction | `data-cooked/source-001.md` | Benchmark plots lack tabular values |
| source-002 | Paper HTML/PDF | Section-aware direct reading | `data-cooked/source-002.md` | Describes original TimesFM, not v3 |
| source-003 | Repo/model card | Documentation inspection | `data-cooked/source-003.md` | Public code may evolve |
| source-004 | Paper | Abstract/method lineage only | `data-cooked/source-004.md` | Do not infer TimesFM-3 adaptation details |
