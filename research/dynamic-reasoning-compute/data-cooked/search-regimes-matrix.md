# Search Regimes Matrix: Test-Time Compute Strategies Compared

| Dimension | Sequential Extended CoT | Leaf-Level Best-of-$N$ | Prefix-Level Tree Search (MCTS) |
|---|---|---|---|
| **Primary Mechanism** | Single long autoregressive chain with `<think>` tags | $N$ independent parallel full rollouts | Step-by-step branching & PRM node evaluation |
| **Token Budget Range** | 1,000 to 256,000 tokens | $N \times L$ (e.g. $16 \times 4096 = 65\text{K}$) | Variable dynamic beam (10K to 100K tokens) |
| **Verifier Requirement** | Optional (Internal self-checking) | **Mandatory** (Outcome verifier or PRM) | **Mandatory** (Process Reward Model PRM) |
| **Latency Profile** | High sequential latency (unparallelizable) | **Low wall-clock latency** (massively parallel) | High latency & complex scheduler state |
| **Backtracking Capability** | Linguistic ("Wait, let me rethink...") | None (Independent paths) | Structural (Explicit graph node retraction) |
| **Cost Scaling** | Linear with token length | Linear with sample count $N$ | Multiplicative with branching factor $B^D$ |
| **Vulnerability to Fluff** | High (Can generate circular loops) | Low (Early stopping on verification) | Moderate (PRM false positives) |
| **Best Used For** | Mathematical deduction & code drafting | Creative algorithmic search & Olympiad math | Very long complex multi-agent SWE tasks |
