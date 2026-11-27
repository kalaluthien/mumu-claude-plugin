# Research

Build and judge a report that answers a question, with no file of the repository changed.

## Domain

- **Raw material**: logs, transcripts, API data, an article fetched with every tip verbatim; never a summary of it.

## Steps

1. Build: fan out at once one subagent per independent source set (transcripts, tasks, official docs, the web), and one per field the question draws on. Each brief names its output form.
2. Build: start from the raw material, mapped one row per item, such as each tip with its quote and the `path:line` that answers it or `none`, and look at it by eye between steps: after each aggregate, print its rows and read each boundary case, yourself or by a labeller briefed with what happened, never the number under test. Test against it each belief the task takes as given before building on it. Compute each number by a kept script or query, never a table read by eye.
3. Build: test a finding that claims to predict on data held out from the data that found it.
4. Build: hand the draft to a red-team subagent briefed to do what a sceptic of that field does to break a claim; fix each break or state it as a limit.
5. Build: write the report to a file: findings, each citing its source; the most urgent decisions they raise, ranked, each with its case for and against; then each criterion with its command, result and output on the base; `comment` it on the task as `REPORTED:`.
6. Judge: open each url, file or command a claim cites and read it beside the claim; answer gaps come back in a new comment, judged again, until approved.

## Rules

- **Cheap first**: a kept script over the raw material before any subagent reads it.
- **One subagent per source set**: one start serves every question about that set.
- **Judge tier**: `mid`, `medium`.
