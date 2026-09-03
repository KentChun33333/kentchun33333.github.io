# Cooked Source: source-005

- Raw file: `data-raw/papers-and-sources.md` (Frontier 2026 releases)
- Type: Model specifications and release notes
- Parser: direct extraction
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Documents actual thinking token budgets across September 2026 releases.

---

Frontier September 2026 releases reflect diverse strategies for inference-time compute:
- **Alibaba Qwen3.8-Max-0902:** Implements a massive thinking budget of up to 256,000 chain-of-thought tokens, specifically targeted at repository-level software development and formal mathematics.
- **Google Gemini 3.8 Flash:** Features an adaptive thinking scheduler that automatically modulates the token budget from 0 (instant response) to 64K tokens depending on prompt complexity.
- **Meta Muse Spark 1.3:** Prioritizes "action economy," using 25% fewer tokens and 20% fewer tool calls to accomplish tasks without redundant exploratory chatter.
