# Big Picture Reference: Frontier Knowledge Work RL Post-Training

## 1. Purpose & Context
Training frontier agents for professional knowledge work (management consulting, corporate law, investment banking) requires operating across long-horizon environments with simulated companies, complex spreadsheets, multi-column PDFs, email/chat systems, and tool harnesses. (Source: source-001)

Post-training open-weight models (`Qwen3.6-35B-A3B` and `Qwen3.5-397B-A17B`) using Reinforcement Learning (RL) on public SkyRL without SFT warmup yields state-of-the-art results:
- **35B Model**: Surpassed Claude Opus 4.5 on the 480-task APEX-Agents benchmark.
- **397B Model**: Improved Pass@1 from 16.11% to 27.29% (+70% relative gain). (Source: source-001)

## 2. Core Architectural Principles

1. **Infrastructure De-Risking Precedes Algorithm Spending**:
   - Steps 1–3 (environment hardening, harness optimization, TITO token tracking, and 32-task overfitting checks) prevent burning thousands of GPU hours on corrupted or off-policy trajectories.
   - Harness bug fixes alone improved base model mean reward from 22.74% to 28.69% (+5.95 pts) with zero training. (Source: source-001)

2. **Equal Group Aggregation (`prompt_mean`)**:
   - In long-horizon agent RL where trajectories vary from 2k to 128k tokens, standard `token_mean` loss lets abnormally long trajectories dominate gradients.
   - `prompt_mean` normalizes loss equally across prompt groups, yielding a **+3.9 point** performance boost. (Source: source-001)

3. **Loss Formulation Without Extra Forward Passes**:
   - Utilizing DPPO or GLM-5 loss directly consumes rollout logprobs, eliminating the traditional Token-Level Importance Sampling (TIS) forward pass and significantly accelerating training on 100k+ token rollouts. (Source: source-001)

4. **Reusable Cross-Harness Generalization**:
   - Models trained in MCP-centric environments (`Archipelago`) successfully transfer capability to code-only tool environments (`OpenCode`) and standard software benchmarks (`Terminal-Bench 2.1`), while preserving core reasoning benchmarks (`HLE`, `GPQA`). (Source: source-001)

## 3. System Boundaries & Constraints
- **Staleness Bound**: Fully-async training bound by `(max_staleness_steps + 1) * mini_batch_size * n_samples_per_prompt` (1024 trajectories).
- **KV-Cache Limit**: Rollout concurrency bounded at 300 (for 397B) to prevent GPU memory thrashing. (Source: source-001)
