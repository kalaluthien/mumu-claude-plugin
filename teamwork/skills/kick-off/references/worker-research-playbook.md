# Research

1. Fan out at once one `mid`, `medium` subagent per independent source set (transcripts, issues, official docs, the web), and one per field the question draws on, briefed to do what that field does, never to write in its voice; each brief names its output form.
2. Start from the rawest material (logs, transcripts, API data), not a summary of it: test against it each belief the backlog takes as given before building on it, and compute each number by a kept script or query, never a table read by eye.
3. Test a finding that claims to predict on data held out from the data that found it.
4. Hand the draft to a red-team subagent briefed to do what a sceptic of that field does to break a claim; fix each break or state it as a limit.
5. Write the report to a file: findings, each citing its source; the most urgent decisions they raise, ranked, each with its case for and against; then each criterion with its command, result and output on the base; `comment` it on the issue as `REPORTED:`.
6. A `judge` reviews the comment's url; answer its gaps in a new comment, judged again, until it approves.
