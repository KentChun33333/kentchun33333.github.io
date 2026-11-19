# System Design, Step by Step

Interactive system-design lessons rendered as animated isometric SVG diagrams.
Source lives here; the static build is committed to `../system-design/` and served by GitHub Pages at `/system-design/`.

```sh
npm install
npm run dev     # local dev server
npm run build   # writes ../system-design/ — commit that folder
```

## Adding a lesson

All content is in `src/lessons.js`. A lesson is `{ id, title, steps }`; each step is a complete scene (the schema is documented at the top of that file). Nodes keep their `id` across steps, so moving a node between steps animates it. Packets follow `flows[].route`, and edges are derived from routes automatically.

URLs are `#/<lesson-id>/<step>`. ← / → keys step through.
