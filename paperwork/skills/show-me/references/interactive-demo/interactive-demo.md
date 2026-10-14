# Interactive demo

The reader learns by trying: moves a value and sees the result at once, or follows steps. Placed after the part that explains, before the one that decides.

## Parts

Write a fragment; `assemble-page.py` wraps it and adds this folder's CSS and script. Unmarked parts are optional; use at least one of Live block and Steps.

- **Lead** (required): one `<p>`: what to try and watch for
- **Live block**: `.live` with `.controls` and `.preview`: one control per parameter that changes the result, `data-param="<name>"`, with name, value in `<output data-show="<name>">` and unit; rare ones in a `<details>`. Controls redraw on `input`; no apply button.
- **Preview**: in Live block, the real output the parameters drive, not a placeholder; it reads each parameter as CSS variable `--<name>` (with `data-unit`), or listens for the `demo-draw` event, whose `detail` holds every value. A parameter needing data (query, regex) runs on a small real sample. Animate only without reduced-motion.
- **Presets**: 3 to 5 `<button data-preset='{"<name>": value, …}'>` named by intent, each setting all controls; the first is the current value
- **Result**: `<pre data-template="… {<name>} …">`: the result in its used form, rewritten on every change, and copied into the page's `.reply` if any
- **Steps**: `<ol class="steps">`, one action per `<li>` with a checkbox and, where the reader types, the exact command in a `<pre>`; `<span data-steps-count>` shows how many are done

## Gotchas

| symptom | fix |
| --- | --- |
| preview and result disagree | both read the same parameter; no hard-coded value in the preview |
