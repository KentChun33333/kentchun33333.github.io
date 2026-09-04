# Automatic artifact discovery

Implemented as build-time discovery, with no new packages, service, or database
server. The browser receives the resulting catalogue through its normal static
files. It does not scan repository directories at runtime.

## Generator contract

1. Generate the HTML in a folder listed in `hub-src/discovery.json`. Add another
   repository-relative folder there when introducing a new artifact collection.
2. Put exactly one `<script type="application/json" id="asset-metadata">` block in
   the HTML head. Its JSON must follow `asset-metadata.example.json` beside this
   document. The path comes from the file itself, not its metadata.
3. Set `visibility: public` to opt into the library. Use `unlisted` to retain a
   source without listing it. Files without the block are ignored by discovery.
4. Run `python3 scripts/build_hub.py`, then `python3 scripts/validate_hub.py`.
   Commit the artifact and generated outputs; publish through the existing Hugo
   branch workflow. Refresh the library after deployment.

```html
<script type="application/json" id="asset-metadata">
{
  "schema_version": 1,
  "id": "my-new-demo",
  "title": "My new demo",
  "summary": "Explore the workflow and compare its outcomes.",
  "kind": "Demo",
  "stream": "Build",
  "topics": ["Agent workflows"],
  "status": "Interactive prototype",
  "visibility": "public",
  "rights": "All rights reserved. Contact the author for reuse.",
  "dates": {}
}
</script>
```

Dates can contain `published` and/or `added`, each with `at` (ISO timestamp with
timezone) and `source` (evidence). Use actual publication evidence or a recorded
first-upload commit, not generation/build time. An empty object is allowed when
unknown; undated artifacts still appear and sort after dated ones. Embedded added
dates are author-owned: the existing central-catalogue date importer does not write
HTML. Supply date evidence in the generated contract when known. UTC and offset
timestamps normalize consistently for existing sorting.

The generator must emit valid JSON, escaping `<` as `\u003c` within JSON strings
so user text containing a closing script tag cannot terminate the metadata block.
Metadata contains plain text and data only; discovery never executes JavaScript.

## Ownership and conflict rules

Central `hub-src/catalog.json` owns existing curated assets. When embedded metadata
uses both the same ID and same path, the central record wins as a complete record;
fields are not merged unpredictably. Updating such an asset requires editing its
central record. New artifacts need no central catalogue entry.

A reused ID at a different path, or a different ID on a centrally registered path,
is an error. Discovered IDs must also be unique. Invalid opted-in metadata stops
the build before generated outputs are written and reports the file and problem.
Changing an embedded ID creates a new identity; retain IDs across ordinary edits.

`required`, supported kinds/streams, the marker ID, and folder scope are recorded
in `hub-src/discovery.json`. Required fields must be present even when an allowed
value is empty (`dates: {}`). Field semantics are checked by the standard-library
validator. Adding an entirely new asset kind still requires updating the library's
filter vocabulary; this feature discovers assets within the supported kinds, not
arbitrary new UI types. Keep those lists aligned until shared filter generation
is implemented.

The builder derives source URLs, fingerprints, detail pages and catalogue records.
The existing cards and viewer consume them, including search text and date-sort
attributes. Markdown and unmarked legacy HTML retain their current curated path.
Existing related assets and offers continue to use stable IDs in the central
catalogue. No automatic commerce or relationships are inferred.

This does not install a file watcher or GitHub Actions workflow. Automatic means
inclusion on the normal build, not immediate publication when a local file appears.
Original HTML and supporting files are never rewritten by discovery. Unlisting
can remove a generated detail listing through existing build behavior; it does not
delete the source artifact or make its original public URL private.

## Verification

`python3 scripts/test_asset_discovery.py` checks opting in, omission, invalid
metadata, duplicate identity, central precedence, dates, source preservation, and
an isolated end-to-end build into HTML, JSON, and SQLite.
