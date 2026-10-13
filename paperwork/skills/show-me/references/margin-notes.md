# Margin notes

## Form

- **Answer**: `.answer` says what the change does and whether it is ready; `.figures` gives files, lines added and removed, and notes by severity.
- **Where to look**: a list of the 1 to 3 rows that need the reader's judgement, each a link to its row.
- **Rows**: in `.notes`, one `.row` per place worth a note: its text in a `<pre>` (a diff keeps its `+` and `-` lines) or a `<p>`, cut to the lines the note needs with `⋯` for what was cut, and an `<aside>` beside it with the note, which says why the line matters or what breaks, never what it does. Severity is by effect: `class="high"` breaks behaviour or a rule, `"mid"` makes a later change harder, plain is taste.
- **Files**: rows sit under an `h3` per file, files in the order a reviewer reads them, the interface before its callers; a pull request's file heading links to the file at its `headRefOid`.
- **Skipped**: files with nothing to note are one line each under the rows; past 15 files, a table with one row per folder (files, lines added and removed, what changed there), and rows only for Where to look.
- **Reply**: for an open pull request or a draft, `.reply` holds the notes as plain text, one `path:line — note` per line; a merged or closed change has none.
- **Next**: approve, ask for changes, or what to read first.

## Steps

1. Read the change itself: `gh pr view <n> --json title,body,files,headRefOid` and `gh pr diff <n>`, or the text and its history.
