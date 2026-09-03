# Mathematical Derivation: Test-Time Scaling Laws & Compute Optimality

## 1. The Total Compute Equation in Modern LLMs

Historically, compute scaling was restricted to pre-training:

$$C_{\text{total}} \approx C_{\text{pre}} = 6 \cdot N \cdot D$$

where $N$ is parameter count and $D$ is dataset token count.

In reasoning models, total compute per solved query involves inference-time FLOPs:

$$C_{\text{infer}}(q) = 2 \cdot N_{\text{active}} \cdot T_{\text{infer}}(q)$$

where $N_{\text{active}}$ is active model parameters per token (e.g. 80B in a 2.4T MoE) and $T_{\text{infer}}(q)$ is the total number of thinking tokens generated during test-time search for query $q$.

---

## 2. Mathematical Formulation of the Three Inference Regimes

Let $q$ be the problem prompt, and let $y^*$ be the correct verified solution.

### Regime A: Sequential Chain-of-Thought with Budget $T$
The model generates a single token sequence $o = (w_1, w_2, \dots, w_T)$ containing reasoning tokens and final answer:

$$P(\text{Success} \mid T) = P(\operatorname{Verifier}(q, o) = 1 \mid |o| \le T)$$

Empirical scaling relationship (Snell et al., 2024):

$$P(\text{Success} \mid T) \approx 1 - \exp\left( - \alpha \cdot \log\left( \frac{T}{T_{\text{min}}} \right)^\gamma \right)$$

where $T_{\text{min}}$ is the minimum deductive distance required for the problem, and $\gamma > 0$ depends on problem difficulty.

### Regime B: Leaf-Level Parallel Sampling (Best-of-$N$)
The model independently samples $N$ rollouts $\{o_1, \dots, o_N\}$, each of length $L \approx T / N$.
An outcome verifier or Process Reward Model selects the candidate $\hat{o}$:

$$P(\text{Success} \mid N) = 1 - (1 - p_{\text{single}})^N$$

where $p_{\text{single}} = P(\operatorname{Verifier}(q, o_i) = 1)$.

- **When it wins:** On problems where finding the solution requires broad divergent exploration (e.g. creative problem reformulation, finding a rare mathematical substitution).
- **When it loses:** When each individual step requires long sequential deduction that cannot be shortened.

### Regime C: Prefix-Level Tree Search (MCTS / Beam Search)
The reasoning process is decomposed into discrete steps $s_1, s_2, \dots, s_K$.
At each step $k$, the policy proposes $B$ candidate continuations $\{s_{k,1}, \dots, s_{k,B}\}$.
A Process Reward Model (PRM) scores intermediate value:

$$V(s_k) = P(\text{Correct} \mid q, s_1, \dots, s_k)$$

Subtrees where $V(s_k) < \tau$ are pruned, and the search backtracks to the parent node.

---

## 3. Compute-Optimal Test-Time Allocation

Given a compute budget $C_{\text{budget}}$ (measured in inference FLOPs or monetary budget $\$$):

$$\max_{\text{strategy} \in \{A, B, C\}, T} P(\text{Success} \mid \text{Difficulty}(q)) \quad \text{s.t.} \quad \operatorname{Cost}(\text{strategy}, T) \le C_{\text{budget}}$$

### The Optimality Boundary:
1. **Low-Difficulty Queries:** $T \le 512$ tokens. Sequential greedy CoT dominates. Best-of-N is wasteful because $p_{\text{single}} \approx 1.0$.
2. **Intermediate Queries (Competition Math / LeetCode):** $T \in [2048, 16384]$ tokens. Dynamic sequential CoT with autonomous backtracking achieves highest accuracy per dollar.
3. **Hard Multi-Branch Queries (Formal Provers / SWE Repository Bug Hunting):** Tree Search or Best-of-N with deterministic sandbox validation dominates single-path decoding.
