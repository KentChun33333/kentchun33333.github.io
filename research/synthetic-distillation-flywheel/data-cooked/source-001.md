# Cooked Source: source-001

- Raw file: `data-raw/papers-and-sources.md` (Kim & Rush paper entry)
- Type: Academic research paper
- Parser: direct extraction
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Foundational work on sequence-level knowledge distillation (Seq-KD).

---

Kim & Rush (2016) introduced Sequence-Level Knowledge Distillation (Seq-KD) to address the limitations of word-level knowledge distillation in auto-regressive generation. Rather than minimizing the cross-entropy over the vocabulary distribution at every token position, Seq-KD has the teacher model generate complete sequences from its own output distribution.

The student model is then trained via standard maximum likelihood estimation directly on the teacher's sampled sequences. This approach transfers the global sequence-level probability distribution of the teacher to the student while avoiding the massive memory overhead of storing dense soft probability tensors across multi-thousand token contexts.
