# Raw Data: September 2026 Frontier AI Model Releases

Gathered September 3, 2026.

## 1. Google: Gemini 3.8 Flash & Gemini 3.8 Flash Cyber
- **Release Date:** September 2, 2026 (announced via Google Research & Google DeepMind blog).
- **Positioning:** High-intelligence, cost-efficient "workhorse" model in the Flash tier. Third Flash update in a 6-week cadence (following Gemini 3.7 Flash).
- **Key Enhancements:**
  - Long-horizon software engineering and multi-step autonomous agent execution.
  - Native multi-step reasoning and dynamic reasoning budgets.
  - Cybersecurity variant: **Gemini 3.8 Flash Cyber** tuned for vulnerability detection, automated patching, and secure code transformation under Google's Fairwind Program.
- **Pricing & Availability:**
  - $0.75 / 1M input tokens, $3.75 / 1M output tokens (introductory rate locked through Dec 31, 2026).
  - Deployed in Google AI Pro/Ultra, AI Mode, Google Workspace Sheets, and Google Cloud Vertex AI / Gemini API.

## 2. Meta: Muse Spark 1.3 (Meta Superintelligence Labs - MSL)
- **Release Date:** September 2, 2026.
- **Positioning:** Multimodal reasoning and agentic model from Meta's newly formed Meta Superintelligence Labs (MSL), succeeding Muse Spark 1.2.
- **Key Enhancements:**
  - Designed specifically for terminal-based coding agents and personal superintelligence.
  - Benchmark scores: DeepSWE 1.1 (75.4%), Terminal-Bench 2.1 (88.8%).
  - Token and Tool Efficiency: Completes coding tasks using ~20% fewer tool calls and ~25% fewer tokens than Muse Spark 1.2 by eliminating redundant discursive reasoning and optimizing tool calling ergonomics.
- **Deployment:** Accessible in Muse Code (terminal coding agent) and Meta Model API; open-weight weights planned for later release.

## 3. Alibaba Cloud: Qwen3.8-Max-0902
- **Release Date:** September 2, 2026 (versioned snapshot of the flagship Qwen3.8-Max released August 3, 2026).
- **Architecture:** 2.4 Trillion parameter Mixture-of-Experts (MoE) with fine-grained routing.
- **Key Enhancements:**
  - 1 Million token context window, 128K maximum output tokens.
  - Optional thinking mode with up to 256K chain-of-thought token budget.
  - Post-trained specifically for repository-level software engineering, autonomous agents, and multi-modal chart/document reasoning.
  - Leaderboard: Scored 1691 on LMArena Code Arena: WebDev.
- **Deployment:** Alibaba QwenCloud API identifier `qwen3.8-max-0902`.

## 4. Anthropic: Claude Fable 5.1 & Claude Mythos 5.1
- **Release Date:** September 1, 2026.
- **Architecture & Relationship:** Fable 5.1 and Mythos 5.1 share identical underlying model weights and architecture. Difference is access tier and safeguard tuning:
  - Fable 5.1: General enterprise/developer availability (Claude API, Bedrock, Google Cloud, Azure Foundry).
  - Mythos 5.1: Restricted, invitation-only access (Project Glasswing) for vetted defense, cybersecurity, and life-sciences organizations.
- **Key Enhancements:**
  - 1M token context window, 128K output window.
  - Benchmark leadership on Terminal-Bench 4.0 and Terminal-Bench-Science 0.1.
  - Cache Read Fee Reduction: Slashed prompt cache read pricing by 75% to $0.25 / 1M tokens ($10/M input, $50/M output base), reducing effective agent workload costs by 25% to 45%.
  - Tuned safeguards to reduce false-positive refusals on cybersecurity audit and biomedical reasoning tasks.

## 5. Moonshot AI: Kimi K3
- **Release Date:** July 2026.
- **Architecture:** 2.8 Trillion parameter Mixture-of-Experts (MoE) model.
- **Key Enhancements:**
  - Open-weight natively multimodal agentic model.
  - 1 Million token context window.
  - Optimized for agentic execution and long-document synthesis across visual and textual data.
