# Margin notes

## Parts

- **Answer**: `.answer` says what the change does and whether it is ready.
- **Key numbers**: `.numbers` gives files, lines added and removed, and notes by severity.
- **Where to look**: links to the 1 to 3 Places that need the reader's judgement.
- **Places**: in `.notes`, one `.place` per place worth a note: its text in a `<pre>` (a diff keeps its `+` and `-` lines) or a `<p>`, cut to the lines the note needs with `⋯` for what was cut, and an `<aside>` beside it with the note, which says why the line matters or what breaks, never what it does. Severity is by effect: `class="high"` breaks behaviour or a rule, `"mid"` makes a later change harder, plain is taste.
- **Files**: places sit under an `h3` per file, files in the order a reviewer reads them, the interface before its callers; a pull request's file heading links to the file at its `headRefOid`.
- **Skipped**: files with nothing to note are one line each under the places; past 15 files, a table with one row per folder (files, lines added and removed, what changed there), and Places only for those Where to look names.
- **Reply**: `.reply` holds the notes as plain text, one `path:line — note` per line.
- **Next**: approve or ask for changes; for a merged or closed change, the follow-up it needs, or none.

## CSS

```css
.notes .place { display: grid; gap: .5rem; margin: 0 0 1rem; }
.notes aside { border-left: 3px solid var(--ink); padding: .25rem .75rem; font-size: .9rem; }
.notes aside.high { border-color: var(--fail); } .notes aside.mid { border-color: var(--warn); }
@media (min-width: 60rem) { .notes .place { grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); } }
```
