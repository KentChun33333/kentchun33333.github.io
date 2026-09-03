# Cooked Source: source-002

- Raw file: `data-raw/papers-and-sources.md` (Layer-wise token revision entry)
- Type: Academic research paper
- Parser: direct extraction
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Published in 2026. Investigates internal layer representations during extended reasoning.

---

The 2026 paper "Think Deep, Not Just Long" addresses the phenomenon of token inflation in reasoning models. It demonstrates that total token length is an imperfect proxy for true reasoning effort, as models often generate thousands of repetitive, redundant tokens without changing their internal hypotheses.

By measuring the angular displacement of token prediction distributions across transformer layers (from early layers to deep layers), the authors identify "deep-thinking tokens"—tokens where the internal representations undergo major revisions and error corrections. The study shows that compute efficiency can be improved by pruning superficial conversational tokens while preserving genuine hypothesis-testing tokens.
