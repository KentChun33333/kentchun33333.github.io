# Analysis: Dynamic Compute Allocation & Search Flow

How modern reasoning architectures dynamically adapt test-time compute to problem difficulty.

```text
[STEP 1: QUERY INGESTION & DIFFICULTY PROFILING]
├── Ingest user problem q
├── Fast classifier / router estimates task complexity tier:
│   ├── Tier 1 (Easy / Conversational): Allocate 0–512 tokens
│   ├── Tier 2 (Standard Code / Math): Allocate 2K–8K tokens
│   └── Tier 3 (Olympiad / SWE Bug): Allocate 16K–256K tokens
               │
               ▼
[STEP 2: TEST-TIME SEARCH STRATEGY SELECTION]
├── Strategy A: Sequential CoT (Deep thinking tokens, linear stream)
├── Strategy B: Best-of-N Parallel Sampling (Outcome Verifier selection)
└── Strategy C: Prefix-Level Tree Search (Step-level PRM scoring & pruning)
               │
               ▼
[STEP 3: AUTONOMOUS DEDUCTION & BACKTRACKING]
├── Generation unfolds within <think> tags
├── Step verification: Model checks internal consistency
├── Detection of contradiction triggers linguistic backtracking:
│   └── "Wait, this assumption leads to a negative value. Let's restart from step 2."
               │
               ▼
[STEP 4: INTERMEDIATE NODE PRUNING (If Tree Search)]
├── PRM scores intermediate steps: V(s_t) = P(Correct | s_1...s_t)
├── Prune branches below threshold tau
└── Allocate remaining token budget to high-scoring candidates
               │
               ▼
[STEP 5: TERMINATION & OUTCOME VERIFICATION]
├── Solution finalized or max token budget T exhausted
├── Sandbox execution / test runner asserts correctness
└── Output answer extracted outside </think> tags
```

## Architectural Insights

1. **The Cost of Over-Thinking on Easy Queries:** Generating 10,000 tokens of circular reasoning on a simple request like "What is 15% of 80?" wastes latency and money while increasing the risk of hallucination. Dynamic routing is essential.
2. **Backtracking is Emergent, Not Hardcoded:** The model does not execute an external Python `rewind()` function. Because of RLVR, the transformer weights learn to emit natural language tokens that negate previous claims and explore alternate branches within the same context window.
