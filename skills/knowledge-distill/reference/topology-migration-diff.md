# Topology: Architecture Migration & Delta Distillation

Use this flow when the input represents a migration, refactoring, version upgrade (e.g. v1 to v2), framework transition, or side-by-side paradigm comparison.

## Reasoning Topology

```text
legacy state (v1)
  -> driver for change
  -> migration vector & strategy
  -> contract diff (deprecated vs replacement)
  -> state/data migration & compatibility
  -> failure modes & fallback gates
  -> verified target state (v2)
  -> reusable migration lessons
```

## Required Analysis Emphasis

- **Legacy Contract & Constraints**: What baseline assumptions existed in the old architecture.
- **Drivers & Invalidation of v1**: Why the legacy pattern broke or failed to scale.
- **Contract Transition Mapping**:
  ```markdown
  | Legacy Contract (v1) | Modern Contract (v2) | Breaking Changes | Compatibility / Adapter Strategy | Source IDs |
  |---|---|---|---|---|
  ```
- **State & Data Invariants**: How existing records, state machines, and caches transition without data loss.
- **Rollout / Fallback Gates**: Strangler fig pattern, dual-write verification, canary routing, or rollback triggers.
- **Spec Drift & Deprecations**: Documented features dropped, changed default configs, or renamed symbols.

## Stacking Diagram Format

Use the standard 3-column format with migration transition clearly mapped:

```text
[Legacy Contract / v1]        -->   [Adapter / Migration Bridge]   -->   [Target State / v2]
======================              ============================         ===================
Legacy Token, Auth Header     -->   Auth Token Converter v1->v2   -->   JWT Session Lease
                                                                        (Source: source-001, source-003)
```

## Output Preferences

Add or emphasize:

- `analysis/contract-diff.md`
- `analysis/migration-risks.md`
- `knowledge/migration-guide.md`
- `knowledge/compatibility-matrix.md`
- `knowledge/rollback-runbook.md`

## Invalidation Tests

- A migration plan is invalid if breaking schema changes lack backfill/dual-write strategies.
- A compatibility claim is weak if rollback fails to preserve dirty state generated during the transition.
