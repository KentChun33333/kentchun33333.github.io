# Wealth Intelligence Agent — Design Flow

## Core flow

```text
[P1: USER ENTRY]
      |
      | question + topic + sources + lookback + reasoning cap
      v
[CASE MANAGEMENT TABLE]
      |
      | open case / start async run
      v
[P2: DATA-CAPABILITY DISCOVERY]
      |
      | visualise safe aggregates
      | human narrows boundary
      | right panel: prompt / quick QA
      v
[ASYNC MANAGER RUN]
      |
      +------------------------------+
      |                              |
      v                              v
[CASE TABLE: P2 UPDATED]        [P3: CROSS-SOURCE INSIGHT]
      |                              |
      | open updated P2               | report + evidence + actions
      |                              | right panel: Finetune / Done
      |                              v
      |                       [ASYNC MANAGER RUN]
      |                              |
      +---------------+--------------+
                      |
             +--------+---------+
             |                  |
             v                  v
     [CASE TABLE: P3 UPDATED] [FROZEN CASE]
             |                  |
             | reopen P3        | immutable report version
             +------------------+
```

## Page responsibilities

### Page 1 — User entry and Case Management

Page 1 creates and lists cases. The table is the return point for every asynchronous action. It is also the audit surface: a user can see who ran what, when it ran, which sources and lookback were used, and which Summary Report version is current.

### Page 2 — Data-capability discovery

Page 2 answers “what can the connected data support?” before the system claims an insight. Visuals are capability maps and aggregated previews, not final recommendations. The human uses them to narrow:

- source and aggregation boundary;
- relationship and evidence types;
- population, jurisdiction, and lookback;
- chain depth, confidence, and deduplication;
- exceptions and non-inference rules; and
- required output views.

The agent can explain, compare, and propose a boundary. The human confirms the boundary through the case event before the system moves to Page 3.

### Page 3 — Cross-source insight

Page 3 renders the approved boundary as a Summary Report. It should show the cross-source join, the evidence that supports each finding, uncertainty, and the human decision required next. It should not imply that an inferred link is a verified fact.

## Recursive loops

### Page 2 loop: refine the search boundary

The right sliding panel accepts a short human prompt such as “include trust beneficiaries but exclude shared addresses.” The Async Manager records it as a `P2 / QA` or `P2 / FINETUNE` event, runs against the current case version, and returns to Case Management. The case row then exposes “Open updated Page 2” and “Continue to Page 3”.

### Page 3 loop: refine or freeze the report

The Page 3 right panel accepts a human correction such as “separate inferred links from confirmed links.” **Finetune** creates a new `P3 / FINETUNE` event and report version, then returns to Case Management. **Done** creates a `P3 / DONE` event and changes the case to `FROZEN`; the final report and all metadata become immutable.

## Source capability layers

```text
CRM     : profile -> client -> portfolio       (no raw transaction level)
FileNet : document type -> client -> portfolio (no unrestricted key-value level)
HELIOS  : case type -> client -> portfolio     (no underlying detail level)
T24     : client -> account relationship       (transaction detail only if separately authorised)
```

Each visual on Page 2 must declare its source, aggregation level, coverage, timestamp, and exclusions. This makes the visualisation a governed capability explanation rather than an unexplained chart.

## Case event metadata

```text
case_id | event_id | parent_event_id | report_version_id
actor   | timestamp | stage            | action
topic   | question  | lookback_period  | selected_sources
boundary | human_hypothesis | guardrails | summary_report
status  | evidence_manifest | confidence_summary
```

The metadata is shown in the Case Management table and retained with every Summary Report. A new async run appends an event; it never replaces history.

## Technical feasibility decision

The architecture is feasible as an asynchronous orchestration system if the first release treats Page 2 outputs as aggregate capability metadata and Page 3 outputs as evidence-linked report versions. The main implementation risks are source permission boundaries, evidence lineage, idempotent retries, and preventing inferred relationships from being rendered as facts.

The three scenario decisions are documented in `s1.html`, `s2.html`, and `s3.html`.
