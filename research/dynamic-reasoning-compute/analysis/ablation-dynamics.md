# Analysis: Ablation Dynamics in Dynamic Reasoning Compute

Quantitative relationships governing the interactive simulator for test-time compute.

## 1. Problem Complexity Tiers

| Complexity Tier | Example Task | Baseline Pass@1 (Greedy, 256 tokens) | Ceiling with 32K Thinking Tokens |
|---|---|:---:|:---:|
| **Tier 1: Elementary** | Basic formatting, arithmetic, simple syntax | 92% | 94% (Negligible gain, high waste) |
| **Tier 2: Medium** | LeetCode Medium, standard SQL, logic puzzles | 58% | 84% (+26% gain) |
| **Tier 3: Hard** | AIME Olympiad Math, complex algorithmic proof | 18% | 68% (+50% major gain) |
| **Tier 4: Frontier** | Multi-file SWE repository bug fix | 8% | 52% (+44% gain via backtracking) |

## 2. Search Strategy Scaling Curves

### Sequential Extended CoT
- **Latency:** $\mathcal{O}(T)$ (Linear wall-clock time; tokens generated autoregressively one by one).
- **Cost:** $\$0.003 \times (T / 1000)$ at standard frontier output pricing.
- **Scaling Behavior:** Accuracy exhibits logarithmic-sigmoidal scaling with budget $T$:
  $$P(\text{Pass}) = P_0 + (P_{\text{max}} - P_0) \cdot \frac{T^\gamma}{T^\gamma + K^\gamma}$$
- **Self-Correction Activation:** Backtracking loops emerge prominently when $T \ge 4096$ tokens.

### Best-of-$N$ with Verifier
- **Latency:** $\mathcal{O}(L)$ (Near constant wall-clock if run on parallel GPU workers).
- **Cost:** Linear in $N$: $\text{Cost} = N \times L \times \text{Price}$.
- **Scaling Behavior:** Exponential decay of failure: $1 - (1 - p)^N$. Satures rapidly if $p=0$ (the model cannot find the solution in any sample).

### Prefix-Level Tree Search (MCTS + PRM)
- **Efficiency:** Highest accuracy per generated token on deep logical puzzles.
- **Bottleneck:** High scheduling complexity and PRM inference overhead.

## 3. The Token Efficiency Index (Deep vs Fluff)
$$\text{Efficiency} = \frac{\text{Tokens spent in state transitions and hypothesis verification}}{\text{Total tokens generated}}$$
- Without length penalties, efficiency drops to 20–30% (verbose conversational padding).
- Under calibrated RLVR (e.g. Meta Muse 1.3 action economy), efficiency exceeds 75%.
