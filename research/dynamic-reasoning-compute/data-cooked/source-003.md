# Cooked Source: source-003

- Raw file: `data-raw/papers-and-sources.md` (Test-Time Scaling survey)
- Type: Research survey and benchmarking study
- Parser: direct extraction
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Standard taxonomy classifying test-time compute into three operational regimes.

---

This research establishes a taxonomy for inference-time compute scaling in reasoning LLMs, categorizing methods into:
1. **Single-Trajectory Sequential Scaling:** Generating a continuous chain of thought with variable token length budgets (e.g., 8K to 256K tokens).
2. **Leaf-Level Parallel Scaling:** Generating $N$ independent candidate completions and selecting the winning answer via an outcome verifier or majority voting (Best-of-N).
3. **Prefix-Level Tree Scaling:** Using Monte Carlo Tree Search (MCTS) or step-level beam search to evaluate intermediate states using a Process Reward Model (PRM) and prune failing branches.

The study concludes that hybrid strategies—combining sequential self-correction with selective tree branching—yield the highest accuracy-to-compute ratio on multi-step reasoning benchmarks.
