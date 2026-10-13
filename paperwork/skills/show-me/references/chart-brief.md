# Chart brief

The reader must know where things stand or what happened: a status, a trend, a count by kind, an incident. The page leads with the number that answers, one chart that shows it, and what needs acting on.

## Form

- **Answer as a number**: `.answer` states the result with its number and unit and the period it covers, such as "Merged PRs per week rose from 3 to 11 over 12 weeks".
- **Key figures**: `.figures`, at most 3 numbers the answer and the chart do not already show, each with its unit and what it counts; none when they show all.
- **One chart**: change over time is a line, values compared across kinds are bars: an `<svg data-chart="line|bar" data-unit="…" data-values="label:number,…">` the base page draws, in a `<figure>` whose caption says what to read off it. A sequence of events with times (an incident) is an `<ol>` timeline of time and event instead.
- **Attention list**: a table of only the items that need action (stale, failing, blocked), each with its link and why, never every item; none when nothing needs action.
- **Source**: one line under the chart naming the command that produced the data and when it ran.

## Steps

1. Get the data with a command (`gh api`, `gh issue list --json`, `git log`), and compute counts, sums and periods with a script, never in your head; keep the command for the source line.
2. Pick the one chart by the answer's shape, charting the numbers the answer is about; a second chart only when the answer has two parts, never one that repeats a table.
3. Write the answer sentence from the computed numbers, claiming no more than they show.
4. Build from the base page with `.answer`, `.figures`, the chart, the attention list, the source line and `.next`, the next action being the item to act on first.

## Gotchas

| symptom | fix |
| --- | --- |
| bars or labels crowd | over 12 labels: group them (weeks, top 8 and other) |
| a zero or missing period looks like a gap | include it as `label:0` |
| the answer and the chart disagree | both come from the same computed numbers; recompute, never round by hand |
