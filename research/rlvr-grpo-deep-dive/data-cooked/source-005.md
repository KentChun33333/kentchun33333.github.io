# Cooked Source: source-005

- Raw file: `data-raw/papers-and-sources.md` and `data-raw/grpo-mathematical-derivation.md`
- Type: Technical synthesis and comparative study
- Parser: mathematical derivation
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Compares PPO, GRPO, and DPO under the lens of verifiable reward reinforcement learning.

---

In classical PPO, Generalized Advantage Estimation (GAE) depends on a learned critic $V(s)$. Training the critic introduces high variance when rewards are sparse, as the critic struggles to predict whether a 2000-token reasoning trajectory will pass a compiler test at the final token.

GRPO completely bypasses this by estimating advantage from the empirical distribution of $G$ rollouts on the same prompt. By normalizing rewards across the group ($A_i = (r_i - \mu)/\sigma$), GRPO eliminates value network memory costs and grounds policy gradients in direct empirical success rates. When paired with binary programmatic verifiers, GRPO provides unmatched stability and throughput for reasoning model post-training.
