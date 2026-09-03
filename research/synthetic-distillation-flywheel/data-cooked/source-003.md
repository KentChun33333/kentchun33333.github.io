# Cooked Source: source-003

- Raw file: `data-raw/papers-and-sources.md` (Nature 2024 paper entry)
- Type: Academic research paper
- Parser: direct extraction
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Published in Nature (2024). Mathematically models degradation in recursive synthetic training.

---

Shumailov et al. (Nature, 2024) demonstrated that when generative models are trained recursively on synthetic data produced by previous generations without external grounding, they suffer from "Model Collapse."

The process begins with early collapse, where the model loses statistical variance in the tails of the data distribution (forgetting rare words, specialized grammatical constructs, and uncommon factual knowledge). In late collapse, the model's outputs degenerate into homogeneous repetitive babble. The collapse is mathematically inevitable when finite ungrounded samples are fed back into training, establishing the necessity of external anchors to maintain distribution fidelity.
