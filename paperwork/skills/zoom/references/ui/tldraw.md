# tldraw

Draws a Schema level as editable shapes in the tldraw offline desktop app, through its local HTTP server. Use it when
the owner wants a canvas to rearrange and annotate, not a fixed picture.

```
U=paperwork/skills/zoom/references/ui
$U/tldraw/scripts/render-tldraw.py paperwork/skills/zoom/examples/pull-request/schema.json out.png
```

It prints the PNG path and leaves a new `<out>-tldraw/*.tldraw` file beside it, so the owner can open the canvas. It
opens the app when it is not running and never touches a document already open. Shown on this machine for the
pull-request example: [pull-request.png](tldraw/examples/pull-request.png).

## What it draws

The script turns the root `level` into Mermaid (each node a box with its `label`, each edge an arrow with its `label`)
and hands it to the app's `helpers.mermaid`, which makes real boxes and bound arrows. It reads the kinds as
[semantics.md](../schema/semantics.md#opening-a-level) says but draws none of the difference; `opens`, `rules`, `meta`
and `media` are left out.

## Gotchas

- The app must be installed as `tldraw offline`; its port and token come from
  `~/Library/Application Support/tldraw/server.json`, which a clean quit removes.
- Each run creates a document, so reruns pile up files; delete the `-tldraw` folder when done.
- The screenshot is a JPEG of the canvas; `sips` writes the PNG, so it needs macOS.
