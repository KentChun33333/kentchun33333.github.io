# Big Picture: Verifiable Reward RL (RLVR) & GRPO

## Executive Summary
Reinforcement Learning with Verifiable Rewards (RLVR) powered by Group Relative Policy Optimization (GRPO) represents the primary algorithmic catalyst behind the sudden capability surge of 2025–2026 reasoning models.

Unlike early reinforcement learning from human feedback (RLHF)—which relied on subjective, learned neural reward models that frequently hallucinated and favored verbose sycophancy—RLVR enforces objective, programmatic ground truth through compilers, unit test runners, symbolic solvers, and formal verification engines.

GRPO completely eliminates the memory-heavy, unstable Critic/Value network of classical PPO. By sampling a group of $G$ rollouts per prompt and normalizing advantages across the group ($A_i = (r_i - \mu)/\sigma$), GRPO cuts training VRAM in half and provides mathematically stable policy gradient updates over reasoning chains spanning thousands of tokens.

## Sourced Key Findings
1. **Critic Elimination:** Standard PPO doubles model memory; GRPO requires only the Actor policy, enabling training trillion-parameter MoE reasoning models on standard cluster footprints. [source-001]
2. **Autonomous Reasoning Emergence:** Pure RLVR without supervised fine-tuning prompts models to self-discover internal thinking tags, step backtracking, and dynamic compute allocation. [source-002]
3. **Beyond Search Compression:** While early RLVR acts as search compression, prolonged training expands actual deductive reasoning boundaries (Wen et al., ICLR 2026). [source-003]
4. **Generalization Beyond Code:** Frameworks like K2V adapt verifiable reward checklists to knowledge domains, preventing reward sparsity. [source-004]
5. **Zero-Sum Gradient Dynamics:** Prompts where all samples pass or all fail emit zero gradient, concentrating optimization entirely on the model's active learning frontier. [source-005]
6. **Non-Differentiable Sandbox Autograd Bridge:** PyTorch never differentiates the external compiler or sandbox; the policy gradient score function trick ($\nabla_\theta \log \pi_\theta(o) \cdot A_i$) treats sandbox verification as a detached scalar multiplier on differentiable token log-probabilities. [source-001, source-005]

