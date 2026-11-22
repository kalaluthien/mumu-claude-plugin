# Build

The steps for each kind of work a task changes or ends in, one section per kind.

## Instructions

1. `git grep` every file that states the rule; past 5 files, a `light`, `low` subagent lists them.
2. Edit the rule where it lives; check any size cap with `git diff --numstat origin/<base>`.
3. Run each criterion over the lines that carry the rule, not over the diff.
4. Finish every `decide` and criteria edit before `judge`, since a change mid-review returns stale findings.

## Code

1. Write the failing test or probe first, by the repository's test rules. Each asserts a behaviour your task names through the code's own interface, so it fails when that behaviour breaks, never an assertion true whatever the code does (`A is A`). Drive the code until they pass. Where the rules keep none: keep them in the scratchpad, never committed; hand the `judge` their paths with the url; and run each by [run-on-refs.py](worker-build/scripts/run-on-refs.py) `'<command>' origin/<base> <head sha>` until it prints that it fails on the base and passes at the head. Quote the command in the criterion, so the judge reruns it. A plugin's test runs in its copy: the command copies it into the plugin's folder, then runs `claude plugin test <plugin>`.
2. Run the fixture runners of the parts you changed, leaving the repository's whole check to the one run worker.md's **Land** names; for an eval case, `claude plugin eval ./<plugin>` and read the failing transcript.
3. A hook, monitor, start script or service: probe the live copy in a new session or on its host, never only its fixture; a monitor reads everything on its first loop, so to probe that it notices a change, start the real monitor, wait for its first line, make the change, and check the probe fails with the call under test removed; for a change in looks, the owner checks how it looks on the live pane or page.

## UI

1. Change a fixture page or screen first, then what uses it.
2. Run the render check on each changed page or screen until it prints `ok`; a run over a few minutes goes to a subagent.
3. Look at each 390 px and 1200 px capture until it shows the change, taken past 3 pages by one read-only subagent per page, and for a page behind a login, such as claude.ai, in a signed-in browser: check one is connected (`list_connected_browsers`) before building, `BLOCKED:` at once when none is, since only the owner connects one, save each screenshot by `save_to_disk: true`, and scroll a claude.ai Artifact once first, since its frame stays blank until then.
4. A live pane (`teamwork/hooks/draw-task-pane.tsx`): compile it first by `bun build <file> --external claude-code --external 'react*' --outdir <scratchpad>`, which checks syntax and imports, not types; list the owner's layout words (colors, spacing, symbols, format; their screenshots too) from the task and the tasks it follows, and quote beside each the live row that meets it. The owner's word beats your taste, and an unclear word is a `BLOCKED:`.
5. A live pane, in a narrow width: no text is cut, hidden or shrunk; a link and a fold mark keep full width (`flexShrink={0}`), long text wraps, and each fold row presses over its whole text but the link.

## Refactor

A refactor changes form, never behaviour. The owner's bare "refactor" asks for it over everything the named work built, aiming at one structure, fewest elements, no room for mistakes, nothing scattered, each rule once, easy to understand; a migration is a refactor of one name, format or schema. Read it with the section of what the work touches.

1. List every file, rule, check, UI element and user of an old form in scope, one row each with where it lives, by `git grep -nw <name>`; past 5 files, one `light`, `low` subagent per folder lists them.
2. Give each row one verdict: merge (it repeats another; the owner's later decision wins), delete (no reader or caller), move (a name, rule or value in two places goes to the one place that owns it), guard (a wrong state is possible: make it unrepresentable, else add a check that fails on a planted fault), or keep.
3. Apply them by script, never file by file: `git mv`, then replace; for data, a schema or a live service, dry-run on a copy first; a test that forbids an old name builds it from joined pieces (`a + "-" + b`), or its own literal matches the grep. Then rename what a newcomer would misread and give each rule one example.
4. Done when the suite passes as many tests as on the base (`claude plugin validate ./<plugin>` for a plugin), the installed or live copy loads the moved files or data, `git grep` finds no old name, and a pure migration's `git diff -M --numstat origin/<base>` shows only moves and replaced lines.
5. Report the counts before and after (lines, rules, elements, checks) and each row not kept with its reason, such as `3 key handlers → 1: search, menu and key list each read Escape`.

## Research

1. Fan out at once one subagent per independent source set (transcripts, tasks, official docs, the web), and one per field the question draws on. Each brief names its output form.
2. Start from the rawest material (logs, transcripts, API data, an article fetched with every tip verbatim), not a summary of it, mapped one row per item, such as each tip with its quote and the `path:line` that answers it or `none`, and look at it by eye between steps: after each aggregate, print its rows and read each boundary case, yourself or by a labeller briefed with what happened, never the number under test. Test against it each belief the task takes as given before building on it. Compute each number by a kept script or query, never a table read by eye.
3. Test a finding that claims to predict on data held out from the data that found it.
4. Hand the draft to a red-team subagent briefed to do what a sceptic of that field does to break a claim; fix each break or state it as a limit.
5. Write the report to a file: findings, each citing its source; the most urgent decisions they raise, ranked, each with its case for and against; then each criterion with its command, result and output on the base; `comment` it on the task as `REPORTED:`.
6. A `judge` reviews the comment's url; answer its gaps in a new comment, judged again, until it approves.
