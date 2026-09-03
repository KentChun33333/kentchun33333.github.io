# Workflow Reference: The 5-Stage Synthetic Distillation Flywheel

```text
[Stage 1: Seed Prompts + Real-World Anchor (15-30%)]
                        │
                        ▼
[Stage 2: Massive Teacher Rollout Generation]
├── 2.4T–2.8T MoE generates K=8 candidate reasoning traces
└── Emits deep chain-of-thought within <think> tags
                        │
                        ▼
[Stage 3: Deterministic Programmatic Sandbox Filter]
├── Unit tests, compilers, symbolic checkers evaluate output
├── Failing rollouts (r=0) are rejected (Rejection Sampling)
└── Hallucinations and invalid proofs discarded
                        │
                        ▼
[Stage 4: Token De-Noising & Fluff Pruning]
├── Strip conversational filler and circular hesitations
└── Compress token footprint by 35%
                        │
                        ▼
[Stage 5: Compact Student SFT & Targeted RLVR]
├── Sequence-level cross-entropy + soft-target KL distillation
└── Lightweight student RLVR locks in fast execution (Gemini Flash)
```

Canonical details: see `../analysis/flow.md` and `../analysis/ablation-dynamics.md`. [source-001, source-002, source-004, source-005]
