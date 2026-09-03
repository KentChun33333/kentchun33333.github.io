# Analysis: Dependency Structure in Synthetic Distillation Flywheels

The causal graph of components governing reasoning transfer and model stability.

```text
       ┌──────────────────────────────────────────────┐
       │   Massive Frontier Teacher (2.4T–2.8T MoE)   │
       │   (High reasoning capability, slow inference)│
       └──────────────────────┬───────────────────────┘
                              │ Emits K candidate reasoning traces
                              ▼
       ┌──────────────────────────────────────────────┐
       │   Deterministic Programmatic Verifier        │
       │   (Compilers, test harnesses, SymPy, Z3)     │
       └──────────────────────┬───────────────────────┘
                              │ Filters out all failing or hallucinated rollouts
                              ▼
       ┌──────────────────────────────────────────────┐
       │   Token De-Noiser & Fluff Pruner             │
       │   (Compresses reasoning chains by 35%)       │
       └──────────────────────┬───────────────────────┘
                              │ Delivers clean, verified supervised dataset
                              ▼
       ┌──────────────────────────────────────────────┐
       │   Compact Student Model (7B–32B Dense)       │
       │   (Fast, low-cost inference workhorse)       │
       └──────────────────────────────────────────────┘
```

## Failure Modes When Links Break:
1. **Bypassing the Verifier:** If unverified teacher rollouts are fed directly to the student, the student memorizes subtle reasoning bugs, causing rapid model collapse (Shumailov et al.).
2. **Skipping De-Noising:** Training the student on verbose, unpruned teacher tokens forces the small student to waste parameter capacity modeling conversational filler.
3. **Zero Human/Real Anchor Prompts:** Over multiple flywheel generations ($n \ge 3$), the vocabulary distribution becomes stylistically robotic unless anchored with 10–30% diverse real-world human tasks.
