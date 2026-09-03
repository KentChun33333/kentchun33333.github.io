# Cooked Source: source-002

- Raw file: `data-raw/papers-and-sources.md` (DeepSeek-R1 technical report)
- Type: Technical report
- Parser: direct extraction
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Demonstrates pure RL with verifiable rewards directly from base pre-trained models.

---

The DeepSeek-R1 research demonstrates that Large Language Models can autonomously develop sophisticated reasoning mechanisms through large-scale Reinforcement Learning with Verifiable Rewards (RLVR) without requiring supervised fine-tuning (SFT) as a prerequisite.

By using rule-based ground-truth verifiers (mathematical equality checkers, unit test compilers) paired with structural format rewards (enforcing `<think>` and `</think>` tags), the model discovered emergent behaviors: self-verification, step backtracking, exploring alternative strategies, and allocating dynamic thinking compute to difficult problems. Because rewards are strictly verifiable by code, the policy cannot game subjective human evaluators.
