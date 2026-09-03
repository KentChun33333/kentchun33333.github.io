# Guarded Skill Evolution: Requirement-Aware and Regression-Controlled Improvement of LLM Agent Skills

**Kent Chiu — Research proposal, September 2026**

## Abstract

Agent skill-evolution methods improve reusable procedural instructions from execution traces or user feedback. Most methods, however, begin from an untested premise: that an evolution request correctly identifies both the underlying defect and the desired change. In practice, requests may be ambiguous, incomplete, misdiagnosed, or based on isolated failures. Directly rewriting a persistent skill can therefore introduce regressions, increase complexity, and create apparent improvement without meaningful user utility.

We introduce **Guarded Skill Evolution (GSE)**, a framework that treats skill modification as an evidence-gated decision rather than a default action. GSE first analyzes the evolution request, elicits missing objectives and constraints when necessary, distinguishes skill defects from execution, routing, tool, data, model, and evaluation failures, and constructs a testable change contract. Candidate revisions are evaluated against the incumbent skill with paired held-out tasks, regression suites, cost measures, and requirement-alignment criteria. The incumbent is retained whenever evidence for improvement is insufficient.

We propose a benchmark containing clear, underspecified, misdiagnosed, conflicting, and unnecessary skill-evolution requests across several agent-task domains. A factorial experiment separates the effects of requirement elicitation and version-gated evaluation. We hypothesize that GSE will reduce harmful and unnecessary skill changes while improving held-out utility and user-intent alignment, at the cost of a modest increase in interaction and evaluation overhead.

## 1. Introduction

Skills package reusable procedural knowledge for language-model agents. They can describe how to sequence tools, validate artifacts, recover from errors, and satisfy domain constraints. Recent methods optimize skills from trajectories, reflection, textual edits, or evolutionary search. This creates an increasingly capable improvement loop, but it also turns a skill file into persistent mutable behavior.

Persistent behavior should not change merely because a user asks for an edit or because one execution failed. Three epistemic questions precede optimization:

1. **Is the observed problem real and reproducible?**
2. **Is the skill the causal owner of that problem?**
3. **What user objective, constraints, and invariants define an improvement?**

An agent that skips these questions can efficiently optimize the wrong intervention. For example, it may add instructions when the actual failure is a broken parser; globally enforce a rule motivated by one exception; or make reports longer when the desired outcome is stronger evidence-to-decision synthesis.

We argue that skill evolution is a **selective intervention problem under specification uncertainty**. The system must choose among clarification, skill revision, repair of another component, and retention of the incumbent. Only after this decision should it search for a new skill version.

### 1.1 Contributions

This proposal makes four contributions:

1. It formulates skill evolution as a decision over **whether, where, and how** to intervene rather than assuming that a skill rewrite is required.
2. It introduces a two-sided guardrail: a **pre-evolution epistemic guard** for requirement and root-cause analysis, and a **post-evolution empirical guard** for paired version comparison.
3. It defines a benchmark in which the correct action is sometimes clarification, no change, or repair of a non-skill component.
4. It proposes metrics for evolution decision accuracy, harmful evolution, unnecessary evolution, requirement recovery, regression severity, and net utility.

## 2. Problem formulation

Let an incumbent skill be \(s_0\), an initial user request be \(r_0\), and observed evidence be \(e_0\). A conventional evolution system directly generates a candidate:

\[
s_1 = \operatorname{Evolve}(s_0, r_0, e_0).
\]

GSE instead infers a latent change specification \(z\) and selects an intervention:

\[
a^* \in \{\text{clarify},\text{revise-skill},\text{repair-other},\text{retain}\}.
\]

When clarification is selected, the system chooses a question \(q_t\) that maximizes expected information gain while accounting for user burden:

\[
q_t^* = \arg\max_q I(z; y_q \mid h_t) - \lambda_q C(q),
\]

where \(y_q\) is the anticipated answer, \(h_t\) is dialogue history, and \(C(q)\) estimates interaction cost. The system stops asking when the expected value of further information falls below its cost or the intervention decision is sufficiently stable.

If a skill revision is warranted, the editor proposes a minimal change \(\Delta\):

\[
s' = s_0 + \Delta,
\]

\[
\max_\Delta \quad U(s_0+\Delta;z)-U(s_0;z)-\lambda_1|\Delta|-\lambda_2C_{run}(s_0+\Delta).
\]

The candidate is promoted only if the lower confidence bound on paired utility improvement exceeds a meaningful threshold \(\delta\) and critical regressions remain below \(\rho\):

\[
\operatorname{LCB}_{1-\alpha}(\bar d)>\delta,
\qquad
\operatorname{CriticalRegressionRate}(s',s_0)\leq\rho,
\]

where \(d_i=U_i(s')-U_i(s_0)\) on matched cases and seeds.

## 3. Guarded Skill Evolution

### 3.1 Request adequacy gate

GSE extracts a requirement state

\[
R=(O,P,E,C,I,N),
\]

containing the objective \(O\), observed problem \(P\), supporting evidence \(E\), constraints \(C\), invariants \(I\), and excluded scope \(N\). It evaluates ambiguity, consequence, evidence sufficiency, and contradictions. The gate does not force an interview for every request: it asks targeted questions only when additional information may change the intervention or acceptance criteria.

### 3.2 Failure-owner diagnosis

The system attributes the problem across a structured failure topology:

| Candidate owner | Diagnostic question | Typical intervention |
|---|---|---|
| Skill instruction | Is reusable procedural knowledge absent or incorrect? | Revise the skill |
| Routing/retrieval | Does the correct skill exist but fail to activate? | Repair routing |
| Tool/integration | Did execution fail below the instruction layer? | Repair tool or adapter |
| Input/data | Is required evidence absent or malformed? | Improve intake or validation |
| Model capability | Is the procedure clear but beyond the carrier model? | Change model or decompose |
| Evaluator | Is the measured failure an artifact of scoring? | Repair evaluation |
| User specification | Are objectives, trade-offs, or invariants unresolved? | Clarify |
| Stochastic execution | Is the failure isolated and non-reproducible? | Retest |

The diagnosis may assign a primary owner and connected secondary repairs. It must not create a duplicate skill to compensate for a routing failure or accumulate instructions to mask a tool defect.

### 3.3 Change contract

Before editing, GSE produces a compact contract that can be checked by the user and evaluator:

```yaml
problem:
  observed_behavior: Reports contain evidence but lack decision synthesis.
  suspected_cause: The skill specifies extraction but not evidence-to-decision mapping.

objective:
  target_behavior: Produce concise conclusions linked to evidence.
  success_metric: Improve decision usefulness without reducing factual accuracy.

invariants:
  - preserve source citations
  - do not invent missing evidence
  - preserve the current export format

out_of_scope:
  - changing retrieval tools
  - adding unrelated report sections

proposed_change:
  hypothesis: An evidence-reason-action structure improves usefulness.
  minimal_scope: Modify the final synthesis stage only.
```

The contract makes a proposed evolution falsifiable and provides a stable evaluation target even if the candidate wording changes.

### 3.4 Candidate generation

The editor receives the incumbent, contract, triggering traces, and a strict edit budget. Every edit must be linked to a diagnosed defect or contract requirement. Candidate generation favors deletion, substitution, conditionalization, and focused additions over unbounded instruction accumulation.

### 3.5 Paired version gate

The incumbent and candidate run on identical cases, seeds, tools, and model settings. Evaluation has four slices:

- **Source repair:** cases that motivated the request.
- **Target generalization:** unseen cases representing the desired behavior.
- **Regression preservation:** existing behaviors and invariants.
- **Challenge cases:** boundary, conflict, missing-data, and adversarial scenarios.

The gate returns **accept**, **reject**, or **insufficient evidence**. The third outcome avoids converting noisy measurements into permanent behavior.

### 3.6 Version ledger

Every proposal records:

- parent and candidate identifiers;
- request and final change contract;
- diagnosis and alternative interventions considered;
- exact diff and edit rationale;
- evaluation cases, seeds, model, and tool versions;
- per-slice results and confidence intervals;
- decision and rollback pointer.

This transforms skill evolution from opaque rewriting into an auditable sequence of testable hypotheses.

## 4. Relation to prior work

Existing methods establish that skills can be improved through execution evidence and textual optimization. SkillRevise diagnoses defects from traces, repairs candidate skills, re-executes them, and retains the empirically useful version. SkillOpt introduces bounded textual edits, held-out acceptance, rejected-edit feedback, and slow meta-updates. SkillMOO treats skill bundles as a multi-objective search over performance and cost. MetaSkill-Evolve recursively improves both task skills and the improvement procedure.

GSE addresses an earlier decision boundary. It does not assume the request names the correct failure owner, that the initial objective is adequate, or that revision is required. Requirement-elicitation research provides mechanisms and metrics for uncovering implicit requirements, but does not generally connect them to persistent agent-skill mutation. GSE joins these lines of work.

| Research direction | Main question | Gap addressed by GSE |
|---|---|---|
| Trace-conditioned revision | How can traces repair a weak skill? | The trace may reflect a non-skill cause |
| Skill optimization | Which textual edit improves validation reward? | The reward may encode the wrong user objective |
| Multi-objective evolution | How should performance, cost, and size be balanced? | The need and scope of intervention remain assumed |
| Meta-skill evolution | Can the evolution procedure improve itself? | Recursive improvement can recursively amplify a wrong premise |
| Requirements elicitation | What does the user actually need? | Elicited intent is not tied to skill promotion and regression gates |

## 5. Research questions and hypotheses

**RQ1 — Evolution decision quality.** Does GSE more accurately choose among clarification, skill revision, non-skill repair, and retention?

**RQ2 — Final effectiveness.** Do guarded revisions achieve higher held-out utility than direct evolution?

**RQ3 — Change safety.** Does GSE reduce harmful changes, unnecessary changes, overfitting, and skill bloat?

**RQ4 — Cost-benefit trade-off.** Are improvements worth the additional interaction turns, tokens, latency, and evaluation rollouts?

We hypothesize that requirement gating will contribute most on ambiguous and misdiagnosed requests, version gating will reduce regressions across all request types, and their combination will be super-additive because evaluation is most useful when it measures the correct objective.

## 6. Experimental design

The core study is a \(2\times2\) factorial experiment:

| Condition | Requirement and diagnosis guard | Paired version guard |
|---|---:|---:|
| Direct evolution | No | No |
| Elicitation only | Yes | No |
| Evaluation only | No | Yes |
| Full GSE | Yes | Yes |

Two references bound performance: a **no-change incumbent** and an **oracle specification** condition given the complete hidden requirement and true failure owner.

The benchmark should contain approximately 300 evolution episodes built from 30 base skills in software engineering, spreadsheet/document production, analytical research, and tool-using workflows. Each episode includes a triggering set, target held-out set, regression set, challenge set, hidden requirement, and oracle intervention. Clear, ambiguous, misdiagnosed, conflicting, unnecessary, distribution-shift, and overgeneralized requests are deliberately balanced.

Primary outcomes are Net Evolution Utility, Evolution Decision Accuracy, Harmful Evolution Rate, and Unnecessary Evolution Rate. Secondary outcomes include requirement recovery, critical regression severity, skill-length growth, execution cost, question relevance, and user burden. Full details are specified in [`experiment-protocol.md`](experiment-protocol.md).

## 7. Risks and validity

An LLM-simulated user makes large-scale evaluation reproducible but may not capture human inconsistency, fatigue, or evolving preferences. A second phase should therefore validate a stratified subset with real participants. LLM judges can measure open-ended quality but must be calibrated against experts and supplemented with executable checks wherever possible.

Benchmark authors may leak the oracle intervention through request wording. Request writers and annotators should be separated, and episode difficulty should be audited through blinded baselines. Finally, adaptive questioning can become intrusive. Question utility and user burden must be measured jointly so that the framework does not replace blind evolution with indiscriminate interrogation.

## 8. Expected significance

As agents rely on increasingly persistent skills, an incorrect edit can affect many future tasks rather than one response. The safety unit is therefore not only the current output but the mutation process itself. GSE changes the governing question from “How can this skill be improved?” to:

> “What intervention is justified by the evidence, and has it produced a meaningful net improvement without violating preserved behavior?”

This framing makes no-change a successful outcome, clarification an optimization action, and comparative evidence a prerequisite for persistence.

## References

- Gong, J. et al. (2026). [SkillMOO: Multi-Objective Optimization of Agent Skills for Software Engineering](https://arxiv.org/abs/2604.09297).
- Jin, D. et al. (2026). [ReqElicitGym: An Evaluation Environment for Interview Competence in Conversational Requirements Elicitation](https://arxiv.org/abs/2602.18306).
- Wang, Z. et al. (2026). [MetaSkill-Evolve: Recursive Self-Improvement of LLM Agents via Two-Timescale Meta-Skill Evolution](https://arxiv.org/abs/2607.05297).
- [SkillOpt: Agent Skill Optimization as Bounded Textual Learning](https://arxiv.org/abs/2605.23904) (2026).
- [SkillRevise: Improving LLM-Authored Agent Skills via Trace-Conditioned Skill Revision](https://arxiv.org/abs/2606.01139) (2026).
- Wang, G. et al. (2023). [Voyager: An Open-Ended Embodied Agent with Large Language Models](https://arxiv.org/abs/2305.16291).

