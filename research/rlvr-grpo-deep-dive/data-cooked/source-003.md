# Cooked Source: source-003

- Raw file: `data-raw/papers-and-sources.md` (Wen et al., ICLR 2026)
- Type: Academic research paper
- Parser: direct extraction
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Evaluates whether RLVR extends cognitive boundaries or merely compresses search. Introduces CoT-Pass@K.

---

Wen et al. (ICLR 2026) address the central theoretical controversy surrounding RLVR: does verifiable reward reinforcement learning produce fundamentally new reasoning capabilities, or does it merely act as "search compression" (optimizing the model to sample solutions it was already capable of generating)?

The paper introduces the CoT-Pass@K metric to measure reasoning coverage across sample budgets. Their findings show that while early training behaves largely as search compression, prolonged RLVR training restructures the underlying token transition probabilities, enabling the model to navigate multi-step deductive chains that had near-zero probability in the base model. This provides empirical evidence that RLVR can expand actual reasoning boundaries when backed by deterministic verifiers.
