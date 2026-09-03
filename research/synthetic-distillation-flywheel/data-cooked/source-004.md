# Cooked Source: source-004

- Raw file: `data-raw/papers-and-sources.md` (Verifier-Grounded Distillation literature)
- Type: Technical survey & engineering analysis
- Parser: direct extraction
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Documents the engineering mechanisms that prevent model collapse in reasoning models.

---

Recent engineering analyses of 2025–2026 distillation pipelines reveal how frontier AI labs avoid model collapse when training on synthetic reasoning:
1. **Deterministic Verifier Anchors:** Unlike creative writing or open-ended dialogue, reasoning tasks can be validated objectively by unit tests, compilers, and formal provers. Rejecting unverified traces prevents error accumulation and distribution drift.
2. **Token Fluff Pruning:** Teachers often produce redundant conversational padding ("Let me think about this step carefully..."). De-noising pipelines prune superficial tokens while preserving deductive state transitions, boosting student parameter efficiency by up to 35%.
3. **Anchor Human Mix:** Maintaining a 10–30% mixture of curated real-world human prompts ensures lexical and semantic entropy does not degrade across recursive generations.
