# Cooked Source: source-001

- Raw file: `data-raw/papers-and-sources.md` (Snell et al. paper entry)
- Type: Academic research paper
- Parser: direct extraction
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Foundational work on test-time scaling laws by Snell et al. (UC Berkeley & Google DeepMind).

---

Snell et al. demonstrate that scaling test-time compute can be significantly more effective than scaling model parameters. Across benchmark tasks including GSM8k, MATH, and coding problems, trading test-time FLOPs for accuracy allows a smaller base model to outperform an un-searched model with over $14\times$ more parameters.

The paper establishes that compute optimality is governed by task difficulty: allocating fixed compute across multiple parallel rollouts vs. extended sequential chain of thought depends directly on the model's base probability of generating a correct step. On challenging problems, search with intermediate verifiers provides super-linear scaling against raw parameter scaling.
