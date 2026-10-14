# Interactive demo

The reader learns by trying: they move a value and see the result at once, or follow steps and see each one done. Placed after the part that explains, before the part that decides.

## Parts

Write the part's body as a fragment; `assemble-page.py` wraps it and adds this folder's CSS and script. Use at least one of Live block and Steps.

| part | use | holds |
| --- | --- | --- |
| Lead | required | one `<p>` saying what to try and what to watch for |
| Live block | optional | `.live` with `.controls` and `.preview`: one control per parameter that changes the result, `data-param="<name>"`, labelled with its name, its value in `<output data-show="<name>">` and its unit; the rarely touched ones in a `<details>`. Every control redraws on `input`, with no apply button. |
| Preview | optional | inside the Live block, the actual component, text or output the parameters drive, never a placeholder; it reads each parameter as the CSS variable `--<name>` (with the control's `data-unit`), or listens for the `demo-draw` event, whose `detail` holds every value. A parameter whose effect needs data (a query, a regex) runs on a small real sample. It animates only when the reader has no reduced-motion preference. |
| Presets | optional | 3 to 5 `<button data-preset='{"<name>": value, …}'>` named by their intent, from cases the reader knows, each setting every control; the first is the current value |
| Result | optional | `<pre data-template="… {<name>} …">`: the result in the form it is used (CSS, JSON, a cron line, a prompt), rewritten on every change from the same values the preview reads, and copied into the page's `.reply` when the page has one |
| Steps | optional | `<ol class="steps">`, one action per `<li>`, each with a checkbox and, where the reader types something, the exact command in a `<pre>`; `<span data-steps-count>` shows how many are done. For a guide to follow, or a concept walked one state at a time. |

## Gotchas

| symptom | fix |
| --- | --- |
| the preview and the result disagree | both must read the same parameter; never hard-code a value in the preview |
