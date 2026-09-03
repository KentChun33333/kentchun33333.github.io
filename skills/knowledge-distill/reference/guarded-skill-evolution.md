# Guarded Skill Evolution (GSE) and Decision-Frontier Elicitation

This document specifies the **Guarded Skill Evolution (GSE)** framework adapted from Kent Chiu's research ([`idea-paper/guarded-skill-evolution/guarded-skill-evolution-v2.html`](../../idea-paper/guarded-skill-evolution/guarded-skill-evolution-v2.html)). It governs how skills, contracts, and evaluation profiles evolve safely without regression, instruction bloat, or premature rewrites.

---

## 1. Core Operating Principles

Skill evolution is a **selective intervention problem under specification uncertainty**—not an automatic rewrite operation.

```text
observed failure or user request
               │
               ▼
   [EPISTEMIC GUARD: GRILLING]
   ├── Walk decision tree frontiers (Ft)
   ├── Separate agent facts from user decisions
   └── Attribute true failure owner (8 categories)
               │
      ┌────────┼────────────────────────┐
      ▼        ▼                        ▼
  [CLARIFY]  [REPAIR OTHER]          [RETAIN]
  (ask Ft)   (fix tool/route/data)   (noise/unjustified)
               │
               ▼ (only if owner == "skill")
   [FALSIFIABLE CHANGE CONTRACT]
   (problem, objective, invariants, scope, hypothesis)
               │
               ▼
   [CANDIDATE GENERATION: s' = s0 + Δ]
   (minimal edit budget, bounded scope)
               │
               ▼
   [EMPIRICAL GUARD: PAIRED 4-SLICE GATE]
   ├── Source repair (motivating cases)
   ├── Target generalization (held-out cases)
   ├── Regression preservation (existing behaviors)
   └── Challenge cases (boundaries & adversaries)
               │
               ▼
     PROMOTE iff LCB > δ and Regression ≤ ρ
```

---

## 2. Epistemic Guard: Decision-Frontier Elicitation ("Grilling")

When a user requests a skill change or critiques an output, the system must not immediately jump into editing. Instead, it models requirement discovery as a **design tree** where nodes represent decisions and directed edges represent prerequisite dependencies.

### 2.1 The Frontier Rule

At step $t$, the question set contains only unresolved decisions whose prerequisites are completely settled:

$$F_t = \{ d \in D_{\text{unresolved}} : \operatorname{pred}(d) \subseteq D_{\text{resolved},t} \}$$

- **No premature questions:** Never ask about downstream implementation parameters (e.g., threshold values, card styles) before resolving the core objective and failure owner.
- **Batching independent nodes:** Questions within the same frontier $F_t$ share prerequisites but are logically independent; they may be presented together in a single round.
- **Cost-aware stopping rule:** Stop asking further questions when:

$$\text{ExpectedDecisionValue}(F_t) \le \text{interaction cost}$$

If the remaining uncertainty does not alter the intervention type, scope boundary, or acceptance threshold, proceed without burdening the user.

### 2.2 Facts vs. Decisions Separation

Never ask the user for information that the agent can ascertain through direct investigation.

| Category | Owner | Investigation Method |
|---|---|---|
| **Environment Facts** | **Agent** | Inspect execution traces, file systems, git diffs, tool outputs, delivery fingerprints, schema definitions, and unit test results directly. |
| **Value Judgments & Objectives** | **User** | Elicit intended downstream utility, trade-offs between competing metrics, acceptable risk tolerance, and non-negotiable hard invariants. |

### 2.3 The Four Decision Rounds

```text
Round 01: Root Intent      ──→ What outcome should improve? Who is the beneficiary?
Round 02: First Frontier   ──→ Problem gap, agent failure evidence, user hard invariants
Round 03: Derived Frontier ──→ True failure owner, minimum meaningful gain (δ), permitted scope
Round 04: Confirmation Gate──→ Freeze shared Change Contract; explicit approval before editing
```

1. **Round 01 (Root Intent):** Clarify the true purpose of the request. (e.g., "Which downstream decision or deliverable should this improve?")
2. **Round 02 (First Frontier):**
   - *User decision:* What specific gap is observed in the current output?
   - *Agent fact:* Can the agent reproduce the failure trace from existing logs or test inputs?
   - *User decision:* What invariants must remain strictly preserved?
3. **Round 03 (Derived Frontier):**
   - *Agent fact:* Failure owner attribution (see Section 3).
   - *User decision:* What is the smallest meaningful gain $\delta$ that justifies persistent mutation?
   - *Joint decision:* What is the strict boundary of permitted modification?
4. **Round 04 (Confirmation Gate):**
   - An empty frontier is **never** authorization to mutate.
   - The resolved tree is synthesized into a formal **Change Contract** presented to the user. Editing begins only upon confirmation.

---

## 3. Failure-Owner Attribution

Before modifying any skill, diagnose the failure across the 8 candidate failure owners:

| Failure Owner | Diagnostic Question | True Action | Anti-Pattern to Avoid |
|---|---|---|---|
| **`skill`** | Is reusable procedural instruction absent, misleading, or incorrect? | **Revise skill** | Do not bloat skill if execution failed elsewhere. |
| **`routing`** | Does the correct skill exist but fail to be delivered or triggered? | **Repair routing** | Do NOT create duplicate skills or embed instructions to mask route misses. |
| **`tool`** | Did execution fail in a parser, script, adapter, or external tool? | **Repair tool/script** | Do NOT add LLM prompt rules to compensate for a broken deterministic parser. |
| **`data`** | Is the input data or corpus malformed, truncated, or missing evidence? | **Improve intake/validation** | Do NOT hallucinate or relax evidence gates. |
| **`model`** | Is the procedure clear but beyond the carrier model's capability? | **Change model / decompose** | Do NOT endlessly reword prompt instructions. |
| **`evaluator`** | Is the measured defect an artifact of scoring rules or profile mismatch? | **Repair evaluator profile** | Do NOT game the evaluator by warping procedural truth. |
| **`spec`** | Are objectives, trade-offs, or constraints conflicting or underspecified? | **Clarify via frontier** | Do NOT guess user preferences or make subjective edits. |
| **`noise`** | Was the failure an isolated, non-reproducible stochastic run? | **Retain and monitor** | Do NOT permanently mutate a skill based on one outlier. |

---

## 4. The Change Contract

Every skill evolution must be formalized in a testable contract before candidate generation.

### 4.1 Schema (`change-contract.yaml` or `.json`)

```yaml
version: 1
skill_name: "knowledge-distill"
failure_owner: "skill" # One of: skill, routing, tool, data, model, evaluator, spec, noise

problem:
  observed_behavior: "Summaries present citations but lack explicit evidence-to-decision causal links."
  suspected_cause: "The skill specifies source indexing but lacks a structured reasoning step linking findings to actionable recommendations."
  reproducibility: "reproducible_in_trace"

objective:
  target_behavior: "Synthesize findings into concise, causal conclusions linked to verified source IDs."
  success_metric: "Decision usefulness increases without lowering factual citation density."
  minimum_meaningful_gain_delta: 0.10

invariants:
  - "Preserve valid source IDs and provenance hashes"
  - "Do not invent or extrapolate ungrounded claims"
  - "Preserve output formatting and manifest export schema"
  - "Do not exceed token budget (+15% maximum edit delta)"

out_of_scope:
  - "Modifying input parsing tools or graph extraction scripts"
  - "Altering unrelated builder skill interfaces"

proposed_change:
  hypothesis: "Adding a structured 'evidence -> reason -> recommendation' gate improves downstream decision utility."
  minimal_scope: "Update synthesis instruction section in SKILL.md only."
```

---

## 5. Candidate Generation & The Empirical Gate

### 5.1 Minimal Edit Budget

The revision $s' = s_0 + \Delta$ must satisfy:

$$\max_\Delta \quad U(s_0 + \Delta; z) - U(s_0; z) - \lambda_1 |\Delta| - \lambda_2 C_{\text{run}}(s_0 + \Delta)$$

- Edit budget: Prefer deletions, substitutions, and conditionalization over unbounded instruction additions.
- Every edit must directly trace back to a diagnosed defect in the change contract.

### 5.2 Paired 4-Slice Evaluation

Candidates are tested alongside the incumbent under identical seeds, tools, models, and budgets across four evaluation slices:

1. **Source Repair:** Cases that motivated the evolution request (must resolve the observed symptom).
2. **Target Generalization:** Held-out, unseen cases representing the desired behavior (must demonstrate true transfer).
3. **Regression Preservation:** Existing baseline cases and invariants (must not degrade previous capabilities).
4. **Challenge Cases:** Boundary inputs, conflicting specs, missing data, and adversarial conditions.

### 5.3 Promotion Equation

A candidate skill $s'$ is promoted to active production if and only if:

$$\operatorname{LCB}_{1-\alpha}\left(\overline{U(s') - U(s_0)}\right) > \delta \quad \land \quad \operatorname{CriticalRegressionRate}(s', s_0) \le \rho \quad \land \quad \forall \text{inv} \in \text{Invariants}, \; \operatorname{pass}(\text{inv})$$

Where:
- $\operatorname{LCB}_{1-\alpha}$ is the lower confidence bound on paired utility improvement across held-out cases.
- $\delta$ is the minimum meaningful gain specified in the Change Contract.
- $\rho$ is the critical regression threshold (typically 0.0 for hard invariants).

---

## 6. Version Ledger and Rollback

Every accepted or rejected evolution proposal must append an entry to [`reference/skill-evolution-ledger.md`](skill-evolution-ledger.md):
- Target skill and date.
- Initial request and failure owner diagnosis.
- Link to Change Contract.
- Diff summary and minimal edit scope.
- 4-slice evaluation results (baseline score vs. candidate score).
- Promotion decision (`ACCEPTED`, `REJECTED`, or `REPAIR_OTHER`) and `.prev` rollback pointer.
