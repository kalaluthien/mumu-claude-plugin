# Sitrep

The reader grasps where something stands or what changed: numbers, a trend, events in time, or the places of a change or a text worth a note. Placed first when the ask starts from a situation; a decision or a deeper look follows it.

## Parts

Write the part's body as a fragment; `assemble-page.py` wraps it and adds this folder's CSS. Use the parts the situation needs, and at least one of Chart, Timeline and Notes.

| part | use | holds |
| --- | --- | --- |
| Lead | required | one `<p>`: the result with its number, unit and period ("Merged PRs per week rose from 3 to 11 over 12 weeks"), or what the change does and whether it is ready |
| Key numbers | optional | `.numbers`, at most 3, each with what it counts; a change gives files, lines added and removed, and notes by severity |
| Chart | optional | change over time is a line, values compared across kinds are bars, as `<svg data-chart="line\|bar" data-unit="…" data-values="label:number,…">` inside a `<figure>` whose caption says what to read off it; one chart, two only when the answer has two parts |
| Timeline | optional | `<ol class="timeline">`, one `<li>` per event with its `<time>`: what happened (an incident) or what is planned (a plan ahead, each item with its owner and what it waits on) |
| Notes | optional | `.notes`, one `.place` per place worth a note: its text in a `<pre>` (a diff keeps its `+` and `-` lines) or a `<p>`, cut to the lines the note needs with `⋯` for what was cut, and an `<aside>` that says why the line matters or what breaks, never what it does. Severity by effect: `class="high"` breaks behaviour or a rule, `"mid"` makes a later change harder, plain is taste. Places sit under an `h3` per file, the interface before its callers; a pull request's file heading links to the file at its `headRefOid`. Above them, links to the 1 to 3 places that need the reader's judgement; below, one line per file with nothing to note, or past 15 files a table per folder. |
| Attention list | optional | a table in `.scroll` of only the items that need action (stale, failing, blocked), each with its link and why |
| Source | required | one `.muted` line naming the command that produced the data, or the sha read, and when |

## Gotchas

| symptom | fix |
| --- | --- |
| bars or labels crowd | over 12 labels: group them (weeks, top 8 and other); keep labels short enough that none is dropped at 390 px |
| a zero or missing period looks like a gap | include it as `label:0` |
