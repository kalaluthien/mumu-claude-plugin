# Sitrep

The reader grasps where something stands or what changed: numbers, a trend, events in time, or places worth noting. Placed first.

## Parts

Unmarked parts are optional; use at least one of Chart, Timeline and Notes.

- **Lead** (required): one `<p>`: the result with number, unit and period, or what the change does and whether it is ready
- **Key numbers**: `.numbers`, at most 3, each with what it counts; a change gives files, lines added and removed, notes by severity
- **Chart**: `<svg data-chart="line|bar" data-unit="…" data-values="label:number,…">` in a `<figure>` whose caption says what to read; line for time, bars across kinds; one chart (two only for a two-part answer)
- **Timeline**: `<ol class="timeline">`, one `<li>` per event with `<time>`: what happened, or what is planned (owner, what it waits on)
- **Notes**: `.notes`, one `.place` per place: text in a `<pre>` (diff keeps `+`/`-`) or a `<p>`, cut with `⋯`, plus an `<aside>` on why it matters or what breaks, never what it does. `class="high"` breaks behaviour or a rule, `"mid"` makes a later change harder, plain is taste. Places sit under an `h3` per file, interface first; a pull request's file heading links to the file at its `headRefOid`. Above: links to the 1 to 3 places needing judgement; below: a line per file with nothing to note, or past 15 files a table per folder.
- **Attention list**: table in `.scroll` of only items needing action (stale, failing, blocked), each with link and why
- **Source** (required): one `.muted` line: the command that produced the data, or the sha read, and when

## Gotchas

| symptom | fix |
| --- | --- |
| bars or labels crowd | over 12 labels: group them (weeks, top 8 and other); no label dropped at 390 px |
| a zero or missing period looks like a gap | include it as `label:0` |
