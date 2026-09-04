# Refactor preservation report

- Baseline: 4832 existing files (excluding Git internals and .DS_Store).
- Preserved byte-for-byte at the same path: 4831.
- Authorized replacement: root `index.html`. Its exact prior bytes are retained as `index.previous-nexus.html`.
- Files removed by this refactor: 0.
- Existing nested HTML/Markdown sources inventoried: 740.
- Public catalogue: 56 assets; 8 explicitly described relationships; 3 inquiry-stage offers.
- Image discoverability follow-up: 21 original local images linked from 11 articles, with homepage features for MIT-CSAIL beginnings and the Singapore home-buying story. All original image bytes and paths remain unchanged.
- SQLite rebuild preserved all existing revision observations.
- Original blog, research, demo, skill and Markdown contents were not rewritten.

## Pre-existing worktree state

These changes existed before the refactor and were not reset or restored:

```text
 M index.html
 D openmemo/.DS_Store
 D openmemo/agent-learner/.DS_Store
 D openmemo/agent-learner/output/mercor-skyrl-397b-frontier-agent/analysis/boundaries-and-invalidation.md
 D openmemo/agent-learner/output/mercor-skyrl-397b-frontier-agent/analysis/dependency.md
 D openmemo/agent-learner/output/mercor-skyrl-397b-frontier-agent/analysis/flow.md
 D openmemo/agent-learner/output/mercor-skyrl-397b-frontier-agent/analysis/iq-training-evaluation.md
 D openmemo/agent-learner/output/mercor-skyrl-397b-frontier-agent/data-cooked/source-001.md
 D openmemo/agent-learner/output/mercor-skyrl-397b-frontier-agent/data-cooked/source-index.md
 D openmemo/agent-learner/output/mercor-skyrl-397b-frontier-agent/data-raw/mercor_blog.md
 D openmemo/agent-learner/output/mercor-skyrl-397b-frontier-agent/knowledge/big-picture.md
 D openmemo/agent-learner/output/mercor-skyrl-397b-frontier-agent/knowledge/executive-summary.md
 D openmemo/agent-learner/output/mercor-skyrl-397b-frontier-agent/knowledge/manifest.json
 D openmemo/agent-learner/output/mercor-skyrl-397b-frontier-agent/knowledge/read-order.md
 D openmemo/agent-learner/output/mercor-skyrl-397b-frontier-agent/knowledge/workflow-reference.md
?? css/modern-hub.css
?? index.legacy-hugo.html
?? js/modern-hub.js
```
