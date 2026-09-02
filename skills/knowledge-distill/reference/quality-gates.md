# Quality Gates

## Evidence Rules

1. Never invent missing facts.
2. Every major claim must trace back to cooked source IDs.
3. Terminology must reflect actual usage.
4. Charts are visual companions, not primary evidence.
   - **Markdown Knowledge Artifacts**: **Mermaid is strictly forbidden**; use ASCII-style stacking diagrams. Workflow diagrams must use a stacked layout with input data contracts on the left, core modules in the center, and output data contracts on the right (`[Input Data Contract] --> [Core Module] --> [Output Data Contract]`).
   - **Interactive Web Insight Artifacts (HTML)**: Use semantic HTML/CSS cards, responsive 3-column layouts, and interactive visual flow engines (see [web-insight-artifact.md](web-insight-artifact.md)).
5. Contradictions must be preserved.
6. Low confidence must be marked explicitly.
7. Parser uncertainty must be visible.
8. Final knowledge files must distinguish evidence, inference, recommendation, and open questions.
9. Recommendations must be labeled separately from demonstrated results.
10. Related-work candidates must not be presented as validated winners unless the source evaluates them.
11. Repeated concepts must have exactly one canonical explanation. The knowledge stage must be heavily compressed and deduplicated while maintaining high-coverage cross-references.
12. Every major practical recommendation should include an invalidation test.

## Automated Verification

Before completing distillation, run the automated quality guardian:

```bash
python3 skills/knowledge-distill/scripts/engine.py audit-all [project_dir] --write
```

This verifies:
- Folder contract completeness (`data-raw/`, `data-cooked/`, `analysis/`, `knowledge/`).
- Provenance headers across all cooked files.
- Zero hallucinated source ID citations.
- Absence of forbidden mermaid blocks in markdown.
- 7-dimension IQ scoring report generation.
- Generation of `knowledge/manifest.json`.

## IQ-Style Review Dimensions

Use these dimensions when reviewing output quality:

| Dimension | What to evaluate |
|---|---|
| Structure reasoning | Does the output expose workflow, mechanisms, dependencies, and causal chain? |
| Output duplication | Does repetition improve clarity or dilute information density? |
| Quality vs output size | Is the artifact set proportional to useful payload? |
| Reasoning depth quality | Does it go beyond summary into mechanisms, failure modes, tradeoffs, and second-order effects? |
| Evidence of boundaries | Does it mark what is demonstrated, inferred, recommended, unverified, or out of scope? |
| Evidence of invalidation | Does it state what would falsify or weaken a recommendation? |
| Practical transfer | Can the user apply it with a scorecard, workflow, or example? |

## Completion Checklist

- `data-cooked/source-index.md` exists.
- Every raw source has a source ID.
- Every cooked file has provenance.
- `analysis/flow.md` exists and leads the reasoning.
- `analysis/dependency.md` exists.
- `analysis/terminology.md` exists.
- `analysis/evidence-map.md` exists.
- `analysis/boundaries-and-invalidation.md` exists when practical recommendations are made.
- `knowledge/read-order.md` exists for multi-file outputs.
- `knowledge/big-picture.md` exists.
- `knowledge/executive-summary.md` exists.
- `knowledge/manifest.json` exists for agent consumers.
- Agent/harness outputs include activation/adherence metrics or templates.
- Repeated concepts have one canonical explanation.
- Open questions and low-confidence areas are clearly marked.
- Skill evolution caused by feedback is recorded in a ledger.


