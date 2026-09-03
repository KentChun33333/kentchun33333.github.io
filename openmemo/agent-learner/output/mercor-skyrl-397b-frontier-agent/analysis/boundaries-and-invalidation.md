# Boundaries, Invalidation & Evidence Map

## 1. Evidence Map & Boundary Tags

| Claim / Mechanism | Status | Evidence Basis | Source IDs |
|---|:---:|---|---|
| Zero-SFT RL Post-Training at 397B Scale | `IMPLEMENTED` | Qwen3.5-397B-A17B Pass@1 improved from 16.11% to 27.29% on APEX-Agents. | source-001 |
| Prompt Mean Loss Superiority | `IMPLEMENTED` | Prompt-mean aggregation beat token-mean baseline by +3.9 points on 480 held-out tasks. | source-001 |
| Context Wrap-up Nudge Efficacy | `IMPLEMENTED` | 20% remaining context budget prompt warning added +3.0 points pure training-time gain. | source-001 |
| Cross-Harness Generalizability | `IMPLEMENTED` | Archipelago-trained weights transferred to code-only OpenCode harness and Terminal-Bench 2.1. | source-001 |
| DPPO Shorter Turn Induction | `IMPLEMENTED` | DPPO increased turns (21 -> 32) while reducing tokens/turn (834 -> 588) compared to GLM-5. | source-001 |
| Overlong Filtering Ineffectiveness | `RECOMMENDATION` | OLF degraded performance by -1.5 points; not recommended without context compaction. | source-001 |
| Data-First Frontier Scaling | `INFERENCE` | Post-training data gains (+10-12 pts) exceeded algorithm knob gains (+3.9 pts). | source-001 |

## 2. Invalidation Tests

- **Prompt Mean Invalidation**: The advantage of `prompt_mean` over `token_mean` weakens if all task trajectories in a dataset have near-identical token lengths (variance -> 0).
- **TITO Invalidation**: TITO necessity weakens in single-turn completion tasks where tokenization boundaries never span multiple prompt-response turns.
- **De-Risking Invalidation**: The 32-task overfitting check is invalidated if the selected 32 tasks have zero offline reward variance or trivial binary solutions.
- **Cross-Harness Transfer Invalidation**: Transfer from MCP to code harness fails if the agent model has never been pre-trained on code execution tools.
