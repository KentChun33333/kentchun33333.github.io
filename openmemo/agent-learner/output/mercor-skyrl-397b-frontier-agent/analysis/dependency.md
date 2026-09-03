# Dependency Analysis — Mercor 397B SkyRL Training

## 1. System & Entity Relationships

- **External Services & Infrastructure**:
  - **Modal**: On-demand sandbox provider spinning up containerized customer worlds from ECR images. (Source: source-001)
  - **AWS ECR**: Registry hosting container images containing simulated company filesystems and MCP servers. (Source: source-001)
  - **LLM Judge APIs**: Evaluation judges for open-ended professional tasks (requires multi-key round-robin to prevent 429 throttling). (Source: source-001)

- **Compute & Framework Stack**:
  - **Ray Cluster**: Distributed execution mesh separating GPU rollout workers and GPU trainer nodes. (Source: source-001)
  - **vLLM**: Inference generation engine exchanging raw token IDs with agents. (Source: source-001)
  - **Megatron-LM**: Training backend executing parallel forward/backward passes (TP/PP/EP/CP). (Source: source-001)
  - **SkyRL**: Fully asynchronous RL loop orchestrating in-flight NCCL weight synchronization. (Source: source-001)
  - **Harbor**: Task packaging standard and trial lifecycle manager (`BaseAgent`, `Trial`). (Source: source-001)

## 2. Critical Path Analysis

- **Critical Path**: Task Ingestion → Modal Sandbox Boot → MCP Tool Loop Rollout → Verifier Score → Trajectory Stream → Megatron Loss Step → In-Flight NCCL Weight Broadcast.
- **Single Point of Failure (SPOF)**:
  - **KV-Cache Exhaustion**: If trajectory lengths blow up without CPU offloading or dynamic microbatching, vLLM blocks, stalling the trainer. (Source: source-001)
  - **Harness Quirks**: Ineffective tools (e.g. garbled PDF tables or silent None returns) teach models to avoid tools entirely instead of learning the domain task. (Source: source-001)
