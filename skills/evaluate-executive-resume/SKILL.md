---
name: evaluate-executive-resume
description: Compare one or more tailored resumes against a source resume and target job description, then score role fit, professional expert VP/director tone, executive scope, evidence credibility, ATS coverage, and presentation quality. Use for resume selection, seniority calibration, claim-inflation checks, job-specific gap analysis, or an iterative evaluate-rewrite-rescore loop for director, VP, FVP, SVP, head-of, principal, and senior expert roles.
---

# Evaluate Executive Resume

Evaluate senior resumes as evidence-backed positioning documents, not keyword collections. Reward credible scope, decisions, outcomes, and role fit. Penalize unsupported seniority, invented technologies, vague executive language, and claims that exceed the source evidence.

Read [references/rubric.md](references/rubric.md) before scoring.

## Required Inputs

Collect, or explicitly mark as missing:

1. Source resume or career evidence.
2. Target job description.
3. One or more tailored resume variants.
4. Optional rendered PDF for layout review.

Treat the source resume as the default truth boundary. A tailored claim may add framing, but not new facts, technologies, scope, relationships, or outcomes unless the user supplies evidence.

## Evaluation Loop

### 1. Decompose the role

Classify the target as one dominant archetype:

- Expert VP/director: senior individual contributor or player-coach; emphasize depth, judgment, delivery, and stakeholder influence.
- Enterprise VP/director: emphasize portfolio ownership, operating cadence, people leadership, budget, governance, adoption, and cross-functional execution.
- Research/innovation executive: emphasize external partnerships, research portfolio, commercialisation, research-to-production mechanisms, and value measurement.

Extract must-haves, differentiators, title signals, and explicit evidence requirements from the job description.

### 2. Build an evidence ledger

Atomize material claims in each tailored resume and label them:

- E2 - directly supported by the source.
- E1 - defensible reframing or reasonable inference.
- E0 - unsupported, contradicted, or materially broader than the source.

Flag title inflation, duration inflation, people or regional scope inflation, technology invention, and causal overclaiming separately. Do not average credibility risks away.

### 3. Score each variant

Use the 100-point rubric. Provide dimension scores, total score, confidence, and a one-line verdict.

Apply hard gates:

- No variant can be "ready" with a material E0 claim in the headline, summary, current role, degree, employer, title, or quantified impact.
- Cap readiness at 79 when more than two material E0 claims remain.
- Cap readiness at 74 when the resume targets a higher title than the candidate currently holds without clearly showing equivalent scope.
- Cap readiness at 69 when the target's core mandate is mostly absent from the source evidence.

### 4. Test the tone

Check whether the language sounds like:

- A credible expert: precise domain nouns, clear mechanisms, bounded claims, technical judgment, measurable outcomes.
- A credible VP/director: ownership of decisions, teams or portfolios, stakeholder level, operating scale, trade-offs, governance, and business outcomes.
- Empty executive theatre: repeated "strategic," "championed," "spearheaded," or "transformation" language without scope, mechanism, or evidence.

Prefer "senior and specific" over "grand and generic."

### 5. Diagnose gaps

Separate findings into:

- Positioning gap: true evidence exists but is buried or poorly framed.
- Evidence gap: the job requires experience not demonstrated by the source.
- Credibility risk: the tailored version asserts an unsupported fact.
- Presentation gap: contact details, hierarchy, density, pagination, grammar, or ATS parsing.

Never recommend wording alone as a fix for an evidence gap. Recommend collecting proof, narrowing the claim, or targeting a closer role.

### 6. Rewrite selectively

If rewriting is requested, revise only failed sections first:

1. Headline and summary.
2. Current-role bullets.
3. Skills or selected achievements.
4. Older roles.

Preserve quantified results and concrete mechanisms. Remove unsupported keywords. Add missing role language only when evidence supports it.

### 7. Rescore and stop

Repeat the evidence audit and scoring after each revision.

Stop when:

- Total score is at least 85.
- Evidence credibility is at least 18/20.
- Role fit is at least 21/25.
- No material E0 claim remains.
- The first half-page communicates target role, scope, two differentiators, and two outcomes.
- PDF review has no clipping, weak hierarchy, or severely unbalanced pagination.

Allow a lower stop threshold only when the target itself is a stretch; label the result "best defensible version," not "ready."

## Output Contract

Return:

1. Ranked comparison table.
2. Professional expert and VP/director tone assessment.
3. Evidence-risk register with exact claims.
4. Target-role gap analysis.
5. Prioritized corrections: critical, important, optional.
6. Final recommendation: submit, revise, or do not use for this role.
7. If iterating, a before/after score and remaining stop-condition failures.

Use exact language from the resume only in short excerpts needed to identify a problem.
