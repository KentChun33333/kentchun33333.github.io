# Raw Literature & Evidence: Dynamic Reasoning Compute Budgets

Gathered September 3, 2026.

## 1. "Scaling LLM Test-Time Compute Optimally Can be More Effective Than Scaling Model Parameters"
- **Authors:** Charlie Snell, Jaehoon Lee, Kelvin Xu, Aviral Kumar (UC Berkeley / Google DeepMind).
- **Core Thesis:**
  - Standard scaling laws focused exclusively on pre-training compute ($C_{\text{pre}} \propto N^\alpha D^\beta$).
  - Snell et al. demonstrate an inference-time scaling law: given a fixed pre-trained model, investing additional test-time FLOPs via search can equal or surpass a model with $14\times$ larger parameter count.
  - The optimal inference strategy depends strictly on problem difficulty:
    - On easy problems: standard greedy decoding or small chain-of-thought is compute-optimal.
    - On hard problems: tree search with intermediate process verifiers or dense sampling dominates single-pass decoding.

## 2. "Think Deep, Not Just Long: Layer-Wise Token Revision in Reasoning LLMs"
- **Key Findings (2026 Literature):**
  - Distinguishes "deep-thinking tokens" from superficial "token inflation".
  - Deep-thinking tokens are identified by tracking how hidden representation vectors change across transformer layers $L_1 \to L_{N}$.
  - In genuine reasoning steps, later layers significantly modify the token prediction distribution (hypothesis revision).
  - In superficial padding (token inflation), layers $L_5$ through $L_{80}$ have near-zero gradient displacement, merely outputting conversational connective tissue ("Furthermore, let us consider another aspect...").

## 3. "Test-Time Scaling in Reasoning LLMs: A Formal Taxonomy" (2025–2026 Survey)
- **Categorizes Test-Time Compute into Three Regimes:**
  1. **Single-Trajectory Sequential Scaling (CoT):** Increasing the max generation budget $T$ per prompt (e.g. 16K, 64K, 128K, or 256K in Qwen3.8-Max). The model self-manages search sequentially via natural language tokens.
  2. **Leaf-Level Parallel Sampling (Best-of-N):** Sampling $N$ complete independent rollouts from the policy and selecting the best using an outcome verifier or Process Reward Model (PRM).
  3. **Prefix-Level Tree Search (MCTS / Beam Search):** Branching at step boundaries within the chain of thought, scoring partial steps with a PRM, and backtracking from low-scoring nodes.

## 4. Autonomous Backtracking and the "Aha Moment" (DeepSeek-R1 & QwQ)
- **Observed Phenomenon:**
  - In RLVR post-trained models, when given a token budget $T > 8192$, the model develops autonomous backtracking without external prompting:
    - *Example Trace Snippet:* "...therefore the determinant must be 0. Wait, that contradicts the non-singular condition given in the problem statement. Let me re-evaluate step 2. If we instead expand along row 3..."
  - This capability emerges naturally because the RLVR reward signal penalizes incorrect final answers; models that backtrack and correct errors achieve higher expected reward than those that forge ahead with broken hypotheses.

## 5. Frontier 2026 Model Budgets
- **Google Gemini 3.8 Flash:** Adaptive thinking budget (dynamically scales from 0 to 64K tokens based on prompt complexity).
- **Alibaba Qwen3.8-Max-0902:** Expanded thinking budget up to 256,000 chain-of-thought tokens for repository-level software development and formal math proofs.
- **Meta Muse Spark 1.3:** Focuses on "action economy"—curbing redundant thinking tokens to reduce inference latency by 25%.
