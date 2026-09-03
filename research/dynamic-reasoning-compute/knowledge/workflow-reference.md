# Workflow Reference: Dynamic Compute Search & Backtracking Loop

```text
[Input Problem q + Difficulty Classifier]
                  │
                  ▼
[Token Budget Allocation T in (256, 256000)]
                  │
                  ▼
[Sequential CoT / Tree Search Generation]
├── Emit hypothesis 1 within <think> tags
├── Step Evaluation: Check internal consistency
                  │
                  ▼
[Contradiction / Flaw Detected?]
├── YES ──→ [Emit "Wait, let me rethink that..."]
│               │
│               └── Discard branch & explore hypothesis 2
│
└── NO  ──→ Continue forward deduction
                  │
                  ▼
[Verifier Assertion Check]
├── Pass: Emit solution outside </think> tags
└── Fail: If budget T remains, re-trigger backtracking loop
```

Canonical details: see `../analysis/flow.md` and `../analysis/ablation-dynamics.md`. [source-001, source-003, source-004]
