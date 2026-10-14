# Live controls

## Parts

- **Answer**: `.answer` names what to tune and its current value.
- **Live block**: `.live` holds `.controls` and `.preview`; every control redraws the preview on `input`, with no apply button.
- **Controls**: one per parameter that changes the result, labelled with its name, value and unit; grouped by concern, the rarely touched ones in a `<details>`.
- **Preview**: the actual component, text or output the parameters drive, never a placeholder; a parameter whose effect needs data (a query, a regex) runs on a small real sample; it animates only when the reader has no reduced-motion preference.
- **Presets**: 3 to 5 buttons named by their intent, from cases the reader knows, each setting every control; the first is the current value.
- **Reply**: `.reply` shows the result in the form it is used (CSS, JSON, a cron line, a prompt), rewritten on every change from the same parameter values that draw the preview.

## CSS

```css
.live { display: grid; gap: 1rem; } @media (min-width: 60rem) { .live { grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); } }
.controls label { display: block; margin: 0 0 .75rem; font-size: .9rem; }
.controls input, .controls select { width: 100%; }
.preview { border: 1px solid var(--ink); padding: 1rem; min-height: 8rem; }
```
