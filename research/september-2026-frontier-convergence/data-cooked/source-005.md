# Cooked Source: source-005

- Raw file: `data-raw/frontier-models-sept2026.md` and `data-raw/technical-foundations.md`
- Type: Model technical specification and RLVR research literature
- Parser: synthesis
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Kimi K3 2.8T MoE and RLVR reinforcement learning literature.

---

Moonshot AI released Kimi K3 in July 2026 as a 2.8-trillion parameter Mixture-of-Experts (MoE) open-weight model with a 1-million-token context window. It exemplifies the scaling of open-weight models to multi-trillion parameter sparse architectures with fine-grained routing.

Underpinning Kimi K3 and its peer frontier models is the universal adoption of Reinforcement Learning with Verifiable Rewards (RLVR) stabilized by Group Relative Policy Optimization (GRPO). RLVR substitutes learned human reward models with programmatic ground truth (unit tests, compilers, formal theorem provers), enabling automated, self-improving training loops without human labeling bottlenecks.
