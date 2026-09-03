# Cooked Source: source-002

- Raw file: `data-raw/papers-and-sources.md` (DeepSeek-R1 Distill entry)
- Type: Technical report & model evaluation
- Parser: direct extraction
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Documents the transfer of reasoning traces to small dense models.

---

The DeepSeek-R1 technical report documented a landmark achievement in reasoning distillation: by harvesting approximately 800,000 verified reasoning trajectories from the flagship 671B Mixture-of-Experts teacher, researchers distilled state-of-the-art reasoning capabilities directly into dense open-weight students ranging from 1.5B to 32B parameters (Qwen and LLaMA architectures).

Remarkably, the distilled DeepSeek-R1-Distill-Qwen-32B model achieved a 94.3% score on MATH-500 and 57.2% on AIME 2024, outperforming large proprietary models like OpenAI o1-mini. This proved that reasoning capabilities discovered through expensive RLVR can be packaged into compact supervised synthetic datasets and absorbed by smaller architectures without running large-scale RL from scratch.
