# Cooked Source: source-004

- Raw file: `data-raw/papers-and-sources.md` (Autonomous Backtracking technical reports)
- Type: Empirical analysis and technical synthesis
- Parser: direct extraction
- Parsed at: 2026-09-03
- Confidence: high
- Notes: Investigates the emergence of self-correction loops in reasoning models like DeepSeek-R1 and QwQ.

---

Technical reports analyzing large-scale RLVR models (e.g. DeepSeek-R1, QwQ) document the spontaneous emergence of the "Aha moment"—where a model detects a flaw in its reasoning and actively backtracks.

Without any explicit few-shot demonstrations of error correction, models trained under binary outcome verifiers autonomously learn markers such as *"Wait, let me rethink that..."* or *"This creates a contradiction; let's try an alternative path."* Because the RL reward is binary on the final answer, trajectories that detect and discard flawed hypotheses before committing to a final answer receive reinforcement, whereas stubborn trajectories fail and get penalized.
