# Analysis: Ablation Dynamics in Synthetic Distillation Flywheels

Quantitative relationships governing the interactive simulator for synthetic data flywheels.

## 1. Verification Filtering Quality Ablation

| Filter Mode | Pass Rate on Math/Code | Model Collapse Risk (5 Generations) | Effective Token Density |
|---|:---:|:---:|:---:|
| **Unfiltered (Raw Synthetic)** | 42.0% (Degrades to 18% by Gen 4) | **Extreme (Catastrophic collapse)** | Very Low (Memorizes hallucinations) |
| **Heuristic / Keyword Filter** | 58.0% (Plateaus early) | Moderate (Error accumulation) | Moderate (Retains false positives) |
| **Deterministic Unit Tests / Compilers** | 76.5% (Stable across generations) | **Near Zero (Entropy anchored)** | High (Verified reasoning only) |
| **Verifier + Fluff Pruning (Peak)** | **84.2%** (Highest throughput) | **Zero (Maximum stability)** | **Peak (35% token compression)** |

## 2. Teacher-to-Student Parameter Ratio Dynamics
- **$2.4\text{T} \to 70\text{B}$ Student:** Absorbs ~92% of teacher reasoning capability; retains broad general knowledge and complex instruction following.
- **$2.4\text{T} \to 32\text{B}$ Student:** Sweet spot for efficiency (DeepSeek-R1-Distill-32B). Retains ~88% of teacher reasoning on MATH-500 and AIME.
- **$2.4\text{T} \to 7\text{B}$ Student:** Absorbs ~72% of teacher capability; requires focused domain distillation to prevent capacity saturation.
- **$2.4\text{T} \to 1.5\text{B}$ Student:** Struggles with multi-step reasoning context retention; requires strict token compression.

## 3. The Collapse Entropy Equation Across Generations
Let $H(X_n)$ be the lexical and functional entropy of generation $n$:

$$H(X_n) = H(X_0) \cdot \left( 1 - \lambda_{\text{decay}} \right)^n + \alpha_{\text{anchor}} \cdot H_{\text{real}}$$

- When $\alpha_{\text{anchor}} = 0$ and filter is unfiltered: $\lambda_{\text{decay}} \approx 0.25 \implies$ total collapse by generation 4.
- When $\alpha_{\text{anchor}} \ge 0.15$ and filter is deterministic compiler: $\lambda_{\text{decay}} \approx 0.01 \implies$ distribution remains stable indefinitely.
