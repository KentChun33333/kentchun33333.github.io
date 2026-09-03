# Workflow Reference: The 5-Stage Frontier Convergence

```text
[Input State: Code Repo + Shell + 1M Context]
                    │
                    ▼
[Stage 1: Sparse MoE Parameter Expansion]
├── 2.4T (Qwen3.8-Max) to 2.8T (Kimi K3) total capacity
└── Fine-grained routing activates <90B parameters per token
                    │
                    ▼
[Stage 2: Environment Harness Sandbox Grounding]
├── Live execution in bash, terminal, and git environments
└── Action economy: 20% fewer tool calls, 25% fewer tokens (Meta Muse Spark 1.3)
                    │
                    ▼
[Stage 3: Verifiable Reward Reinforcement Learning (RLVR)]
├── Programmatic ground-truth verifiers (compilers, test suites, provers)
└── Stable optimization via Group Relative Policy Optimization (GRPO)
                    │
                    ▼
[Stage 4: Test-Time Search & Dynamic Compute Allocation]
├── Up to 256K thinking tokens (Qwen3.8-Max 0902)
└── Self-evaluation, internal checkpoint verification, and backtracking
                    │
                    ▼
[Stage 5: High-Speed Synthetic Distillation Flywheel]
├── Rapid distillation into high-speed workhorse models
└── 3-week release cadence (Google Gemini 3.8 Flash)
```

Canonical details: see `../analysis/flow.md` and `../analysis/breakthrough-assessment.md`. [source-001, source-002, source-003, source-004, source-005]
