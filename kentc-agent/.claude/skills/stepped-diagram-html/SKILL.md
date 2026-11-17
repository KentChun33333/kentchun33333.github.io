---
name: stepped-diagram-html
description: Build a self-contained interactive HTML explainer in the style of designed-to-scale.vercel.app — an isometric SVG diagram the reader steps through (Back/Next, keyboard, stepper), with animated packets, live metric chips, a narration panel and light/dark themes. Use when asked for an animated/interactive diagram, step-through tutorial, architecture or flow explainer, or "HTML like that page".
---

# Stepped isometric diagram explainers (single-file HTML)

Reference: https://designed-to-scale.vercel.app/ (Dilum Sanjaya). Studied 2026-11-17: one Vite bundle, no
framework runtime detected, one SVG diagram per lesson (gradients, `feGaussianBlur` shadows, a pattern grid,
markers), motion from CSS keyframes/transitions plus a JS loop. Learn the techniques; do not copy its code,
copy or images.

Start from [`template.html`](template.html) (runnable, no dependencies, ~270 lines). Copy it, then replace
`NODES`, `LINKS`, `STEPS`, `CHIPS`. Open it directly from disk: it must work from `file://`.

## The idea that makes it feel good

Each step changes **one thing** the reader can see, and the motion *is* the explanation:
- a newly introduced component fades/slides in and gets a one-shot spotlight ring;
- a packet travels the hop, its duration scaled by the hop's real latency (`500 + ms × 3`);
- the metric chip that changed flashes and its value rises in; untouched chips stay still;
- the narration slides in from the direction of travel (Next → from right, Back → from left).
Nothing loops forever except an explicit "live" indicator. Stillness is what makes the change readable.

## Architecture (keep these boundaries)

| Part | Rule |
|---|---|
| Scene | All nodes and links declared once (`NODES`, `LINKS`) and drawn once. Steps only toggle classes. |
| Steps | Pure data: `{title, tag, body, idea, show[], links[], hops[[from,to,ms,kind]], metrics{}}`. No per-step code. |
| `go(i)` | Idempotent state → DOM. Clears transient fx, toggles `.off`, re-renders chips/narration, starts hops. Back, Next, stepper, hash and Replay all call it. |
| Run token | `++run` on every `go`; async hop loops exit when their token is stale. Prevents overlapping packets on fast clicking. |
| URL | `history.replaceState('#step-N')`; load reads the hash. Steps are linkable. |

## Isometric drawing (2:1 dimetric)

```js
const TILE = 40;
const iso = (i, j, z = 0) => [(i - j) * TILE / 2, (i + j) * TILE / 4 - z];
```
- A box = three polygons: left face, right face, top face (draw in that order), shared `stroke` 1.5 px,
  `stroke-linejoin: round`. Faces use three tokens (`--face-top/-l/-r`) so dark mode works.
- **Painter's algorithm:** draw nodes sorted by `i + j` ascending (far first). Links go in a layer *under*
  nodes; packets and fx in a layer *above*.
- Floor grid: an SVG `<pattern>` of one diamond (`M0 10 L20 0 L40 10 L20 20 Z`, 40×20) in `--line`.
- Anchor labels/packets at the top-face centre returned by `box()`. Labels are pill `rect rx=12` + text.
- Space nodes ≥ 3 tiles apart on screen; check overlaps at the final step where everything is visible.

## Visual tokens (start here, then theme)

- Warm paper palette: `--paper #f4ebe0`, `--sheet #f9f2e8`, `--line #ddd3c5`, `--edge #46413b`,
  `--ink #1d1b18`, accents `--green #cfe3b2`, `--violet #e7ddf5`, `--amber #f6d58e`, `--rust #d0683a`.
- Dark theme = same token names under `:root[data-theme=dark]`; never hard-code colours in SVG attributes —
  use `fill="var(--…)"`.
- One monospace family for everything (`"JetBrains Mono", ui-monospace, …`); hierarchy by size/weight only.
- Tactile buttons: 1 px `--edge` border + hard offset shadow `1.5px 2.5px 0`; hover lifts (−1,−1), active presses
  (+1,+1, no shadow).
- Cards: 12 px radius, 1 px `--line` border. Tags/pills: 999 px radius.

## Motion vocabulary

| Use | Timing |
|---|---|
| Enter/settle (`--ease-out`) | `cubic-bezier(.2,.7,.2,1)`, 0.30–0.34 s for transforms, 0.22 s opacity |
| Playful pop (`--ease-back`) | `cubic-bezier(.34,1.56,.64,1)`, 0.32 s, small elements only |
| Progress bars (`--ease-io`) | `cubic-bezier(.65,0,.35,1)`, 0.6–0.7 s |
| `value-in` | from `opacity 0; translateY(4px)` |
| `chip-flash` | expanding box-shadow ring 0 → 4 → 10 px, lift −2 px at 15 % |
| `spot` | ring scale .75 → 1.4, opacity 0 → 1 → 0, ~1.1 s, removed on `animationend` |
| `guide-in` | narration children from `translateX(var(--slide))`, staggered 50 ms |
| Packets | JS `requestAnimationFrame`, ease-in-out cubic, pausable (accumulate elapsed only when not paused) |

Use CSS for anything state-driven (class toggles); JS only for path-following motion.

## Interaction checklist

- Keys: `←`/`→` step, `R` replay, `Space` pause (preventDefault); ignore keys inside inputs.
- Stepper buttons with `aria-current="step"`, done steps tinted; Next shows the next step's title.
- Narration in an `aria-live="polite"` panel; SVG `role="img"` labelled by the step title.
- `prefers-reduced-motion: reduce`: disable CSS animations/transitions and jump packets to the end
  (duration 0). The content must stay complete without motion.
- Responsive: two columns ≥ 880 px, stacked below; no horizontal scroll at 390 px.

## Verify before delivering

Run it in a real browser (not only by reading the code):
1. Load from `file://`; console has no errors.
2. Step through every step with the keyboard; screenshot the final step (all nodes visible): no overlaps,
   labels readable.
3. Toggle dark theme; every face, label and chip stays legible.
4. 390 px viewport: `document.documentElement.scrollWidth <= innerWidth`.
5. Motion settles: `await Promise.all(document.getAnimations().map(a => a.finished))` resolves (≈ 1.1 s with a
   spotlight). Headless screenshots taken right after a step can show mid-transition frames; wait or measure.
6. Hash navigation: load with a different `#step-N` using a *reload* (a hash-only `goto` keeps the old page).
