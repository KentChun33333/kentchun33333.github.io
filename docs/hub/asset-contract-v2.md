# Asset contract v2 — design proposal

Status: proposed; this document does not migrate the live catalogue.
Scope: the existing GitHub Pages asset library, filters, search, sorting, in-place
viewer, right conversation panel, related assets, and optional offers.

## Dependency review: reduced implementation scope

Review outcome: no new third-party package or hosted service is required, but the
full proposal introduces more schema coupling and migration work than today's
search and sorting need. The scope below governs the first implementation;
remaining sections describe possible future evolution, not mandatory prerequisites.

Keep the current catalogue shape and existing schema version for additive optional
fields. Do not rename `path`, kind/stream values, or `dates.added`, and do not
introduce the full nested v2 record yet. A breaking v2 migration needs a concrete
consumer requirement before proceeding.

| Keep now | Why |
| --- | --- |
| Stable asset IDs and existing source paths | Preserve links and asset identity. |
| Existing title, summary, kind, stream, topics, rights | Already support discovery and current actions. |
| Publication and added dates with evidence | Needed for trustworthy chronological sorting. |
| Optional `curation_rank` | Moves current ordering out of hard-coded asset IDs. |
| One small kind/stream definition map | Generate labels and filter validation once; no registry service or separately versioned taxonomy. |
| Existing Python builder and validator | Validate dates and derive consistent JSON/HTML using standard-library tools. |
| Existing browser search and sort | No framework, search service, or extra network index required at this size. |
| Existing SQLite export | Preserve existing consumers and history; frontend does not query it. |

Defer metadata revision counters and metadata-updated timestamps (Git already
records edits), topic/audience registries, required language tags, lifecycle state
machines, route-alias migration, nested source/action/capability models, separate
viewer manifests, extension namespaces, bundle hashes, deployment receipt ingestion,
full-text indexes, and per-asset authoring files. Retain existing optional data;
deferral is not permission to delete any asset or existing feature.

Dependency direction stays one-way:

```text
catalogue + existing source files → Python build → HTML + catalogue JSON
                                             └→ SQLite export
browser → static HTML / JSON / selected asset
Git history → optional date import → persisted catalogue dates
```

Git is needed only to import upload estimates, not to render or sort the website.
Normal builds consume persisted dates and do not rescan history. Python is build
and validation tooling; Node is used by existing interaction tests. Neither runs
on GitHub Pages. SQLite is a Python-standard-library export, not a database server.
The current build preserves revision observations from the existing export, so it
is not fully stateless: keep that history when rebuilding rather than claiming
that deleting the database has no effect. Browser rendering stays independent of
SQLite. No new package, backend, CMS, queue, authentication service, or cloud API
is needed for this work. Original embedded assets may have their own dependencies;
this review covers the library contract and tooling, not every preserved demo.

First delivery should therefore be additive: shared filter definitions, explicit
curation rank, date normalization/display rules, and matching search/sort checks.
Do not require a multi-store schema migration just to add these UI capabilities.

## Implemented additive discovery

The opt-in discovery feature is implemented without requiring the full v2
migration. See [generator contract](asset-discovery.md) and
[metadata template](asset-metadata.example.json). `hub-src/discovery.json` controls
scan roots and required metadata; new tagged HTML joins the same build pipeline.
Central records remain authoritative for existing curated assets. Deployment
continues through the existing build/publish process, with no new runtime service.

## Core decision

Give each logical asset one stable identity and one authoritative metadata record.
Keep its original files separate from its discovery metadata. Generate one public
read model for the web, JSON consumers, and SQLite queries. UI components consume
that read model; they do not infer dates, types, permissions, or viewer behavior.

```text
Original HTML / Markdown / images / supporting files
               +
Authoritative metadata + taxonomy + relations + offers
               ↓
Validate → resolve evidence → derive public records
               ↓
Static cards / JSON search index / SQLite / viewer manifest
               ↓
Search → filter → sort → open asset → conversation or purchase
```

A missing library listing does not make a publicly hosted source file private.
Unlisted and archived assets retain their files and stable URLs. Private source
files require a separate private storage system outside this public repository.

## Record structure

The collection envelope contains `schema_version: 2`, `taxonomy_version`, assets,
relations, and offers. Version 2 is a migration boundary, not just a new label on
existing records. Unknown major versions fail validation. Optional extensions
belong under a namespaced `extensions` object and cannot override core behavior.

| Field | Contract and ownership |
| --- | --- |
| `id` | Required immutable lowercase identifier; stable across path, title, and version changes. Editor assigns once. |
| `revision` | Positive metadata revision, advanced by explicit metadata changes; builds never increment it. |
| `title`, `summary` | Required plain text, nonempty; no embedded HTML. Summary describes the actual artifact. |
| `aliases` | Optional former titles and common alternate names for search, distinct from route aliases. |
| `kind` | One taxonomy ID: research, demo, article, skill, tool, protocol. |
| `stream` | One primary taxonomy ID: build, research, publish. |
| `topics`, `audiences` | Unique arrays of registered IDs. Topics may grow through registry edits. |
| `language` | Explicit language tag, with `und` for unknown; never guessed from a filename. |
| `status` | Separate lifecycle (`active`, `archived`, `superseded`) and editorial maturity label. |
| `listing` | `listed` or `unlisted`; controls discovery, not source access. |
| `source` | Current entry path, media type, viewer mode, supporting-file roots, and version label. |
| `route_aliases` | Previous detail routes mapped to the stable ID; never rewrite original asset URLs. |
| `dates` | Named date records with precision, evidence, and verification method. See below. |
| `curation` | Optional numeric rank; lower ranks appear first. No hard-coded IDs in frontend code. |
| `media` | Optional thumbnail and gallery references with alt text and display order. |
| `rights` | Required rights statement; optional license reference. Unknown reuse rights remain unknown. |
| `actions` | Conversation eligibility, download references, and linked offer IDs; no executable scripts. |
| `extensions` | Optional namespaced future metadata; ignored safely by current consumers. |

V2 starts with the existing collection and enum mappings. A taxonomy registry owns
IDs, labels, icons, synonyms, and display order. This generates sidebar buttons,
filter validation, and facet labels, eliminating the separate hard-coded type
lists in the current Python builder and JavaScript.

`source.viewer` is explicit: `html-frame`, `markdown-reader`, or `download`.
The builder checks compatibility with media type. Frame permissions are selected
from reviewed viewer profiles, never arbitrary metadata-supplied sandbox strings.
Each self-contained research HTML stays independently usable at its original URL.

Required core fields: id, revision, title, summary, kind, stream, language, status,
listing, source, dates, rights. Arrays default empty; unknown dates are omitted.
Derived hashes, resolved URLs, search tokens, and counts are never hand-authored.

## Dates: meaning before convenience

Each date is a record:

```json
{
  "value": "2026-09-03T14:55:51Z",
  "precision": "second",
  "method": "git_first_add",
  "evidence": {
    "commit": "960a36adfc169832add8abe77ca51d1bc1d36e77",
    "path": "ai-research-insights/synthetic-distillation-flywheel-explained.html"
  }
}
```

| Date key | Meaning | What changes it |
| --- | --- | --- |
| `published` | Original public publication, when supported by evidence | Explicit correction of publication evidence |
| `uploaded` | First upload of the logical asset to this site | Normally immutable; correction with evidence |
| `updated` | Latest substantive content revision | Explicit content release; not cosmetic CSS edits |
| `metadata_updated` | Latest metadata edit | Authoring operation; never used for content sorting |

Allowed methods: `source_metadata`, `deployment_receipt`, `git_first_add`, and
`editorial`. Each method requires its relevant evidence (source locator, deployment
identifier, commit/path, or editorial note). Git first-add uses the committer time
of the exact original entry path and is labelled an upload estimate, not an exact
remote push time. Local filesystem dates and build timestamps are invalid sources.

Preserve publication dates with their original precision. A day-only value is
`YYYY-MM-DD` with `precision: day`; do not invent midnight as its observed time.
Second-precision values require an offset and normalize to UTC for comparison.
Display date-only values unchanged; display timestamps in a consistent declared
site timezone (Asia/Singapore initially). This avoids shifting an August 2 local
publication into August 1 when showing a UTC date substring.

For sorting only, derive a common integer Unix-millisecond key for both calendar
dates and timestamps. Interpret date-only values at the start of their day in the
declared site timezone, recording this as a comparison convention, not greater
precision. Equal keys use deterministic tie-breakers. Missing dates stay null.
Publication, upload, and substantive update need not be monotonically ordered:
an imported article can predate this site by years. Suspicious sequences trigger
review warnings instead of silently rewriting dates.

The existing `dates.added` is migrated to `dates.uploaded`, retaining evidence.
For current research and demos, use the first-add commit as the initial estimate.
After migration, renaming or replacing the entry file does not reset an asset's
first upload. A newly versioned file changes the source version and optionally
`updated`; an independently meaningful new artifact receives a new ID.

Exact upload times can later come from a deployment receipt matched to asset ID
and content hash. Receipt ingestion fills missing evidence or explicitly upgrades
an estimate; it never stamps every asset on each deployment.

## Derived public read model

Every asset projection includes the following calculated fields:

- `urls`: detail URL, original source URL, safe viewer URL, and route aliases.
- `search`: normalized title, aliases, summary, topic labels/synonyms and keywords.
- `sort`: curated rank, publication-or-upload key, upload key, update key, stable ID.
- `display_date`: selected date value, label, precision, timezone and provenance hint.
- `capabilities`: open, read, download, conversation, and buy eligibility.
- `media`: resolved image URLs, alt text, order, and content fingerprints.
- `source_digest`: hash of the current entry; supporting file changes may contribute
  to a separately specified bundle digest when version tracking needs it.

The JSON index and SQLite projection come from the same normalized records.
The browser must not fetch every original HTML file to extract metadata.
Original research bodies remain outside the initial lightweight search payload.
An optional full-text index can be generated separately later with chunk IDs and
source locations, without changing identity or date semantics.

SQLite retains assets, relations, offers, media, and source inventory. Evolve the
date table to `(asset_id, kind, value, precision, method, evidence_json)` and add
indexed derived sort keys. Revision observations remain a separate history of
hashes seen by the builder. A schema migration records its version and executes
in one transaction; a metadata export must never discard prior revision history.

## UI behavior contract

| UI function | Data used | Defined behavior |
| --- | --- | --- |
| Search | title, aliases, summary, topics, keywords | Unicode NFKC and locale-independent lowercase; whitespace tokens AND across fields. Empty query matches all. |
| Asset types | taxonomy + kind | One selected type; default All. Labels/icons generated from registry. |
| Workstreams | taxonomy + stream | AND with kind and search. |
| Result count | matching listed active assets | Count after filtering, before pagination; same collection as cards. |
| Newest / Oldest | published, otherwise uploaded | Same effective date shown on the card; never substitute metadata update time. |
| Recently uploaded | uploaded only | Card switches to Uploaded date; unknown uploads last. |
| Curated | curation rank | Ascending rank, unranked last, then stable ID. |
| Asset open | source + viewer profile + URLs | In-place viewer retains filters, sorting, scroll state, and draft. |
| Related work | validated relations | Stable IDs resolve links; missing targets fail build. |
| Conversation | ID + title + capability | Preselect current asset; source URL included in brief. |
| Buy | linked available offer | Render only if price, currency, license, delivery, checkout pass offer validation. |
| Images | media references | Preserve original files; missing decorative preview degrades to text card. |

Search normalization must use a shared set of fixtures in Python and JavaScript,
including accented text and Chinese text. V2 retains literal matching within
normalized fields; stemming, fuzzy matching, and language segmentation are later
explicit search-version changes. Query input is never interpreted as HTML or regex.

The pipeline is: eligible assets → query/type/stream predicates → sort → page or
render. Null date keys sort last in both directions. Chronological ties use
curation rank then ID; stable IDs prevent order changing after metadata reordering.
Existing curated order is migrated to explicit ranks to preserve today's homepage.
Changing sort never clears search or filters. Changing query, filters, or sort
resets pagination if pagination is introduced. Reset all clears filters and returns
to Curated. Default sorting stays Curated unless explicitly changed as a product
setting. Relevance ranking would be a separately named mode, never secretly
replacing a user's chronological order.

URL contract remains `q`, `kind`, `stream`, `sort`, `asset`. Existing `newest`,
`oldest`, `added`, and curated links keep working; labels can say Recently uploaded
while `added` remains the compatibility token. Unknown values fall back safely;
known legacy taxonomy values map to new IDs. Back/Forward restores the complete
state. Drawer opening is ephemeral UI state; drafts and private input do not enter
URLs. No cookie or account is needed for discovery.

The count row is the only sort control. Date labels show the active sort meaning:
Published/Uploaded for chronological modes, Uploaded for upload mode. Unknown
dates say Date not recorded. Detailed evidence is available through a tooltip or
asset detail disclosure rather than repeated prose on every card.

## Metadata management and validation

1. Register the existing source path and stable ID; never move original content
   just to satisfy the catalogue.
2. Import candidate source metadata and Git evidence into a reviewable diff.
   Importers update missing or previously machine-derived values only; explicitly
   reviewed editorial metadata takes precedence.
3. Validate structure, controlled vocabulary, cross-record references, dates,
   evidence, paths, image references, source/viewer compatibility and offers.
4. Derive outputs deterministically in a staging directory. Validate those outputs
   before replacing the published files as a complete set.
5. Commit source metadata and generated outputs together. Schema changes include
   a migration and compatibility tests. Roll back using a prior consistent commit.

Build errors: duplicate IDs, missing required text, unknown enums, path traversal,
missing entry, invalid timestamps, missing date evidence, broken relation/offer
IDs, route alias collisions, incompatible viewer mode, invalid public offer.
Warnings: unknown dates, missing optional thumbnail, unusually old upload estimate,
suspect event ordering, superseded asset without replacement. Unknown optional
metadata is never invented to make a warning disappear.

Ownership: editors own titles, summaries, topics, rights, ranks and release dates;
importers propose evidence; build tools own hashes, projections and search indexes;
UI owns query state only. Keep publication lifecycle separate from private storage.

Initially keep a single `hub-src/catalog.json` to fit the current builder. At larger
scale, split authoring into `hub-src/assets/<id>.json` plus taxonomy/relations/offers;
compile the same envelope for consumers. This changes editing granularity, not the
public contract. A database admin UI or external CMS is unnecessary for the current
size and remains optional behind the same import/validation interface.

## Migration from the current implementation

1. Add a machine-readable v2 schema and taxonomy registry beside v1. Supply a
   one-way converter and fixture validation; leave live v1 output intact initially.
2. Preserve IDs, source paths, images, offers and relations. Map existing kinds and
   streams, retain maturity text, create curated ranks from today's rendered order,
   and convert date evidence without inventing missing publication dates.
3. Introduce the normalized read model and generate v1 compatibility fields while
   migrating the viewer, filters and sorting. Fix date display to follow the chosen
   sort mode and site timezone; today's static card labels do not yet do that.
4. Migrate SQLite transactionally; compare equivalent JSON/DB/UI values. Export a
   migration report listing missing metadata, date estimates and unchanged sources.
5. Switch UI consumers only after state-restoration and preservation checks pass.
   Keep original URLs and v1 URL parameters indefinitely; retire v1 data fields
   only through a documented later consumer migration.

Acceptance checks: source bytes unchanged; same asset coverage; no lost relations,
media or revisions; deterministic exports; unknown-date ordering; publication vs
upload fallback; same-day/timestamp ties; timezone-boundary display; invalid query
fallback; search/filter/sort combinations; viewer Back/Forward preservation; date
import idempotence; no fabricated dates; no source deletion when unlisting assets.

## Deliberate boundaries

This is a metadata and discovery contract. It does not introduce payments,
authentication, private customer memory, automatic publication of all repository
files, or semantic claims inferred from an embedding. The existing graph stays in
the asset layer and is exposed only where it serves a concrete asset interaction.
