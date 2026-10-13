# Margin notes

The reader must review a change or a text: a pull request, a diff, a draft, a document. The page shows the text itself, with each note beside the line it is about, so the reader reads both at once.

## Form

- **Verdict first**: `.answer` says what the change does and whether it is ready, in one sentence; `.figures` under it gives the size: files, lines added and removed, and the count of notes by severity.
- **Where to look**: a short list of the 1 to 3 places that need the reader's judgement, each a link to its row below.
- **Rows**: in `.notes`, one `.row` per hunk or passage worth a note: the text in a `<pre>` (a diff keeps its `+` and `-` lines) or a `<p>`, and an `<aside>` beside it with the note; `class="high"` or `"mid"` marks the severity, plain is a remark. Group rows under an `h3` per file, files in the order a reviewer reads them, the interface before its callers.
- **What is skipped**: files with nothing to note are one line each under the rows, never shown whole; past 15 files, one table row per folder instead (files, lines added and removed, what changed there), and rows only for the places to look.
- **Reply**: `.reply` holds the notes as plain text, one `path:line — note` per line, so the reader pastes them into the review.

## Steps

1. Read the change itself: `gh pr view <n> --json title,body,files,headRefOid` and `gh pr diff <n>`, or the file and its history; never review from the description alone.
2. Decide each note's severity by its effect: high breaks behaviour or a rule, mid makes a later change harder, plain is taste.
3. Cut a hunk to the lines its note needs, with `⋯` for what was cut; link each file heading to the file on GitHub at the head commit.
4. Build from the base page with `.answer`, `.figures`, the list of places, `.notes`, `.reply` and `.next`, the next action being approve, ask for changes, or what to read first.

## Gotchas

| symptom | fix |
| --- | --- |
| a long line pushes the page sideways | it stays inside its `<pre>`, which scrolls; never widen the column |
| every hunk is shown | show only rows with a note; list the rest |
| notes restate the code | a note says why the line matters or what breaks, never what it does |
