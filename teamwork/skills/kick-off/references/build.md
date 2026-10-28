# Build

The steps for each kind of work a task changes or ends in, one section per kind; open the one [worker.md](worker.md) step 2 **Build** names.

## Rules

1. `git grep` every file that states the rule; past 5 files, a `light`, `low` subagent lists them.
2. Edit the rule where it lives; check any size cap with `git diff --numstat origin/<base>`.
3. Run each criterion over the lines that carry the rule, not over the diff.
4. Finish every `decide` and criteria edit before `judge`, since a change mid-review returns stale findings.

## Code

1. Write the failing test or probe first, by the repository's test rules. Each asserts a behaviour your task names through the code's own interface, so it fails when that behaviour breaks, never an assertion true whatever the code does (`A is A`). Drive the code until they pass. Where the rules keep none: keep them in the scratchpad, never committed; hand the `judge` their paths with the url; and run each by [run-on-refs.py](../scripts/run-on-refs.py) `'<command>' origin/<base> <head sha>` until it prints that it fails on the base and passes at the head. Quote the command in the criterion, so the judge reruns it. A plugin's test runs in its copy: the command copies it into the plugin's folder, then runs `claude plugin test <plugin>`.
2. Run the repository's or plugin's tests; for an eval case, `claude plugin eval ./<plugin>` and read the failing transcript.
3. A hook, monitor, start script or service: probe the live copy in a new session or on its host, never only its fixture; a monitor reads everything on its first loop, so to probe that it notices a change, start it, wait for its first line, then make the change; for a change in looks, the owner checks how it looks on the live pane or page.

## UI

1. Change a fixture page or screen first, then what uses it.
2. Run the render check on each changed page or screen until it prints `ok`; a run over a few minutes goes to a subagent.
3. Look at each 390 px and 1200 px capture until it shows the change; past 3 pages, one read-only subagent per page. A capture that needs a signed-in browser, such as a claude.ai page: before building, check one is connected (`list_connected_browsers`), and `BLOCKED:` at once when none is; scroll a claude.ai Artifact once before capturing, since its frame stays blank until then.
4. A live pane (`teamwork/hooks/issue-pane.tsx`): compile it first by `bun build <file> --external claude-code --external 'react*' --outdir <scratch>`, which checks syntax and imports, not types; list the owner's layout words (colors, spacing, symbols, format; their screenshots too) from the task and the issues it follows, and quote beside each the live row that meets it. The owner's word beats your taste, and an unclear word is a `BLOCKED:`.
5. A live pane, in a narrow width: no text is cut, hidden or shrunk; a link and a fold mark keep full width (`flexShrink={0}`), long text wraps, and each fold row presses over its whole text but the link.

## Migration

1. Count every reference or user of the old form, `git grep -nw <old>`; past 50 files, one `light`, `low` subagent per folder.
2. For data, a schema or a live service, dry-run the change on a copy first.
3. A test that forbids the old name builds it from joined pieces (`a + "-" + b`), or its own literal matches the grep.
4. `git mv`, then replace by script, never file by file.
5. Rerun the suite until it passes as many tests as on the base; `claude plugin validate ./<plugin>` for a plugin.
6. Probe the installed or live copy that loads the moved files or data.
7. Done when `git diff -M --numstat origin/<base>` shows only moves and replaced lines, and `git grep` finds no old name.

## Research

1. Fan out at once one `mid`, `medium` subagent per independent source set (transcripts, issues, official docs, the web), and one per field the question draws on, briefed to do what that field does, never to write in its voice. Each brief names its output form.
2. Start from the rawest material (logs, transcripts, API data, an article's every tip, not its headlines), not a summary of it, and look at it by eye between steps: after each aggregate, print its rows and read each boundary case. Test against it each belief the backlog takes as given before building on it. Compute each number by a kept script or query, never a table read by eye. Brief a labeller with what happened, never the number under test.
3. Test a finding that claims to predict on data held out from the data that found it.
4. Hand the draft to a red-team subagent briefed to do what a sceptic of that field does to break a claim; fix each break or state it as a limit.
5. Write the report to a file: findings, each citing its source; the most urgent decisions they raise, ranked, each with its case for and against; then each criterion with its command, result and output on the base; `comment` it on the issue as `REPORTED:`.
6. A `judge` reviews the comment's url; answer its gaps in a new comment, judged again, until it approves.
