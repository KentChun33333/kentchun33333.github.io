# Topology: Heterogeneous Corpus Input

Use this flow when the input is a mixed bundle of text, PDFs, emails, chats, docs, meeting notes, reports, screenshots, URLs, spreadsheets, or messy exports.

## Reasoning Topology

```text
source clustering
  -> timeline / provenance
  -> actor-intent map
  -> topic and claim extraction
  -> contradiction handling
  -> insight synthesis
  -> decision implications
  -> open questions
```

## Required Analysis Emphasis

- Source provenance: who/what/when/where.
- Clustering by topic, actor, time, and reliability.
- Timeline of events or idea evolution.
- Actors, stakeholders, roles, incentives, and intent.
- Claims versus evidence.
- Contradictions and duplicate statements.
- Signal versus noise.
- Insights, risks, decisions, and follow-up questions.

## Output Preferences

Add or emphasize:

- `analysis/source-clusters.md`
- `analysis/timeline.md`
- `analysis/actor-intent-map.md`
- `analysis/contradictions.md`
- `knowledge/insight-brief.md`
- `knowledge/decision-implications.md`

## Boundary Checks

- Do not treat email/chat claims as verified facts without corroboration.
- Preserve disagreement instead of resolving it prematurely.
- Mark stale sources by date.
- Separate firsthand evidence from forwarded/reported claims.

## Invalidation Tests

- An insight is weak if it depends on one uncorroborated actor.
- A timeline claim is weak if timestamps are missing or inferred.
- A decision recommendation is weak if source reliability is low or contradictory.

