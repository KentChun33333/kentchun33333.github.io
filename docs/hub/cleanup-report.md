# Unused-file cleanup — 2026-09-04

Removed four unused legacy theme files: `css/additional.css`, `css/medium.css`,
`css/toggle.css`, and `js/mediumish.js`. None of their filenames appeared in any
other existing tracked file, including archived homepages, scripts, and styles.

Removed 29 existing Finder `.DS_Store` files and five generated Python bytecode
cache files. Python source files remain unchanged. Added ignore rules for local
metadata and Python caches. The two already-missing `openmemo` metadata files,
and all pre-existing missing `openmemo` content, were left unstaged.

No content assets, images, fonts, Markdown sources, HTML pages, demos, research,
or catalogue records were removed. Archived homepages and their referenced
styles/scripts remain available at their original paths. Generated hub detail
pages and compatibility routes remain useful for direct links and fallback use.

The unreferenced `upload-test/Install Notion Calendar.app` installer bundle is a
possible future cleanup candidate. It is retained because lack of website links
alone does not establish that an uploaded downloadable file is disposable.

This cleanup follows the earlier preservation report; its zero-removal statement
records the initial refactor, before this separate authorized cleanup.
