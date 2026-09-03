# Workflow Reference: GRPO Training Loop

```text
[Prompt Batch q ~ P(Q)]
          │
          ▼
[Policy pi_theta_old generates G distinct rollouts]
├── Candidate o_1: Chain of thought + solution
├── Candidate o_2: Chain of thought + solution
└── Candidate o_G: Chain of thought + solution
          │
          ▼
[Deterministic Verifier Sandbox]
├── Compiler / Unit Test Runner evaluates each o_i
└── Raw Rewards r = [r_1, r_2, ..., r_G] in {0.0, 1.0}
          │
          ▼
[Intra-Group Advantage Normalization]
├── mu = mean(r), sigma = std(r)
└── A_i = (r_i - mu) / (sigma + eps)
          │
          ▼
[Clipped Surrogate Policy Loss + KL Penalty]
├── Token-level importance sampling ratio rho_t
├── Clipped objective min(rho_t * A_i, clip(...) * A_i)
└── - beta * D_KL(pi_theta || pi_ref)
          │
          ▼
[Parameter Update via AdamW]
└── Policy weights theta updated; Zero Critic VRAM used
```

Canonical details: see `../analysis/flow.md` and `../analysis/ablation-dynamics.md`. [source-001, source-002, source-005]
