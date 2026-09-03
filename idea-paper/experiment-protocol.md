# GSE Experiment Protocol

This document defines a preregistration-ready evaluation of Guarded Skill Evolution.

## 1. Experimental question

Does combining requirement/root-cause analysis with paired incumbent–candidate evaluation improve the net reliability of skill evolution compared with direct rewriting?

## 2. Conditions

Randomize each benchmark episode across the following conditions while keeping model, tools, budgets, and seeds matched.

| ID | Method | Elicitation/diagnosis | Version gate |
|---|---|---:|---:|
| C0 | No change | No | Incumbent only |
| C1 | Direct evolution | No | No |
| C2 | Elicitation only | Yes | No |
| C3 | Evaluation only | No | Yes |
| C4 | Full GSE | Yes | Yes |
| C5 | Oracle specification | Oracle supplied | Yes |

## 3. Episode construction

Target 300 episodes across 30 base skills and four domains:

- software engineering;
- spreadsheets and documents;
- evidence-grounded research;
- tool-using operational workflows.

Each base skill contributes ten episodes balanced across request types. Split by base skill, not by individual task, when testing cross-skill generalization.

Every episode contains:

1. incumbent skill and dependencies;
2. initial user request;
3. hidden complete requirement;
4. true root cause and oracle action;
5. triggering cases;
6. held-out target cases;
7. regression cases;
8. challenge cases;
9. executable and/or rubric-based evaluators.

## 4. Interaction protocol

For guarded conditions, an oracle user answers only from the hidden requirement record. It must not volunteer unspecified information. Record every question, the requirement field it targets, whether it can alter the intervention decision, and the answer.

Stop elicitation when any of these conditions holds:

- posterior intervention confidence exceeds the preregistered threshold;
- all critical requirement fields are resolved;
- expected information gain falls below the interaction-cost threshold;
- the maximum turn budget is reached.

For GSE conditions, represent unresolved user decisions as a dependency tree. In each round, ask only the current frontier: unresolved decisions whose prerequisites are resolved. Investigate environment-resolvable facts directly rather than asking the user. Recompute the frontier after every round or material evidence update, and require explicit confirmation of the resulting change contract before candidate generation.

Run a human validation subset of at least 40 stratified episodes to measure oracle-user realism and question burden.

## 5. Candidate protocol

- Give every condition the same incumbent and total optimization budget.
- Require a machine-readable change hypothesis for C2–C5.
- Limit candidate count and total evaluation rollouts equally.
- Use identical target model, temperature, tools, and environment snapshots.
- Pair seeds between incumbent and candidate.
- Prevent the editor from reading held-out or regression expected outputs.

For conditions with a version gate, use source-repair results for diagnosis, a validation slice for candidate selection, and a locked test slice for final reporting.

## 6. Primary metrics

### 6.1 Evolution Decision Accuracy

Macro-F1 over:

```text
CLARIFY
REVISE_SKILL
REPAIR_OTHER_COMPONENT
RETAIN_INCUMBENT
```

Also report hierarchical accuracy: first `change vs no change`, then correct intervention owner.

### 6.2 Net Evolution Utility

```text
NEU = held_out_gain
      - λr × regression_severity
      - λc × normalized_compute_cost
      - λi × normalized_interaction_burden
```

Preregister the weights and publish sensitivity plots over a reasonable range rather than selecting weights after results are known.

### 6.3 Harmful Evolution Rate

Fraction of promoted candidates whose locked-test NEU is below the incumbent by more than the smallest effect of interest.

### 6.4 Unnecessary Evolution Rate

Fraction of oracle no-change or non-skill-repair episodes in which the method nevertheless edits the skill.

## 7. Secondary metrics

- requirement-field recall and precision;
- critical-invariant recovery;
- targeted-question yield per turn;
- frontier validity and premature-question rate;
- question count and round count;
- average clarification turns;
- source-case repair rate;
- target held-out performance;
- critical and non-critical regression rates;
- worst-slice utility;
- candidate edit distance and skill token growth;
- execution tokens, latency, and monetary cost;
- human-rated question relevance, frustration, confidence, and acceptance.

## 8. Promotion rule

Preregister a smallest meaningful effect \(\delta\), confidence level \(1-\alpha\), and critical regression cap \(\rho\).

Promote only when:

```text
lower_confidence_bound(paired_gain) > δ
and critical_regression_rate <= ρ
and every hard invariant passes
```

Otherwise return `REJECT` or `INSUFFICIENT_EVIDENCE`. Do not count retention as a failure when the oracle indicates that no change is correct.

## 9. Factorial analysis

Estimate the main and interaction effects of elicitation \(E\) and version gating \(V\):

\[
g(Y)=\beta_0+\beta_1E+\beta_2V+\beta_3(E\times V)+u_{skill}+u_{domain}+u_{model}.
\]

Use logistic mixed-effects models for binary outcomes and hierarchical linear or ordinal models for continuous or rated outcomes. Report paired bootstrap confidence intervals and effect sizes. Correct the family of confirmatory hypotheses; label all other analyses exploratory.

## 10. Confirmatory hypotheses

- **H1:** C4 has lower Harmful Evolution Rate than C1.
- **H2:** C4 has lower Unnecessary Evolution Rate than C1.
- **H3:** C4 has higher locked-test NEU than C1.
- **H4:** Elicitation has its largest effect on ambiguous and misdiagnosed requests.
- **H5:** Version gating reduces regression even when the initial requirement is clear.
- **H6:** The positive interaction \(E\times V\) is largest when the initial request optimizes a proxy rather than the true objective.

## 11. Ablations

Run C4 without each component:

- failure-owner classifier;
- adaptive questions;
- change contract;
- no-change action;
- edit-size regularization;
- held-out target slice;
- regression slice;
- confidence-bound threshold;
- insufficient-evidence outcome;
- structured version ledger.

The critical ablation is **C4 without the ability to retain the incumbent**. It tests whether selective intervention—not simply a stronger editing prompt—drives the gain.

## 12. Reproducibility artifacts

Release:

- immutable episode manifests and split hashes;
- skill versions and exact diffs;
- prompts, model identifiers, sampling parameters, and seeds;
- tool/environment container identifiers;
- raw trajectories with redaction policy;
- executable evaluators and judge rubrics;
- per-episode decisions, confidence values, costs, and receipts;
- analysis notebooks and preregistration.
