# Live controls

The reader must set a value best judged by seeing it: a colour, a size, an easing, a layout setting, a prompt, a query, a config. The page puts controls beside a live preview, so the reader tunes by eye and copies the result out.

## Form

- **Live block**: `.live` holds `.controls` and `.preview`; every control redraws the preview at once, with no apply button.
- **Controls**: one per parameter that changes the result, labelled with its name, value and unit; grouped by concern, and the rarely touched ones in a `<details>`.
- **Presets**: 3 to 5 buttons with names that say their intent, each setting every control; the first is the current value.
- **Result**: `.reply` shows the result in the form the reader pastes (CSS, JSON, a cron line, a prompt), rewritten on every change.

## Steps

1. Name the parameters from the code or the system the value goes into, with their current values and allowed ranges.
2. Make the preview real: the actual component, text or output the value drives, not a placeholder; a value whose effect needs data (a query, a regex) runs on a small real sample.
3. Write the preset values from cases the reader knows, the current one first.
4. Build from the base page with `.answer` (what to tune and the current value), `.live`, the presets, `.reply` and `.next`, the next action being to paste the result back.

## Gotchas

| symptom | fix |
| --- | --- |
| too many controls | keep the ones that change what the reader sees; move the rest to `<details>` |
| the preview lags or jumps | redraw on `input`, not `change`; animate only under no reduced-motion preference |
| the result drifts from the controls | build it from the same state object that draws the preview |
