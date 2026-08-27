---
name: semantic-pattern-mining
description: Extract recurring semantic, causal, sequential, and risk patterns from heterogeneous raw text (incident logs, user workflows, trading histories, support tickets) using schema-first normalization, statistical validation, embedding clustering, contrastive mining, and red-team/evaluator loops.
---

# Semantic Pattern Mining

Extract recurring patterns from unstructured, noisy, or sequential logs and documents. Unlike traditional FP-tree itemset mining which requires exact discrete item tokens and ignores order, semantic pattern mining uses LLMs to parse context, embeddings to group variants, and adversarial evaluator loops to prove causal impact and actionability.

## Workflow Diagram

```text
[Input Data Contract]                 [Core Module]                    [Output Data Contract]
=====================                 =============                    ======================
Raw Heterogeneous Cases    -->     Normalize Schema        -->    Canonical JSON/Structured Cases
(Alerts, logs, tickets)           (LLM Semantic Parser)           (Normalized evidence)

Normalized Evidence        -->     Embed & Cluster         -->    Semantic Groups
                                  (Vector/TF-IDF tools)           (Topical subsets)

Semantic Groups            -->     Hypothesis Generation   -->    Proposed Pattern Cards
                                  (LLM Miner Model)               (Draft patterns & conditions)

Proposed Pattern Cards     -->     Contrastive Audit       -->    Refined Pattern Cards
& Success/Failure Labels          (Statistical check)             (With Support & Lift metrics)

Refined Pattern Cards      -->     Red-Team Challenge      -->    Validated/Hardened Rules
                                  (LLM/Evaluator Audit)           (Surviving counterexample check)

Validated/Hardened Rules   -->     Commit to Store         -->    Active Pattern Bank
                                  (Pattern Registry)              (Continuous drift tracking)
```

---

## Core Execution Loops

### 1. Discover & Cook Raw Cases
Collect the corpus of heterogeneous cases. Identify the outcome metric (e.g., success/failure, SLA met/breached, trade win/loss). Assign a unique ID to each raw event case and compile them into a source index.

### 2. Schema-First Normalization
Do not mine raw text directly. Instruct the LLM to parse raw transactions into a structured JSON schema mapping actors, triggers, actions, states, and outcomes.
- **Rule**: If temporal order matters, extract events as an ordered array of normalized state-transitions (e.g., `["State A", "Event X", "State B"]`).

### 3. Embed & Cluster
Generate vector embeddings on the raw text or the normalized schemas. Use clustering algorithms (e.g., HDBSCAN, K-Means) or semantic topic modeling (e.g., BERTopic) to partition cases into topical subsets. This discovers semantic co-occurrences beyond exact keyword matches.

### 4. Propose Candidate Patterns (Miner)
For each cluster, prompt the LLM Miner to discover candidate pattern rules. The miner must draft rules linking context, decisions, and constraints to the observed outcome.

### 5. Contrastive Validation & Statistical Audit
Run statistical tests across the database of all cases to calculate support and lift:
- **Support**: How often does the proposed pattern context occur?
- **Confidence/Precision**: When the pattern occurs, how often does the outcome follow?
- **Lift**: Does the pattern occur significantly more in failure cases than success cases? (Or vice versa).
- **Rule**: Reject patterns with support below a defined threshold (e.g., < 3 cases or < 5% of the cluster size) unless manually flagged as a critical edge case.

### 6. Red-Team Challenge (Evaluator Loop)
Submit the draft pattern to a separate adversarial LLM instance (the Red-Team Auditor) tasked with finding counterexamples or alternate explanations:
- Retrieve cases matching the pattern context that resulted in the *opposite* outcome.
- Force the miner to narrow down the conditions (e.g., adding constraints) until the pattern is statistically robust.

### 7. Register to Pattern Bank
Convert the validated pattern into a structured **Pattern Card** and save it to the project registry.

---

## Structured Prompt Templates

### Template A: The Miner (Hypothesis Generator)

```text
You are a Semantic Pattern Miner. Your goal is to analyze the provided set of structured cases and discover recurring patterns that correlate with the final outcome.

INPUT CASES:
{input_cases_json}

INSTRUCTIONS:
1. Examine the cases and group them by semantic similarity of triggers, actions, and constraints.
2. Formulate hypotheses linking specific sequences of events and conditions to the outcome (success/failure).
3. For each candidate pattern, write a Pattern Card containing:
   - Pattern Name: A concise, descriptive title.
   - Definition: The exact chain of triggers, actions, and states that defines this pattern.
   - Required Conditions: The context or constraints under which this pattern is active.
   - Evidence Examples: Reference IDs of cases that match and validate this pattern.
   - Counterexamples: Reference IDs of cases that match the triggers but did NOT lead to the outcome.
   - Primary Outcome: The typical result of this pattern.
   - Actionability: What concrete intervention can prevent the failure or replicate the success.
   - Confidence Score: (1 to 10) based on direct evidence strength.

OUTPUT FORMAT:
Return a JSON array of Pattern Cards.
```

### Template B: The Red-Team Auditor (Evaluator)

```text
You are an Adversarial Red-Team Evaluator. Your goal is to critique the proposed pattern cards and find weaknesses, ambiguities, or counterexamples.

PROPOSED PATTERNS:
{proposed_patterns_json}

ALL REFERENCE CASES:
{all_cases_json}

INSTRUCTIONS:
For each proposed pattern:
1. Search the full case directory to identify any "leakage" or counterexamples: cases that meet the pattern's "Required Conditions" but resulted in a different outcome.
2. Evaluate the causality: Is the pattern naming a true cause, or is it merely describing a correlational symptom?
3. Check for "empty executive theatre": Reject vague terms (e.g., "lack of alignment", "suboptimal strategy") and force conversion into precise, observable variables (e.g., "SLA breach on step 2", "missing API token verification").
4. Assign a strict validation grade:
   - PASS: The pattern has strong statistical support, zero major counterexamples, and a clear intervention mechanism.
   - REWRITE: The pattern is directional but needs narrower conditions or stricter definitions to filter out counterexamples.
   - REJECT: The pattern is correlational, vague, or lacks sufficient support.

OUTPUT FORMAT:
Provide a critique ledger detailing the validation grade and specific rewriting rules or counterexample case IDs.
```

---

## Quality Gates (The 4 Checks)

Verify that every finalized pattern satisfies all four gates:

| Gate | Check Question | Target Condition for Sign-off |
|---|---|---|
| **1. Semantic Consistency** | Do the evidence examples share the same root cause and context? | No grouping of unrelated failures under a single generic label. |
| **2. Statistical Support** | Does the pattern appear frequently enough? | Must have a minimum support count (e.g., $\ge 3$ cases) and high confidence. |
| **3. Contrastive Power** | Does the pattern distinguish success from failure? | The pattern must yield a high odds ratio (Lift $> 1.5$) comparing failure cases to success cases. |
| **4. Actionability** | Can an engineer, agent, or manager change behavior based on this? | The pattern must specify a concrete recommendation or automated rule to run when the trigger is detected. |

---

## Worked Example: Pattern Card

### Pattern Card: Missing Idempotency in Payment Retries

* **Pattern Name**: `UNGUARDED_RETRY_DUPLICATE_CHARGE`
* **Definition**: A payment API call fails with a network timeout, triggering an automated retry script without sending a unique, persistent idempotency key, resulting in a duplicate transaction on the downstream gateway.
* **Required Conditions**:
  - Payment gateway: Stripe or Adyen
  - Client retry logic: Automated loop
  - Absence of header: `X-Idempotency-Key` or equivalent
* **Evidence Examples**:
  - `case-012`: Stripe gateway timed out, client retried after 2 seconds, customer charged twice.
  - `case-047`: Network glitch during Adyen checkout, client script re-sent payload, dual debit confirmed.
* **Counterexamples (Anti-patterns)**:
  - `case-019`: Checkout timed out, client retried with `X-Idempotency-Key` set to `cart_id`, Stripe returned the cached response of the first attempt (no duplicate charge).
* **Primary Outcome**: High customer friction, increased chargeback risk, SLA breach on transaction processing.
* **Actionability**:
  - Reject payment retry execution if the payload lacks a transaction-specific idempotency token generated from the source cart.
  - Log warning alerts on any retry request missing an idempotency signature.
* **Support**: 5 cases  
* **Confidence/Precision**: 100%  
* **Adversarial Grade**: **PASS** (Audited and hardened against 1 counterexample by verifying that client-side token caching successfully prevents duplication).
