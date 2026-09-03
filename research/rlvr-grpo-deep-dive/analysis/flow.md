# Analysis: GRPO Training Iteration Pipeline Flow

How a single training step operates in Group Relative Policy Optimization with Verifiable Rewards.

```text
[STEP 1: QUERY BATCH SAMPLING]
├── Sample batch of reasoning prompts q ~ P(Q) (math problems, coding specs, test harnesses)
               │
               ▼
[STEP 2: PARALLEL GROUP ROLLOUT GENERATION]
├── Policy pi_theta_old generates G distinct candidate trajectories per prompt
├── Output group: {o_1, o_2, ..., o_G} (includes chain-of-thought and final answer)
               │
               ▼
[STEP 3: DETERMINISTIC PROGRAMMATIC VERIFICATION]
├── Each rollout o_i is evaluated by automated ground-truth checkers
├── Code sandbox: executes unit tests (pass=1.0, fail=0.0)
├── Math solver: formal verification / exact symbolic match (pass=1.0, fail=0.0)
├── Structural format check: enforces <think> tags (penalty if malformed)
├── Raw reward array: [r_1, r_2, ..., r_G]
               │
               ▼
[STEP 4: INTRA-GROUP RELATIVE ADVANTAGE ESTIMATION]
├── Compute group empirical mean: mu = mean(r_1, ..., r_G)
├── Compute group empirical standard deviation: sigma = std(r_1, ..., r_G)
├── Normalize each trajectory: A_i = (r_i - mu) / (sigma + eps)
├── (Note: No Value Network or Critic model is ever called)
               │
               ▼
[STEP 5: CLIPPED SURROGATE LOSS COMPUTATION]
├── Compute token-level probability ratio: rho_t = pi_theta(o_t | .) / pi_old(o_t | .)
├── Compute clipped objective: min(rho_t * A_i, clip(rho_t, 1-eps, 1+eps) * A_i)
├── Subtract KL penalty: - beta * D_KL(pi_theta || pi_ref)
               │
               ▼
[STEP 6: BACKPROPAGATION & PARAMETER UPDATE]
├── Accumulate gradients across group G and query batch
└── Update policy parameters theta via AdamW optimizer
```

## Critical Architectural Properties

1. **Critic-Free Simplicity:** In step 4, the advantage $A_i$ is computed purely from scalar statistics of the group. No auxiliary value gradients, no value loss $\mathcal{L}_V$, and zero critic parameters stored in GPU memory.
2. **Zero Gradient on Homogeneous Groups:** If all $G$ candidates pass ($r_i = 1$) or all fail ($r_i = 0$), $\sigma = 0$ (or below $\epsilon$). In practice, $A_i = 0$. The prompt contributes zero gradient, naturally filtering out trivial problems and completely impossible problems, focusing compute exclusively on the model's **learning frontier**.
3. **Exploration Incentive:** The model is rewarded not for generating average answers, but for discovering trajectories that outperform other samples in the same group.
4. **Non-Differentiable Sandbox to Autograd Bridge:** PyTorch never differentiates the sandbox code or test execution. Advantage $A_i$ is treated as a detached scalar constant multiplying the log-probabilities $\nabla_\theta \log \pi_\theta(o)$. The model learns by increasing the probability of successful tokens ($A_i > 0$) and decreasing the probability of failed tokens ($A_i < 0$), allowing arbitrary black-box compilers, shells, and test runners to guide gradient descent.

