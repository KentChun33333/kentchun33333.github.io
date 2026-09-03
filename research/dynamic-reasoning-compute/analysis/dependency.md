# Analysis: Dependency Structure in Dynamic Reasoning Compute

The causal web linking token budgets, verifiers, search algorithms, and financial cost.

```text
       ┌──────────────────────────────────────────────┐
       │   Task Complexity Profile                    │
       │   (Algorithmic depth vs. factual retrieval)  │
       └──────────────────────┬───────────────────────┘
                              │ Dictates required search regime
                              ▼
       ┌──────────────────────────────────────────────┐
       │   Thinking Token Budget Allocation (T)       │
       │   (256 tokens to 256,000 tokens)             │
       └──────────────────────┬───────────────────────┘
                              │ Bounds exploration depth and branch count
                              ▼
       ┌──────────────────────────────────────────────┐
       │   Search Mechanism (CoT vs Best-of-N vs PRM) │
       │   (Sequential revision vs parallel voting)   │
       └──────────────────────┬───────────────────────┘
                              │ Converts token budget into candidate paths
                              ▼
       ┌──────────────────────────────────────────────┐
       │   Outcome & Process Verifiers                │
       │   (Selects valid terminal trajectory)        │
       └──────────────────────────────────────────────┘
```

## Critical Dependencies:
1. **Best-of-N Fails Without a Reliable Verifier:** Sampling 64 answers is completely useless unless you have an automated checker (or majority vote) that can reliably distinguish the 1 correct answer from 63 plausible hallucinations.
2. **Sequential CoT Depends on Context Window Capacity:** Extending thinking budgets to 64K–256K tokens requires extreme KV cache optimization and linear attention or multi-head latent attention (MLA) to prevent quadratic memory blow-ups.
3. **Tree Search Depends on Process Reward Model (PRM) Calibration:** If the PRM gives a false high score to a broken early step, the tree search expends its entire token budget exploring an invalid subtree.
