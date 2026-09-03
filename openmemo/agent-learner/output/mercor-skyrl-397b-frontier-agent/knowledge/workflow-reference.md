# Workflow Reference Guide: 397B Knowledge Work RL Training

For high-level system context and model specifications, see [knowledge/big-picture.md](big-picture.md).

## 1. Stacking Flow Diagram

```text
[Input Data Contract]                 [Core Module]                      [Output Data Contract]
=====================                 =============                      ======================
Task Dirs & ECR image.tar  -->   Harbor & Modal Provisioning    -->   Isolated Sandbox with MCP Endpoints
                                                                      (Source: source-001)

Prompts & MCP Tools        -->   ArchipelagoAgent (TITO / vLLM) -->   Multi-Turn Trajectory Token IDs
                                                                      (Source: source-001)

Trajectory Artifacts       -->   In-Sandbox Task Verifiers      -->   Scalar Rewards & Rollout Logprobs
                                                                      (Source: source-001)

Rollouts (Prompt-Mean)     -->   SkyRL Trainer (Megatron-LM)    -->   In-Flight NCCL Synced Checkpoints
                                                                      (Source: source-001)
```

## 2. The 6-Step Implementation Playbook

### Stage 1: De-Risking the Environment & Harness
1. **Infrastructure Hardening**: Put explicit timeouts on every download, tool invocation, and container teardown.
2. **Process Isolation**: Run each agent loop as an isolated Ray task rather than sharing a single Python process across hundreds of agent loops.
3. **Trace-Driven Harness Fixes**: Inspect raw traces to eliminate silent harness bugs before RL:
   - Fix tools returning `None` on success.
   - Nudge PDF extraction to structured tools (`pdfplumber`) to avoid garbling multi-column tables.
   - Inject a 20% remaining context wrap-up warning (+3.0 pts).
4. **TITO (Token-In-Token-Out)**: Bypass text re-tokenization by exchanging raw token IDs directly via `/completions`. (Source: source-001)

### Stage 2: Systems Tuning (Inference vs. Training)
1. **Parallelism & Microbatching**: Sweep Megatron TP/EP/PP/CP and apply dynamic micro-batching (`max_tokens_per_microbatch`).
2. **Node Ratios**: Allocate 12 inference nodes to 8 training nodes for 397B models to ensure the trainer generation buffer wait time stays at 0.
3. **Concurrency Bounds**: Bound rollout concurrency by the lower of the systems KV-cache limit (300 concurrent rollouts for 397B) and the algorithmic staleness ceiling.
4. **Logprob Parity**: Verify mean logprob difference between trainer and vLLM is < 0.03. (Source: source-001)

### Stage 3: Sanity Overfitting Run
- Execute a 32-task synchronous test run (batch size 32, 8 samples/prompt).
- Confirm rapid reward signal convergence before deploying full GPU clusters. (Source: source-001)

### Stage 4 & 5: Algorithm Recipe Selection & Hero Run
- **Loss Aggregation**: Use `prompt_mean` (equal weight per prompt group) over `token_mean` (+3.9 pts).
- **Policy Loss**: Use DPPO or GLM-5 loss to avoid expensive TIS forward passes on 100k+ token sequences.
- **Context Nudge**: Activate 20% context warning.
- **Avoid**: Overlong Filtering (-1.5 pts) and uncalibrated Adaptive Length Penalties. (Source: source-001)

### Stage 6: Cross-Harness & Capability Validation
- Verify generalization on code-only harnesses (`OpenCode`) and independent benchmarks (`Terminal-Bench 2.1`).
- Ensure no regression on foundational reasoning benchmarks (`HLE`, `GPQA`). (Source: source-001)
