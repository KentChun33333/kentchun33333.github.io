# Wealth Intelligence Agent v3 — Product and Interaction Design

## Purpose

`index_v3.html` is a professional, single-file, three-stage demo for relationship-driven wealth intelligence. It blends the AURA entry experience with the richer configuration and visualization patterns from the supplied Client Grouping and Next-Generation prototypes, while retaining the established visual language of `index-v2.html`.

The primary audience is a relationship manager, investment specialist, or product stakeholder who needs to understand how a natural-language question becomes governed evidence and then an actionable client insight.

## Design thesis

The demo uses a restrained institutional interface for task framing and evidence navigation, then transitions into a navy, gold, and ivory private-banking surface for the final insight. Red remains the workflow accent throughout, matching `index-v2.html` and keeping state changes, selections, and high-priority findings visually coherent.

The experience is a working surface rather than a presentation page: each viewport exposes the active task and its outputs without requiring introductory scrolling.

## Three-stage journey

### 1. Frame the question

The first page distils `user-input/AuraHomeFinal.html`:

- Select CRM, FileNet, T24, and HELIOS as governed data sources.
- Enter or load an intelligence question.
- Attach a supporting document through a deliberately small paperclip control. Upload is optional and does not compete with the main task.
- Select agent reasoning capability: Focused, Connected, or Deep.
- Use three suggested analysis patterns drawn from the supplied prototypes.

The default request uses CRM and FileNet with Connected reasoning because this is the smallest coherent setup for the demonstrated shared-relationship scenario.

### 2. Navigate the evidence

The second page is both a database navigator and a visualization configuration workspace. It is intentionally not a generic loading screen.

- The left rail explains what each selected database contributes and allows source-specific inspection.
- The central workspace previews the connected relationship graph and surfaces early structural and data-quality insights.
- The right rail treats visualization components as reusable analytical assets. Users choose the views that should be carried into the final scenario.
- Chain depth, confidence threshold, and client scope tune the relationship analysis.

The visualization asset set is distilled from `user-input/CGIntermediate.html`: network map, group ranking, relationship flow, AUM concentration, evolution timeline, and bridge-client analysis.

### 3. Review the insight

The first complete scenario is **Shared Entities + Direct Relationships**. It was selected because it best demonstrates the combined value of structured CRM data, document evidence, graph navigation, and reusable visualization assets.

The result page includes:

- executive relationship metrics;
- an interactive cluster map;
- node-level evidence and confidence;
- ranked client groups;
- an RM-oriented coverage opportunity and a control signal; and
- a downloadable illustrative brief.

Only one scenario is fully implemented in v3. `user-input/NGIntermediate.html` is retained as the blueprint for a later Next-Generation Opportunity scenario. The thematic-investment prompt is retained as the third future scenario pattern.

## Content model

| Layer | Primary object | User decision | Output |
| --- | --- | --- | --- |
| Request | Question + sources | What should the agent investigate? | Analysis scope |
| Evidence | Databases + graph + visual assets | What evidence and analytical lenses should be used? | Scenario configuration |
| Insight | Client group + relationships | What deserves RM attention? | Evidence-backed action |

## Interaction rules

- Progress navigation allows return to completed stages; future stages remain gated by the main action.
- At least one data source and one visualization asset are required.
- Source selection on Page 1 determines availability in the Page 2 navigator.
- Database selection updates the central evidence summary and graph context.
- Visualization assets are multi-select and their count is passed into the final configuration summary.
- Chain depth and confidence update both the preview and result metadata.
- Result graph nodes update the evidence panel without leaving the page.
- The downloadable brief is generated locally and contains demo-only data.

## Accessibility and responsive behavior

- Native buttons, labels, inputs, and selects are used for keyboard and assistive-technology support.
- Selected states are expressed through color plus border, fill, and text changes.
- Main interface text remains at 14–16 px; smaller type is limited to secondary metadata.
- Desktop uses a three-column evidence workspace. Tablet collapses the configuration rail below the navigator; mobile becomes a single-column flow.
- The journey indicator simplifies on narrow screens while retaining numeric progress.

## Source provenance

The original inputs are preserved unchanged under `wealthy_data_insight/user-input/`:

- `AuraHomeFinal.html` — entry, database selection, query, upload, and suggested-query patterns.
- `CGIntermediate.html` — shared-entity configuration, relationship logic, visualization assets, and generated-output structure.
- `NGIntermediate.html` — next-generation profiling and readiness-analysis blueprint for future expansion.

The v3 implementation also inherits the typography, red workflow accent, neutral task surfaces, and navy/gold result language established by `index-v2.html`.

## Future scenario expansion

The next increment should reuse the same three-stage shell and swap only the scenario schema, configuration controls, and result composition:

1. Next-Generation Opportunity — readiness scoring, family graph, projected transfer, and RM approach.
2. Thematic Investment Demand — meeting-derived themes, client demand clusters, suitability matching, and opportunity prioritisation.

This keeps data-source selection and the visualization asset library stable while allowing scenario-specific intelligence modules to evolve independently.
