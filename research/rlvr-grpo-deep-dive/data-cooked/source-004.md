# Cooked Source: source-004

- Raw file: `data-raw/papers-and-sources.md` (Yuan et al., ICLR 2026 K2V)
- Type: Academic research paper
- Parser: direct extraction
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Knowledge-to-Verification framework expanding RLVR beyond code and math into knowledge domains.

---

Yuan et al. (ICLR 2026) introduce Knowledge-to-Verification (K2V) to extend RLVR to open-world, knowledge-intensive domains (e.g., medicine, law, agriculture) where unit tests or compiler executables are absent.

K2V automatically constructs verifiable checklists from structured knowledge graphs and entity relations. Instead of relying on a subjective reward model, candidate answers are parsed into claim-level assertions and matched against the knowledge checklist with deterministic verification logic. This mitigates reward sparsity and brings the stability of RLVR to non-coding domains.
