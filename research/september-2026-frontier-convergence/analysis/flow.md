# Analysis: The 2026 Frontier Model Capability Pipeline Flow

How frontier labs shifted from the 2023–2024 "pretraining brute-force" paradigm to the 2025–2026 "agentic verifier & test-time search" paradigm.

```text
[STAGE 1: MASSIVE SPARSE MoE PRETRAINING]
├── 2.4T to 2.8T total parameters (e.g. Qwen3.8-Max, Kimi K3)
├── Fine-grained routing: 64–256 micro-experts, sub-100B active per token
└── Multi-Token Prediction (MTP) heads for fast forward decoding
               │
               ▼
[STAGE 2: ENVIRONMENT-HARNESS POST-TRAINING]
├── Transition from passive next-token to interactive execution
├── Models placed in live sandbox harnesses (Bash, Python, Git, Terminal-Bench)
└── Learning tool ergonomics: minimal calls, compact outputs (Meta Muse Spark 1.3)
               │
               ▼
[STAGE 3: VERIFIABLE REWARD REINFORCEMENT LEARNING (RLVR)]
├── Replacement of subjective RLHF with deterministic ground-truth checkers
├── Test suites, compilers, theorem provers, terminal exit codes
└── Stable gradient updates via Group Relative Policy Optimization (GRPO)
               │
               ▼
[STAGE 4: TEST-TIME COMPUTE & DYNAMIC REASONING SEARCH]
├── Allocating inference tokens to solution exploration (256K CoT budget)
├── Self-correction and backtracking on failed verification checkpoints
└── "Search compression": pruning unproductive cognitive branches
               │
               ▼
[STAGE 5: CLOSED-LOOP SYNTHETIC DISTILLATION FLYWHEEL]
├── Teacher models generate millions of verified reasoning trajectories
├── Deterministic filters discard 100% of invalid solutions
└── Rapid distillation into high-speed workhorse models (e.g. Gemini 3.8 Flash)
```

## Stage Descriptions

1. **Stage 1 — Sparse MoE Scaling:** Parameter capacity expanded by an order of magnitude (from ~70B–400B to 2.4T–2.8T), yet inference cost remained flat because each token routes to only a tiny subset of experts. This provides vast world knowledge and domain specialization without destroying inference latency.
2. **Stage 2 — Environment-Harness Training:** Models are no longer trained on static prose; they interact with real shells, file systems, and API boundaries. This directly explains why benchmark scores like DeepSWE and Terminal-Bench jumped across every lab.
3. **Stage 3 — RLVR (Verifiable Rewards):** By removing the noisy, easily hacked subjective reward models of early RLHF and replacing them with binary ground truth (did the test pass? did the code compile?), reinforcement learning scaled reliably without sycophancy or degeneration.
4. **Stage 4 — Test-Time Search:** Models were given permission to spend tokens thinking. Just as human chess players compute deeper in difficult positions, models now dynamically expand compute on complex codebases and scientific proofs.
5. **Stage 5 — The Distillation Flywheel:** The reason smaller models like Gemini 3.8 Flash can improve dramatically in just 3 weeks is that distillation from verified synthetic reasoning data takes days, whereas training foundation models from scratch takes months.
