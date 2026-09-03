# Flow Analysis — 397B Knowledge Work RL Training

## 1. Executive Summary
The end-to-end training pipeline transforms expert domain task definitions into high-performing frontier knowledge work agent checkpoints via a 6-stage lifecycle prioritizing infrastructure de-risking, async rollout scheduling, token accounting, and loss aggregation. (Source: source-001)

## 2. Sequence of Stages

| Step # | Stage Name | Actor / Component | Inputs | Outputs | Source IDs |
|---|---|---|---|---|---|
| 001 | Environment & Sandbox Setup | Harbor + Modal + ECR | Task Dirs, World `image.tar` | Running Container Sandboxes + MCP Endpoints | source-001 |
| 002 | Agent Rollout & TITO Tracking | ArchipelagoAgent + vLLM | Task Prompt, MCP Tools | Raw Trajectory Token IDs & Responses | source-001 |
| 003 | In-Sandbox Verification | Harbor Verifier | Agent Artifacts, Ground Truth | Reward Signal & Traces | source-001 |
| 004 | Async Weight Sync & Training | SkyRL + Megatron Backend | Trajectories + Rollout Logprobs | In-Flight Updated Policy Weights | source-001 |
| 005 | De-Risking & Overfitting Check | Synchronous Trainer | 32-Task Non-Zero Variance Subset | Learnability Proof & Diff Calibration | source-001 |
| 006 | Generalization & Cross-Eval | OpenCode / Terminus Harnesses | Checkpoint Weights, APEX / Terminal-Bench | Validated Frontier Agent Artifacts | source-001 |

## 3. Decision Logic & Gates
- **De-Risking Gate 1 (Non-Model Error Rate)**: Drive infrastructure/timeout errors near 0 at 300–600 concurrency before RL. (Source: source-001)
- **De-Risking Gate 2 (Train-Inference Logprob Mismatch)**: Assert `mean(logprob_trainer - logprob_vLLM) < 0.03`. (Source: source-001)
- **De-Risking Gate 3 (Overfitting Run)**: If the 32-task sanity subset does not exhibit fast reward convergence within a few synchronous steps, abort and audit reward extraction. (Source: source-001)
- **Loss Aggregation Policy**: Use `prompt_mean` over `token_mean` to prevent 128k long-trajectory dominance. (Source: source-001)

## 4. Failure Modes & Edge Cases
- **Context Blowout**: Long multi-turn agent rollouts exhaust context limit. Mitigated via 20% context warning nudge (+3.0 pts). (Source: source-001)
- **MCP Client Bottlenecks**: Shared Python processes cause socket disconnects under heavy concurrency. Mitigated by per-process Ray task isolation. (Source: source-001)
- **Off-Policy Drift**: Re-tokenizing string text outputs causes misalignment in multi-turn RL. Mitigated via raw token ID exchange (TITO). (Source: source-001)
