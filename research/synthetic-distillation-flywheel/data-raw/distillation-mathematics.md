# Mathematical Derivation: Sequence-Level Knowledge Distillation & Collapse Prevention

## 1. Classical Word-Level vs. Sequence-Level Distillation

In classical word-level distillation (Hinton et al., 2015), the student minimizes the cross-entropy of vocabulary logits at each token position:

$$\mathcal{L}_{\text{word}}(\theta) = - \sum_{t=1}^T \sum_{w \in \mathcal{V}} P_{\text{teacher}}(w \mid y_{<t}, x) \log P_\theta(w \mid y_{<t}, x)$$

### The Limitation for Large Language Models:
- Computing full-vocabulary soft probability distributions $P_{\text{teacher}}(w \mid \cdot) \in \mathbb{R}^{|\mathcal{V}|}$ across $|\mathcal{V}| \ge 150,000$ tokens for multi-thousand token reasoning chains creates extreme I/O and storage bottlenecks (hundreds of terabytes of dense float tensors).

### Sequence-Level Knowledge Distillation (Seq-KD, Kim & Rush 2016)
Instead of storing dense probability vectors, the teacher generates complete reasoning sequences via beam search or high-temperature sampling:

$$y_{\text{teacher}} \sim \pi_{\text{teacher}}(Y \mid x)$$

The student is trained using standard autoregressive cross-entropy on the teacher-generated tokens:

$$\mathcal{L}_{\text{Seq-KD}}(\theta) = - \sum_{t=1}^{|y_{\text{teacher}}|} \log \pi_\theta(y_{\text{teacher}, t} \mid y_{\text{teacher}, <t}, x)$$

---

## 2. Rejection-Sampled Distillation (RSD) with Verifiable Rewards

In pure Seq-KD, if the teacher hallucinates or introduces an arithmetic error, the student faithfully memorizes the flawed deduction.

In **Rejection-Sampled Distillation (RSD)**, the teacher generates a set of $K$ candidate reasoning traces $\{o_1, \dots, o_K\} \sim \pi_{\text{teacher}}(O \mid q)$ for query $q$.

Each trajectory is passed to a deterministic ground-truth verifier:

$$\mathbb{I}_{\text{valid}}(o_k) = \begin{cases} 1 & \text{if } \operatorname{Verifier}(q, o_k) = 1 \ (\text{tests pass}) \\ 0 & \text{otherwise} \end{cases}$$

The distillation objective optimizes only over verified solutions:

$$\mathcal{L}_{\text{RSD}}(\theta) = - \mathbb{E}_{q \sim \mathcal{D}, \{o_k\}_{k=1}^K \sim \pi_{\text{teacher}}} \left[ \frac{\sum_{k=1}^K \mathbb{I}_{\text{valid}}(o_k) \cdot \sum_{t=1}^{|o_k|} \log \pi_\theta(o_{k,t} \mid q, o_{k,<t})}{\sum_{k=1}^K \mathbb{I}_{\text{valid}}(o_k) + \epsilon} \right]$$

---

## 3. Mathematical Mechanism of Model Collapse & Verifier Entropy Anchoring

### The Shumailov et al. (Nature 2024) Collapse Equation
Let $p_0(x)$ be the true human data distribution. At generation $n$, the model $\pi_n$ is trained on synthetic data sampled from $\pi_{n-1}$:

$$X_n \sim \pi_{n-1}, \quad \pi_n = \arg\min_\pi \mathcal{L}(X_n; \pi)$$

Under unconstrained maximum likelihood estimation, the variance of the estimated distribution shrinks monotonically:

$$\operatorname{Var}(\pi_n) = \left( 1 - \frac{1}{M} \right) \operatorname{Var}(\pi_{n-1}) \implies \lim_{n \to \infty} \operatorname{Var}(\pi_n) = 0$$

where $M$ is the sample size. The model collapses because low-probability tail modes are repeatedly sampled with zero frequency, causing irreversible information loss.

### How Verifiers Prevent Collapse
When programmatic verification is introduced, the synthetic distribution is conditioned on the indicator function:

$$\tilde{\pi}_{n-1}(x) = \frac{\pi_{n-1}(x) \cdot \mathbb{I}(\operatorname{Verifier}(x) = 1)}{Z}$$

Because $\operatorname{Verifier}(x) = 1$ requires solving the formal constraints of the task:
1. It truncates degenerate modes (e.g. repetitive babble or empty syntax) where $\operatorname{Verifier}(x) = 0$.
2. It guarantees that the support of $\tilde{\pi}_n$ remains within the valid functional subspace $\mathcal{X}_{\text{valid}} = \{x \mid \operatorname{Verifier}(x) = 1\}$.
3. By mixing a fraction $\alpha \in [0.1, 0.3]$ of diverse real-world task prompts, the flywheel maintains vocabulary diversity while expanding deductive capacity.
