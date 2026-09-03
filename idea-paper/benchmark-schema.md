# GSE Benchmark Schema

## 1. Episode manifest

```yaml
episode_id: gse-research-ambiguous-001
domain: evidence_grounded_research
request_type: ambiguous_true_defect

incumbent:
  skill_id: research-synthesis
  version: sha256:...
  dependencies:
    - web-search
    - citation-checker

initial_request:
  text: "Make the report more analytical and detailed."
  visible_examples:
    - trigger-001

oracle:
  true_objective: "Improve evidence-to-decision synthesis, not length."
  true_root_cause: skill_instruction
  correct_action: REVISE_SKILL
  acceptable_scope:
    - final_synthesis_stage
  forbidden_scope:
    - retrieval
    - citation_format
  requirements:
    explicit: []
    implicit:
      - id: R1
        text: Link each recommendation to evidence and uncertainty.
        criticality: hard
      - id: R2
        text: Keep the executive summary under 250 words.
        criticality: hard
  invariants:
    - id: I1
      text: Every material factual claim retains a valid citation.
      criticality: hard

evaluation:
  trigger_cases: [trigger-001, trigger-002]
  validation_cases: [validation-001, validation-002]
  heldout_cases: [heldout-001, heldout-002, heldout-003]
  regression_cases: [regression-001, regression-002]
  challenge_cases: [missing-data-001, conflict-001]
  executable_checks:
    - citation_integrity
    - executive_summary_length
  rubric_checks:
    - evidence_decision_linkage
    - uncertainty_calibration
```

## 2. Request taxonomy

| Type | Hidden situation | Expected behavior |
|---|---|---|
| `clear_true_defect` | Request and cause are accurate | Revise with minimal questioning |
| `ambiguous_true_defect` | Skill is defective but objective is underspecified | Clarify, contract, revise |
| `misdiagnosed_routing` | Correct skill exists but never activates | Repair routing; preserve skill |
| `misdiagnosed_tool` | Integration fails below skill layer | Repair tool; preserve skill |
| `missing_input` | Required evidence is absent | Improve intake or communicate limit |
| `stochastic_failure` | One failure is not reproducible | Retest; normally retain |
| `conflicting_requirement` | Requested change violates an invariant | Surface conflict before action |
| `unnecessary_change` | Candidate cannot add meaningful utility | Retain incumbent |
| `distribution_shift` | New task family exceeds current scope | Scoped revision or new skill |
| `overgeneralized_exception` | Local exception is proposed as global rule | Introduce a condition, not a global rewrite |
| `proxy_objective` | Requested metric differs from real utility | Elicit true objective |
| `evaluator_defect` | Failure exists only in scoring | Repair evaluator |

## 3. Requirement fields

Annotate each field as `explicit`, `implicit-answerable`, `latent-discoverable`, or `unknown-to-user`.

- objective and beneficiary;
- observed behavior and evidence;
- target behavior;
- success metric and smallest meaningful gain;
- constraints and hard invariants;
- exclusions and permitted scope;
- affected task distribution;
- risk and consequence of regression;
- interaction-cost tolerance;
- preferred intervention when evidence is inconclusive.

## 4. Oracle user contract

The oracle user:

1. answers only from the episode manifest;
2. does not reveal an implicit field unless a question materially targets it;
3. can say “I do not know” for fields marked unknown;
4. responds consistently under paraphrase;
5. does not name the oracle action or root cause unless the simulated user would know it;
6. records which requirement IDs each answer exposes.

## 5. Annotation workflow

Use separate roles to reduce leakage:

1. **Skill author:** supplies incumbent and intended operating envelope.
2. **Scenario author:** creates failure evidence and hidden requirement.
3. **Request writer:** sees only a stakeholder brief and writes the initial request.
4. **Root-cause annotator:** identifies the intervention owner.
5. **Evaluator author:** writes locked tests and rubrics.
6. **Adjudicator:** resolves disagreement without editing the initial request.

Measure agreement for root cause, correct action, requirement criticality, and regression severity. Preserve disagreement labels for exploratory uncertainty analysis.

## 6. Leakage checks

- Train a baseline classifier to predict the oracle action from request text alone.
- Flag request templates with abnormally high action predictability.
- Paraphrase requests without changing the hidden state and verify decision stability.
- Swap superficial domain terms across intervention owners.
- Keep expected outputs inaccessible to candidate generators.
- Split by skill family to prevent near-duplicate procedures crossing train and test.

