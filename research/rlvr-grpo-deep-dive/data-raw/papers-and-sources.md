# Raw Literature & Evidence: Verifiable Reward RL (RLVR) & GRPO

Gathered September 3, 2026.

## 1. DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models
- **Authors:** Zhihong Shao, Peiyi Wang, Qihao Zhu, Runxin Xu, Junxiao Song, Mingchuan Zhang, Y.K. Li, Y. Wu, Daya Guo (2024).
- **Core Contribution:** Introduction of **Group Relative Policy Optimization (GRPO)**.
- **Key Mechanics:**
  - Standard PPO trains two large models simultaneously: the Actor $\pi_\theta$ (policy) and the Critic $V_\phi$ (value model to estimate baseline reward).
  - The Critic model is typically the same size as the Actor, effectively doubling GPU memory consumption and complicating distributed training.
  - GRPO eliminates the Critic model entirely. For each prompt $q$, it samples a group of $G$ outputs $\{o_1, o_2, \dots, o_G\}$ from the old policy $\pi_{\theta_{\text{old}}}$.
  - The baseline reward is replaced by the mean and standard deviation of rewards within the group:
    $$A_i = \frac{r_i - \operatorname{mean}(\{r_1, \dots, r_G\})}{\operatorname{std}(\{r_1, \dots, r_G\})}$$
  - Training efficiency: Reduces training memory by roughly 50% and eliminates value function estimation errors and critic drift.

## 2. DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning
- **Core Findings (DeepSeek-AI, 2025):**
  - Demonstrated that pure large-scale RL using rule-based/verifiable rewards (RLVR) without any prior supervised fine-tuning (SFT) can induce self-evolution of reasoning capabilities (the "Aha moment").
  - The model autonomously learned to allocate longer thinking time, backtrack, self-verify intermediate steps, and correct earlier errors.
  - Two types of verifiable rewards were used:
    1. **Accuracy reward:** Evaluates whether the response is correct (e.g., deterministic math solver, unit test execution).
    2. **Format reward:** Enforces structural compliance (e.g., placing thinking process inside `<think>` and `</think>` tags).

## 3. "Reinforcement Learning with Verifiable Rewards Implicitly Incentivizes Correct Reasoning in Base LLMs"
- **Authors:** Wen et al. (ICLR 2026 / arXiv 2025).
- **Key Contributions:**
  - Investigates whether RLVR merely acts as "search compression" (sampling paths the base model could already generate) or expands the reasoning frontier.
  - Proposes the **CoT-Pass@K** evaluation metric.
  - Finds that RLVR fundamentally reshapes the probability distribution of reasoning trajectories, increasing the probability of structurally valid deductive steps rather than simply repeating memorized templates.

## 4. "Knowledge-to-Verification (K2V): Unlocking RLVR in Knowledge-Intensive Domains"
- **Authors:** Yuan et al. (ICLR 2026).
- **Key Contribution:**
  - Explores extending RLVR beyond pure math and coding into medical, legal, and operational domains.
  - Constructs automated verifier checklists derived from knowledge graphs and structured schema constraints, overcoming the binary reward sparsity problem.

## 5. Algorithmic Comparison: PPO vs. GRPO vs. DPO
| Feature | Proximal Policy Optimization (PPO) | Group Relative Policy Optimization (GRPO) | Direct Preference Optimization (DPO) |
|---|---|---|---|
| **Critic Model** | Yes (Dedicated Value Net) | **None (Critic-Free)** | None (Implicit) |
| **Memory Footprint** | $2\times$ Model Size (Actor + Critic) | **$1\times$ Model Size (Actor only)** | $1\times$ Model Size |
| **Exploration Mode** | On-policy online sampling | **On-policy online group sampling** | Offline static pairs |
| **Reward Mechanism** | Value baseline $V(s)$ | **Group normalization ($A_i$)** | Pairwise preference loss |
| **Suitability for RLVR**| High compute overhead | **Optimal (Cheap, stable, fast)** | Poor (cannot explore multi-step trajectories) |
