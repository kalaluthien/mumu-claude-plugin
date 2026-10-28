# pele

Draws a Schema level as a themeable SVG and PNG with [pele](https://pele.run/) 1.7.0, a Mermaid-to-SVG library with no CLI and no layout of its own to tune. Use it when a flat, restylable picture of one level is enough.

## Domain

The script draws only the root `level`, as a left-to-right flowchart: each node is a box with its `label`, each edge an arrow with its `label`. It reads the kinds as [semantics.md](../schema/semantics.md#opening-a-level) says but draws none of the difference: a state, a workflow and a topology level look alike, and `opens`, `rules`, `meta` and `media` are left out.

The script writes `out.png`, `out.svg` and `out.mmd` (the Mermaid it drew) and prints the PNG path. Shown on this machine for the pull-request example: [pull-request.png](pele/examples/pull-request.png).

## Steps

1. Run the script with a document and the PNG path to write:

```
U=paperwork/skills/zoom/references/ui
$U/pele/scripts/render-pele.py paperwork/skills/zoom/examples/pull-request/schema.json out.png
```

## Rules

- **First run**: it installs `pele` and `playwright-core` (`assets/package.json`, locked by `assets/package-lock.json`) with `npm ci --ignore-scripts` into `~/.cache/zoom-render-pele`, so it needs `npm` and network once.
- **Chromium**: the PNG comes from the Playwright headless Chromium in `~/Library/Caches/ms-playwright`; with none there, the script fails at the screenshot, not at pele.
- **Mermaid only**: pele reads Mermaid only, so a quote in a label becomes `'`.
