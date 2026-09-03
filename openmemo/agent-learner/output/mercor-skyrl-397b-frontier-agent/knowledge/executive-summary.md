# Executive Summary: 397B Knowledge Work RL Training

## Headline Achievements
- **Frontier Post-Training Without SFT**: Successfully trained `Qwen3.5-397B-A17B` and `Qwen3.6-35B-A3B` on public SkyRL without supervised fine-tuning warmup. (Source: source-001)
- **Top Benchmark Performance**:
  - `Qwen3.6-35B-A3B-Mercor` surpassed Claude Opus 4.5 on the 480-task APEX-Agents benchmark.
  - `Qwen3.5-397B-A17B-Mercor` achieved a **+70% relative increase** in Pass@1 (16.11% -> 27.29%), led by substantial gains in management consulting. (Source: source-001)

## Key Technical Takeaways

1. **Harness Hygiene is High-ROI**:
   - Trace-level debugging and harness fixes (fixing silent tool failures, using `pdfplumber` for multi-column tables, adding a 20% remaining context wrap-up warning) improved the base 35B model mean reward from 22.74% to 28.69% (+5.95 pts) with zero training. (Source: source-001)

2. **TITO (Token-In-Token-Out) is Mandatory**:
   - Exchanging raw token IDs via `/completions` prevents string re-tokenization misalignment across multi-turn trajectories, keeping async RL on-policy. (Source: source-001)

3. **Prompt-Mean Loss Outperforms Token-Mean**:
   - Normalizing policy loss per prompt group (`prompt_mean`) yields **+3.9 points** over standard `token_mean`, preventing 128k long trajectories from hijacking the gradient. (Source: source-001)

4. **Broad Cross-Harness & Cross-Task Generalization**:
   - Weights trained on an MCP harness transferred effectively to code-only tool environments (`OpenCode`) and `Terminal-Bench 2.1`, while preserving foundational reasoning on `HLE` and `GPQA`. (Source: source-001)
