# Analysis: The 5-Stage Synthetic Distillation Flywheel Flow

How frontier labs continuously upgrade fast workhorse models from massive teachers.

```text
[STAGE 1: PROBLEM SEEDING & DIVERSIFICATION]
├── Curate 500K+ diverse seed tasks across code, math, and workflows
├── Seed mixture: 80% synthetic problem expansions + 20% real-world anchor tasks
               │
               ▼
[STAGE 2: TEACHER MASS ROLLOUT GENERATION]
├── Massive 2.4T–2.8T MoE teacher model (e.g. Qwen3.8-Max, Kimi K3)
├── Generates K=8 rollouts per problem with high exploratory temperature
├── Trajectories include full internal <think> scratchpads and solution patches
               │
               ▼
[STAGE 3: DETERMINISTIC VERIFIER REJECTION SAMPLING]
├── Programmatic sandbox executes unit tests, compilers, or symbolic checkers
├── Binary filter: discard all failing or syntactically invalid rollouts (r=0)
├── Success filtering rate: typically 15% to 40% of generated rollouts pass
               │
               ▼
[STAGE 4: TOKEN DE-NOISING & FLUFF PRUNING]
├── Automated cleaner removes conversational chatter and circular repetition loops
├── Preserves core mathematical state changes and hypothesis backtracking tokens
├── Result: high-density reasoning dataset (30–45% token compression)
               │
               ▼
[STAGE 5: STUDENT SFT & TARGETED RLVR FINE-TUNING]
├── Compact student model (e.g. 7B, 14B, or Gemini Flash) trained via Sequence KD
├── Student absorbs teacher's verified reasoning patterns via cross-entropy loss
└── Followed by lightweight student-level RLVR to reinforce fast inference execution
```

## Key Architectural Insights
1. **The Human Bottleneck is Eliminated:** In stages 2, 3, and 4, zero human labeling is required. A cluster can generate, verify, and clean 1 million multi-step reasoning traces in under 48 hours.
2. **Deterministic Grounding Prevents Model Collapse:** Because stage 3 rejects unverified traces with 100% rigor, the student never trains on hallucinated or incorrect deductions, breaking the "Curse of Recursion".
