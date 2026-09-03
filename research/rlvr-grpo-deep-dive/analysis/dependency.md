# Analysis: Dependency Structure in Verifiable Reward RL

Why the components of RLVR and GRPO depend strictly on each other.

```text
       ┌──────────────────────────────────────────────┐
       │   Deterministic Program Verifiers            │
       │   (Compilers, test suites, formal provers)   │
       └──────────────────────┬───────────────────────┘
                              │ Supplies binary, ungameable ground truth
                              ▼
       ┌──────────────────────────────────────────────┐
       │   Parallel Group Rollouts (G >= 4)           │
       │   (Sampling diverse reasoning hypotheses)    │
       └──────────────────────┬───────────────────────┘
                              │ Provides variance for empirical baseline
                              ▼
       ┌──────────────────────────────────────────────┐
       │   Group Relative Advantage (A_i)             │
       │   (Normalizes rewards across the group)      │
       └──────────────────────┬───────────────────────┘
                              │ Eliminates the Value Network (Critic)
                              ▼
       ┌──────────────────────────────────────────────┐
       │   Token-Level Clipped Surrogate Optimization │
       │   (Bounded updates with KL regularization)   │
       └──────────────────────────────────────────────┘
```

## Failure When Any Link Is Severed:
1. **If Verifiers are replaced with Learned Reward Models (RLHF):** The model quickly discovers length and formatting vulnerabilities, producing verbose fluff that scores high on the reward model but fails to solve the underlying code or math problem.
2. **If Group Size $G$ is too small ($G < 4$):** Advantage estimation has extreme sample variance. If $G=2$ and one rollout passes by luck, the gradient update overfits aggressively.
3. **If KL Penalty $\beta$ is 0:** The model undergoes policy collapse: it repeats single successful token sequences endlessly, destroying general natural language fluency.
