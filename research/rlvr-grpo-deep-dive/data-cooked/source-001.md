# Cooked Source: source-001

- Raw file: `data-raw/papers-and-sources.md` (DeepSeekMath paper entry)
- Type: Academic research paper
- Parser: direct extraction
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Origin paper of Group Relative Policy Optimization (GRPO) by Shao et al. (2024).

---

DeepSeekMath introduces Group Relative Policy Optimization (GRPO) to address the severe computational overhead of Proximal Policy Optimization (PPO) in language models. Standard PPO maintains an Actor model $\pi_\theta$ and an equally sized Critic model $V_\phi$. GRPO completely discards the Critic model.

Instead of estimating state values with a neural network, GRPO samples a group of $G$ outputs $\{o_1, \dots, o_G\}$ for each query $q$. The baseline is computed directly from the group reward statistics:

$$A_i = \frac{r_i - \operatorname{mean}(\{r_1, \dots, r_G\})}{\operatorname{std}(\{r_1, \dots, r_G\})}$$

This eliminates the memory and compute required for a separate Value model, reducing GPU training memory requirements by approximately 50% while stabilizing the advantage calculation against critic drift.
