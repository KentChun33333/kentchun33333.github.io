# Mathematical Derivation: Group Relative Policy Optimization (GRPO)

## 1. Classical PPO Objective and the Critic Bottleneck

In Proximal Policy Optimization (PPO), the objective maximizes:

$$\mathcal{J}_{\text{PPO}}(\theta) = \hat{\mathbb{E}}_t \left[ \min\left( r_t(\theta) \hat{A}_t, \operatorname{clip}(r_t(\theta), 1-\epsilon, 1+\epsilon) \hat{A}_t \right) \right]$$

where $r_t(\theta) = \frac{\pi_\theta(a_t | s_t)}{\pi_{\theta_{\text{old}}}(a_t | s_t)}$, and the advantage $\hat{A}_t$ is estimated using Generalized Advantage Estimation (GAE):

$$\hat{A}_t^{\text{GAE}} = \sum_{l=0}^\infty (\gamma \lambda)^l \delta_{t+l}^V, \quad \text{with } \delta_t^V = r_t + \gamma V_\phi(s_{t+1}) - V_\phi(s_t)$$

### The Problem in LLM Scaling
1. **Memory Overhead:** $V_\phi(s)$ requires an entire value model initialized from the pre-trained LLM. For a 70B policy, running an additional 70B value model requires dedicated GPU memory for weights, activations, and optimizer states, practically doubling the infrastructure footprint.
2. **Value Drift:** Training a value network on sparse rewards is notoriously noisy and unstable. If the critic misestimates the baseline value of a reasoning step, it injects high-variance error into the policy gradient.

---

## 2. The GRPO Formulation: Critic-Free Relative Advantage

GRPO (Shao et al., 2024) removes the value network $V_\phi$ by replacing temporal difference baselines with **intra-prompt group normalization**.

### Step 1: Group Sampling
For each query $q \sim \mathcal{P}(Q)$, the policy generates a group of $G$ distinct candidate completions:

$$\{o_1, o_2, \dots, o_G\} \sim \pi_{\theta_{\text{old}}}(O \mid q)$$

### Step 2: Deterministic Verification / Reward Scoring
Each completion $o_i$ is evaluated by the verifier function:

$$r_i = \operatorname{Verifier}(q, o_i) \in \mathbb{R}$$

In RLVR:
- $r_i = 1.0$ if all unit tests / formal math checks pass;
- $r_i = 0.0$ if any test fails or syntax errors occur;
- Optional format penalty: $r_i \leftarrow r_i - \lambda_{\text{fmt}}$ if tags are missing.

### Step 3: Normalized Group Advantage
The baseline is defined as the empirical mean of the group, and the scale is normalized by standard deviation:

$$\mu_q = \frac{1}{G} \sum_{i=1}^G r_i, \qquad \sigma_q = \sqrt{\frac{1}{G} \sum_{i=1}^G (r_i - \mu_q)^2 + \epsilon_{\text{num}}}$$

The relative advantage of candidate $o_i$ is:

$$A_i = \frac{r_i - \mu_q}{\sigma_q}$$

### Key Mathematical Properties of $A_i$:
- **Zero-Sum Centering:** $\sum_{i=1}^G A_i = 0$. Exactly half the rollouts (or those scoring above average) receive positive advantage, while below-average rollouts receive negative advantage.
- **Scale Invariance:** Because $A_i$ is normalized by $\sigma_q$, the policy gradient is invariant to linear shifts in the reward function:
  $$\operatorname{Adv}(\alpha r_i + \beta) = A_i \quad (\forall \alpha > 0, \beta \in \mathbb{R})$$
- **Variance Control via Group Size $G$:** As $G \to \infty$, $\mu_q$ converges to the true expected value $\mathbb{E}[R \mid q]$, and $\sigma_q$ converges to the true policy variance. In practice, $G \in [8, 16]$ yields near-optimal gradient stability with minimal computational waste.

---

## 3. The Full GRPO Surrogate Objective

The surrogate policy loss optimized by gradient ascent is:

$$\mathcal{J}_{\text{GRPO}}(\theta) = \mathbb{E}_{q \sim \mathcal{P}(Q), \{o_i\}_{i=1}^G \sim \pi_{\theta_{\text{old}}}} \left[ \frac{1}{G} \sum_{i=1}^G \frac{1}{|o_i|} \sum_{t=1}^{|o_i|} \left( \min\left( \rho_{i,t}(\theta) A_i, \operatorname{clip}(\rho_{i,t}(\theta), 1-\epsilon, 1+\epsilon) A_i \right) - \beta \mathbb{D}_{\text{KL}}(\pi_\theta \parallel \pi_{\text{ref}}) \right) \right]$$

where:
- $\rho_{i,t}(\theta) = \frac{\pi_\theta(o_{i,t} \mid q, o_{i,<t})}{\pi_{\theta_{\text{old}}}(o_{i,t} \mid q, o_{i,<t})}$ is the per-token importance sampling ratio.
- $\epsilon \in [0.1, 0.2]$ is the PPO-style clipping boundary.
- $\mathbb{D}_{\text{KL}}(\pi_\theta \parallel \pi_{\text{ref}})$ is the token-level Kullback-Leibler divergence penalty against a frozen reference policy $\pi_{\text{ref}}$, approximated as:

$$\mathbb{D}_{\text{KL}}(\pi_\theta \parallel \pi_{\text{ref}}) = \frac{\pi_{\text{ref}}(o_{i,t} \mid \cdot)}{\pi_\theta(o_{i,t} \mid \cdot)} - \log\frac{\pi_{\text{ref}}(o_{i,t} \mid \cdot)}{\pi_\theta(o_{i,t} \mid \cdot)} - 1$$

This penalty prevents the policy from collapsing into repetitive mode degeneration or ungrammatical exploit sequences.

---

## 4. How Non-Differentiable Sandbox Evaluations Enable Backpropagation

A common point of confusion in modern RLVR is: **how can a non-differentiable external evaluator (such as `pytest` exit codes, a gcc compiler, or a formal Z3 SMT solver) be backpropagated to update neural network weights $\theta$?**

### The Core Principle: Do NOT Differentiate the Reward

In standard supervised learning, the loss function itself must be differentiable:

$$\nabla_\theta \mathcal{L}_{\text{SFT}} = \nabla_\theta \left( -\log \pi_\theta(y^* \mid x) \right)$$

If an external reward function $R(o)$ were inside the standard chain rule, backpropagation would require $\frac{\partial R}{\partial o}$, which is non-existent for discrete compilers or terminal processes (`exit 0` vs `exit 1`).

### The Policy Gradient Theorem (Score Function Trick)

The optimization objective maximizes expected reward under the model's own sampling distribution:

$$\mathcal{J}(\theta) = \mathbb{E}_{o \sim \pi_\theta} [ R(o) ] = \sum_o \pi_\theta(o) R(o)$$

Taking the gradient with respect to policy parameters $\theta$:

$$\nabla_\theta \mathcal{J}(\theta) = \nabla_\theta \sum_o \pi_\theta(o) R(o) = \sum_o \nabla_\theta \pi_\theta(o) \cdot R(o)$$

Multiply and divide by $\pi_\theta(o)$:

$$\nabla_\theta \mathcal{J}(\theta) = \sum_o \pi_\theta(o) \left( \frac{\nabla_\theta \pi_\theta(o)}{\pi_\theta(o)} \right) R(o) = \sum_o \pi_\theta(o) \nabla_\theta \log \pi_\theta(o) \cdot R(o)$$

Converting back to an expectation:

$$\nabla_\theta \mathcal{J}(\theta) = \mathbb{E}_{o \sim \pi_\theta} \left[ \underbrace{\nabla_\theta \log \pi_\theta(o)}_{\text{100% Differentiable in PyTorch}} \cdot \underbrace{R(o)}_{\text{Detached External Scalar Constant}} \right]$$

### In GRPO:

1. The external sandbox executes the candidate rollout outside the computation graph (e.g., Python `subprocess.run(["pytest"])`) and outputs raw scalar $r_i \in \{0, 1\}$.
2. The advantage $A_i = \frac{r_i - \mu_G}{\sigma_G}$ is computed and passed to PyTorch as a **detached scalar weight** (`tensor.detach()`).
3. PyTorch only evaluates and differentiates the probability of the tokens that the model emitted:

$$\nabla_\theta \mathcal{L}_{\text{GRPO}} = - \frac{1}{G} \sum_{i=1}^G \sum_{t=1}^{|o_i|} \nabla_\theta \log \pi_\theta(o_{i,t} \mid \cdot) \cdot A_i$$

- If $A_i > 0$ (sandbox tests passed): The gradient step **increases** the probability of those exact tokens.
- If $A_i < 0$ (sandbox tests failed): The gradient step **decreases** the probability of those tokens.

This likelihood ratio serves as the universal mathematical adapter bridging arbitrary, black-box, non-differentiable real-world execution environments with gradient descent.

