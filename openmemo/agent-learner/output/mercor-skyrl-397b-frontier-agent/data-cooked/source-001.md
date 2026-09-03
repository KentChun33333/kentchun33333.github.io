# Cooked Source: source-001

- Raw file: `data-raw/mercor_blog.md`
- Type: MD
- Parser: markdown-normalization
- Parsed at: 2026-09-02
- Confidence: high
- Notes: Complete extraction of Mercor & SkyRL technical post-training guide for Qwen3.5-397B-A17B and Qwen3.6-35B-A3B.

---

## 1. Executive Summary & Key Results
- **Core Achievement**: Reinforcement Learning (RL) post-training on public SkyRL without SFT warmup.
- **Model Gains**:
  - `Qwen3.6-35B-A3B-Mercor`: Surpassed Claude Opus 4.5 on APEX-Agents benchmark (480 tasks). Mean reward improved from 22.74% to 28.69% through harness fixes, and further through RL.
  - `Qwen3.5-397B-A17B-Mercor`: Pass@1 increased from 16.11% to 27.29% (+70% relative improvement) on held-out APEX-Agents. Highest gains in management consulting.
- **Data Basis**: 1,928 expert-created tasks (corporate law, investment banking, management consulting). Contamination-free (disjoint worlds/prompts from held-out benchmark).
- **Harness & Benchmark Transfer**:
  - Training on MCP harness (`Archipelago`) transfers to code-only tool harness (`OpenCode`).
  - Transfers to `Terminal-Bench 2.1` via `Terminus-2`.
  - Zero regression on non-agentic reasoning benchmarks (`HLE` and `GPQA`).

---

## 2. Six-Step Post-Training Lifecycle

### Step 1: Environment, Harness, and Token Accounting (TITO)
- **Infrastructure Topology**:
  - **Data/Rollout**: Harbor framework (container management across Modal sandboxes).
  - **Compute Split**: Ray GPU cluster runs SkyRL async trainer + vLLM inference engines + `ArchipelagoAgent` (BaseAgent subclass).
  - **Environment Sandboxes**: Modal container booted from ECR `image.tar` with full world filesystem + MCP servers (Docs, PDF, Email, Chat) + in-sandbox verifiers.
- **Engineering Lessons**:
  - Timeouts on all network calls, MCP tools, and container teardowns.
  - LLM-judge rate limiting: round-robin API keys with exponential backoff at 800+ concurrent rollouts.
  - Process isolation: isolate MCP clients per Ray task/process to eliminate disconnect bottlenecks.
  - Harness optimizations (PowerPoint None-return fix, PDF `pdfplumber` nudge, wrap-up prompts, tool error retry) raised base 35B from 22.74% to 28.69% without training (+5.95 pts).
- **TITO (Token-In-Token-Out)**:
  - Avoid string re-tokenization between inference and trainer.
  - Implemented via `/completions` raw token ID exchange in `agents/tito.py`.

### Step 2: RL Systems Tuning
- **Megatron Optimizations**: Parallelism sweep (TP/EP/PP/CP), CPU-offloading, dynamic micro-batching (`max_tokens_per_microbatch`).
- **Cluster Node Ratio (Inference : Train)**:
  - 35B model: 4 inference nodes : 2 train nodes.
  - 397B model: 12 inference nodes : 8 train nodes.
  - Goal: Trainer wait buffer (`timing/wait_for_generation_buffer`) equals 0.
- **Rollout Concurrency Ceilings**:
  - *Systems Ceiling*: KV cache capacity / average trajectory length (2k–128k tokens).
  - *Algorithmic Ceiling*: Staleness tolerance = `(max_staleness_steps + 1) * mini_batch_size * n_samples_per_prompt` = `(3 + 1) * 16 * 16 = 1024`.
  - Configured concurrency: 550 for 35B; 300 for 397B.
- **Logprob Diff Sanity Check**: Mean logprob difference between trainer and inference engine kept < 0.03.

### Step 3: Overfitting Sanity Run
- 32-task subset with non-zero reward variance. Batch size 32, 8 samples per prompt, synchronous training (1 step = 1 epoch).
- Discovered that file-diff grading required high-fidelity 3rd-party diffing tools to prevent false zeroes.

### Step 4: Algorithm Ablations on 35B (3-pass held-out 480 tasks)
1. **Token Aggregation**:
   - `prompt_mean` (DAPO/ScaleRL style: equal weight per prompt group) beats `token_mean` (standard global pool) by **+3.9 points**. Prevents 128k-token rollouts from dominating gradients.
2. **Policy Loss (DPPO vs GLM-5 Loss)**:
   - Both use rollout logprobs directly in loss, avoiding separate forward passes (TIS) on 100k+ token trajectories.
   - Scores are tied at Epoch 1, but DPPO shifts behavior toward more, shorter turns (21 -> 32 turns; 834 -> 588 assistant tokens/turn).
3. **Context Nudge**:
   - Warning at 20% remaining context budget yields **+3.0 points** pure training-time gain by preventing context blowouts.
4. **Negative / Neutral Ablations**:
   - Overlong Filtering (OLF): -1.5 points loss.
   - Adaptive Length Penalty (ALP): neutral to negative across all settings.

### Step 5: 397B Hero Run
- Recipe: DPPO + `prompt_mean` + context nudge (no length penalty, no curriculum).
- Results: Pass@1 increased from 16.11% to 27.29% (+70% relative).

### Step 6: Evaluation and Generalization
- **Cross-Harness Transfer**: Transferred to code-only `OpenCode` harness (no MCP servers). 35B model increased code execution tool calls from ~15% to ~60%, while 397B preserved MCP preference.
- **Cross-Benchmark Transfer**: Tested on `Terminal-Bench 2.1` via `Terminus-2`. Improved across both models.
- **Capability Preservation**: `HLE` and `GPQA` evaluations showed zero degradation.
