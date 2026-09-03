# Teacher-Student Matrix: Frontier Distillation Architectures

| Distillation Pipeline | Teacher Model Scale | Student Model Scale | Target Domain | Key Filtering Mechanism | Performance Outcome |
|---|---|---|---|---|---|
| **DeepSeek-R1 Distill** | 671B MoE (37B active) | 1.5B, 7B, 14B, 32B Dense | Competition Math & Code | Binary test suite + math solver verification | 32B student scores 94.3% on MATH-500, outperforming o1-mini. |
| **Google Gemini 3.8 Flash** | Massive Frontier MoE (>1T) | Sub-30B Fast Workhorse | SWE, Cyber, Long-Horizon Agents | Live execution sandboxes + automated test suites | Shipped 3 weeks after 3.7 Flash; locked at $0.75/$3.75 pricing. |
| **Qwen-2.5-Coder Distill** | Qwen-Max / Qwen3.8-Max (2.4T) | 7B & 32B Dense | Repository-Level Code Generation | Multi-file pytest harnesses + syntax linters | 32B student rivals frontier proprietary models on HumanEval & SWE-bench. |
| **Meta Muse Spark 1.3** | Proprietary MSL Teacher | Compact Muse Code Student | Terminal Agent Workflows | Action economy filter (pruning redundant tool calls) | 20% fewer tool calls, 25% fewer tokens on Terminal-Bench 2.1. |
