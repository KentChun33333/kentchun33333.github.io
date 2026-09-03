# Analysis: Ablation Dynamics & Simulation Mechanics

Theoretical dynamics governing the interactive ablation simulator for RLVR and GRPO.

## 1. Verifier Fidelity Ablations

| Verifier Type | Accuracy Signal | Reward Noise / Gaming Risk | Mathematical Behavior |
|---|---|---|---|
| **Deterministic Unit Tests / Compilers** | Ground-truth binary ($r \in \{0, 1\}$) | Zero accuracy gaming; minor format hacking | Gradient strictly reinforces verified logic. Pass@1 rises continuously. |
| **Subjective Learned RM (RLHF)** | Proxy score ($\hat{r} \in [-3, +3]$) | Extreme length bias, hedging, sycophancy | Policy exploits reward model blind spots; true pass rate plateaus early. |
| **Noisy Heuristic (RegEx / Keyword)** | Partial matching ($r \in [0, 1]$) | High false-positive rate (~25%) | Gradient pushes policy toward syntax tricks without conceptual validity. |

## 2. Optimization Algorithm Dynamics

### GRPO (Group Relative Policy Optimization)
- **Memory Footprint:** Baseline $1.0\times$ (Actor only).
- **Gradient Variance:** Decreases with $\mathcal{O}(1/\sqrt{G})$.
- **Stability:** High; normalized advantage prevents runaway gradient explosions.
- **Pass@1 vs. Pass@K:** Exponential improvement in Pass@1 as group search discovers verifiable reasoning chains.

### PPO (Proximal Policy Optimization)
- **Memory Footprint:** $1.9\times - 2.1\times$ (Actor + separate Critic network).
- **Gradient Variance:** Susceptible to critic approximation error; when rewards are sparse at the end of a 4000-token trace, value estimation drifts significantly.
- **Throughput:** ~40% slower training throughput per GPU hour due to critic forward/backward passes.

### DPO (Direct Preference Optimization)
- **Memory Footprint:** $1.0\times$.
- **Exploration:** Incapable of online exploration. Only updates on static offline pairs. Cannot discover new multi-step reasoning chains that were not present in the offline dataset.

## 3. The Impact of Group Size $G$

$$\operatorname{Var}(\hat{A}_i) \propto \frac{1}{G}$$

- **$G = 2$:** High gradient variance. If one rollout passes by random chance, it receives maximum advantage ($+1.0$) and updates the policy heavily in an ungrounded direction.
- **$G = 4$:** Minimal acceptable group size for reasoning RL.
- **$G = 8$:** The sweet spot in DeepSeekMath and modern RLVR implementations. Balances sample diversity with generation latency.
- **$G = 16$ to $32$:** High statistical stability; near-optimal advantage estimation, but linear scaling of rollout compute.

## 4. The Thinker vs. Sampler Dynamics (Wen et al., ICLR 2026)
- **Early Iterations (Steps 0–500):** Behave as **search compression**. The model's Pass@64 remains relatively constant while Pass@1 rises to meet it. The model learns to prioritize valid paths it already had in its base pre-trained distribution.
- **Prolonged Iterations (Steps 1000+):** True **cognitive boundary extension**. Both Pass@1 and Pass@64 rise simultaneously above the base model's theoretical ceiling. The policy reorganizes intermediate token probabilities into self-checking structures.
