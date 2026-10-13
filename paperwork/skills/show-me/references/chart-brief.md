# Chart brief

## Form

- **Answer**: `.answer` states the result with its number, unit and the period it covers, such as "Merged PRs per week rose from 3 to 11 over 12 weeks".
- **Key numbers**: `.figures`, each with what it counts.
- **Chart**: change over time is a line, values compared across kinds are bars, in the base page's `data-chart` markup inside a `<figure>` whose caption says what to read off it; a sequence of events with times (an incident) is an `<ol>` timeline of time and event instead. One chart, two only when the answer has two parts.
- **Attention list**: a table of only the items that need action (stale, failing, blocked), each with its link and why.
- **Source**: one line under the chart or timeline naming the command that produced the data and when it ran.
- **Next**: the first item of the attention list; with none, when to look again.

## Steps

1. Get the data with a command (`gh api`, `gh issue list --json`, `git log`), and compute counts, sums and periods with a script; keep the command for the source line.

## Gotchas

| symptom | fix |
| --- | --- |
| bars or labels crowd | over 12 labels: group them (weeks, top 8 and other); keep labels short enough that none is dropped at 390 px |
| a zero or missing period looks like a gap | include it as `label:0` |
