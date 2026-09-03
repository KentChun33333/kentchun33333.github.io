# Training frontier knowledge work agents: A 397B RL training guide with SkyRL

Source: https://www.mercor.com/blog/training-frontier-knowledge-work-agents-a-397b-rl-training-guide-with-skyrl/
Published: 2026-09-01
Authors: Charlie Ruan, Sumanth Hegde, Eric Tang, Tyler Griggs, Jungyeon Park, Maanas Baraya, Philipp Moritz, Michael Haines, Edward J. Hu, Mercor Research & SkyRL Teams.
Repo: https://github.com/Mercor-Intelligence/ApexAgents-SkyRL-Recipe
Weights & Traces: https://huggingface.co/collections/mercor/apexagents-skyrl-recipe

## Abstract / Summary
A step-by-step account of post-training Qwen3.5-397B-A17B and Qwen3.6-35B-A3B using Reinforcement Learning (RL) on SkyRL without SFT warmup.
Evaluated on APEX-Agents (480 held-out tasks in corporate law, investment banking, management consulting).
Qwen3.6-35B-A3B surpassed Claude Opus 4.5. Qwen3.5-397B-A17B improved Pass@1 by 70% relative (16.11% -> 27.29%).

## 6-Step Methodology:
- Step 1: Environment, harness, and token accounting (Harbor + Modal ECR sandboxes, Ray GPU cluster, TITO exact token-in-token-out accounting, trace debugging).
- Step 2: RL systems tuning (Megatron TP/EP/PP/CP, dynamic micro-batching, inference:train node split 12:8 for 397B, rollout concurrency KV cache vs staleness ceilings, train-inference logprob mismatch < 0.03).
- Step 3: The overfitting run (32-task sanity check, verifying file-diff grading).
- Step 4: Algorithm ablations on 35B:
  - Token aggregation: `prompt_mean` beats `token_mean` by +3.9 pts.
  - Policy loss: DPPO vs GLM-5 loss (both avoid TIS forward passes; DPPO induces more deliberate shorter turns).
  - Context nudge (+3.0 pts pure training effect when warning at 20% budget).
  - Negative/neutral: Overlong filtering (OLF -1.5 pts) and Adaptive Length Penalty (ALP).
- Step 5: 397B Hero Run (DPPO + prompt_mean + context nudge).
- Step 6: Evaluation & Generalization (Transfers across harnesses: Archipelago -> OpenCode, transfers across benchmarks: Terminal-Bench 2.1 via Terminus, no regression on HLE / GPQA).
