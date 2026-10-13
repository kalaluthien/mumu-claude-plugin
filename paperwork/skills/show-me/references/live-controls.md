# Live controls

## Form

- **Answer**: `.answer` names what to tune and its current value.
- **Live block**: `.live` holds `.controls` and `.preview`; every control redraws the preview on `input`, with no apply button.
- **Controls**: one per parameter that changes the result, labelled with its name, value and unit; grouped by concern, the rarely touched ones in a `<details>`.
- **Preview**: the actual component, text or output the parameters drive, never a placeholder; a parameter whose effect needs data (a query, a regex) runs on a small real sample.
- **Presets**: 3 to 5 buttons named by their intent, from cases the reader knows, each setting every control; the first is the current value.
- **Reply**: `.reply` shows the result in the form the reader pastes (CSS, JSON, a cron line, a prompt), rewritten on every change from the same parameter values that draw the preview.
- **Next**: paste the result back.

## Steps

1. Name the parameters with their current values and allowed ranges.
2. Animate the preview only when the reader has no reduced-motion preference.
