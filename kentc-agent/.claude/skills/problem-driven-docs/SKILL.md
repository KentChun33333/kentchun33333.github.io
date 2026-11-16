---
name: problem-driven-docs
description: Write or restructure the HTML design docs in docs/ (reader shell index.html + one page per topic in docs/topics/) in the problem → core idea → evidence style. Use when adding, editing, merging, renumbering or verifying a docs topic page.
---

# Problem-driven HTML docs (docs/index.html + docs/topics/)

The design docs explain the system as a set of **problems it solves**, not as a tour of modules.
Every topic answers three questions in order: what breaks without this (問題), how we solve it and
why this way (核心想法), and what evidence supports it (依據). Language: 繁體中文.

## Tone: expert reader, minimum words

Write for a highly capable engineer who reads fast and distrusts filler.

- Lead with the claim; no warm-up, rhetorical setup or questions (「其實」「真正」「就是」「也就是說」「我們」「聽起來…但」).
- One idea per sentence; never restate what the summary card already says.
- `.psd` cards: ≤ 2 short sentences each (~25–60 字). Problem items: `<b>名稱</b>：機制 → 後果。`
- Prefer numbers, symbols (→ ≤ × ≈) and exact names over explanation; skip basics an expert knows.
- Caveats stay, as one clause. Neutral register: no marketing, no exclamation, no teaching voice.
- Shorter must never mean less information: every number, link, caveat and `[推論]` survives an edit.

## Architecture (do not add a second convention)

| File | Role |
|---|---|
| `docs/index.html` | Reader shell: hero (project-level 問題/核心想法/依據), `<template id="homeTpl">`, `<noscript>` topic list |
| `docs/topics/<slug>.html` | One standalone page per topic; must work alone, from `file://`, and without JS |
| `docs/asset/js/topics.js` | **Single source of truth** for topic order, `num`, `nav`, `group`, `kicker`, `title`, `problem` |
| `docs/asset/js/core.js` | Widgets (`KentcDocs.mount(root, slug)`), shared sidebar, search filter, pager, sticky offsets |
| `docs/asset/js/shell.js` | Router: `#slug`, `#slug/anchor`; unknown `#id` is searched across topics; fetch failure → standalone page |
| `docs/asset/css/shell.css` | Reader layout, `.psd` summary cards, `h3.part` headings (core.css is minified; add rules here) |

Groups are problem areas (e.g. 基礎：一個代理 / 上下文視窗：長任務的核心限制 / 編排與外部資料 / 應用與參考),
not package names. Reorder or merge topics when two pages tell one story (web + web-design became one page).

## Topic page structure (required)

```html
<section class="card" id="<slug>" aria-labelledby="<slug>-title">
  <p class="eyebrow">NN · <kicker></p>
  <h2 id="<slug>-title"><title></h2>
  <div class="psd">
    <div class="psd-item problem"><span>問題</span><p>One concrete failure, 1–2 sentences.</p></div>
    <div class="psd-item idea"><span>核心想法</span><p>The mechanism and the reason for it.</p></div>
    <div class="psd-item data"><span>依據</span><p>The strongest number or test, with "（見 ③）".</p></div>
  </div>
  <h3 class="part problem" id="problem" data-step="1">問題：…</h3>
  <!-- optional, when alternatives were tried: -->
  <h3 class="part explored" id="explored" data-step="2">先嘗試過的方案：…</h3>
  <h3 class="part idea" id="solution" data-step="N">核心想法：…</h3>
  <h3 class="part data" id="data" data-step="N">依據：…</h3>
  <p class="source">實作對照：<a href="../../src/...">…</a></p>
</section>
```

- Exactly one `.psd` per page; parts start with `problem`, contain `idea`, end with `data`.
  `data-step` numbers are sequential (1, 2, 3[, 4]). Other `h3` inside a part are ordinary subsections.
- Eyebrow must equal `num · kicker` and the `h2` must equal `title` in `topics.js`;
  `topics.js` `problem` is the one-line problem shown on home cards and in `<meta name="description">`.
- Keep existing ids (`recovery`, `pdf-safeguards`, `horizontal`, …) when moving content: old links
  resolve through them. When merging a page, put the old slug as the id of the merged part
  (e.g. `id="web-design"` on the explored part of `web.html`).

## Writing each part

**① 問題** — what breaks, for whom, and why it matters in *this* system (small local model,
62,536-token window, untrusted inputs). Prefer a short list of concrete failure modes over adjectives.
Link the related topic when the problem is an instance of a broader one (documents → horizontal context).

**② 先嘗試過的方案** (only if real) — options considered or built, the criteria used, what failed and
the measured reason. Include removed implementations: the lesson is part of the design.

**③ 核心想法** — the mechanism, then the existing technical detail (tables, formulas, widgets, YAML).
State boundaries and what it does **not** guarantee (callout `warn`).

**④ 依據** — evidence that already exists in the repo, in this order of preference:
1. Recorded runs (`docs/compare-run-*/`, `docs/*-results*.json`, `docs/*.md` result sections)
2. Numbers computed from the page's own formula with real deployment values (show the arithmetic)
3. Regression tests and benchmark scripts (link the files)

If a topic has no measurement, say so and point to the tests or the topic that holds it.

## Evidence rules (non-negotiable)

- Every number must come from a file you read or a computation you ran; link the source file.
  Compute ratios with a tool. (A past error: "242,000 chars is 4× the window" — it is ≈60k tokens, ≈1×.)
- Mark inference as `[推論]`. Do not attribute a result to a mechanism the data did not isolate
  (v2 beat v1, but topic notes were barely read — the page must say so).
- Historical results of removed implementations are labelled historical, never as current behaviour.
- A high rubric score is not proof of correctness; mention known factual errors next to scores.
- Do not change raw result files or rubrics to make a page read better.

## Links

- Cross-topic: `href="<slug>.html"` (the reader rewrites it to `#<slug>`). Never `href="#other-topic"`.
- From `docs/topics/`: repo files are `../../src/…`, `../../tests/…`; docs files are `../compare.md`,
  `../compare-run-…/…`. The reader resolves these against the topic URL.
- README and other external references link the standalone page: `docs/topics/<slug>.html#<id>`.

## Adding, renaming or merging a topic

1. Create/edit `docs/topics/<slug>.html` from an existing page (same `<head>`, header search,
   `.reader` + `.sidebar` wrapper, `<nav class="pager" data-pager>`, scripts `topics.js` then `core.js`).
2. Update `topics.js` (order = reading order; renumber `num` and every affected eyebrow).
3. Regenerate `<title>`, meta description and the `index.html` `<noscript>` list from `topics.js`.
4. Search docs and README for the old slug/number; keep old ids alive as anchors.
5. Widgets: add a `mountX(root)` in `core.js` that queries only inside `root` and returns early when its
   elements are absent; never depend on DOM from another topic (shared values go through sessionStorage).

## Verification (run before reporting)

Static check (script): for every manifest entry — eyebrow/h2 match, one `.psd`, part order, no duplicate
ids, no `href="#…"` except `#topic`, every relative `href` exists on disk; same link check for `index.html`;
`node -e` load of `topics.js` succeeds.

Browser check (`python -m http.server` from the repo root, cache disabled, reload after edits):
- Home: card count = topics, groups in order, problem line on each card, no page errors.
- Each topic via `#slug`: outline lists 問題 / 核心想法 / 依據 parts; widgets mount on their page.
- Old anchors (`index.html#recovery`, `#pdf-safeguards`, any merged slug) land on the right part.
- 390px width: no horizontal overflow on any topic; sidebar strip visible.
- `file://…/docs/index.html#slug/anchor` falls back to the standalone page at the anchor.

Known pitfalls: the shared headless browser serves stale JS/CSS from cache; `display:flex` on links
overrides `[hidden]` (add an explicit `[hidden]{display:none}`); `scroll-behavior:smooth` makes topic
switches animate from the old position (use `behavior:'instant'`); long code paths in `.source` overflow
on phones; `.psd` arrows rely on three-column layout and switch to ↓ below 880px.
