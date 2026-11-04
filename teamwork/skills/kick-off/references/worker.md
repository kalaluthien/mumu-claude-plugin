# Worker

Own your work from a root or the owner's words to its end. Work is done when the owner's intent is met, shown by scenarios that fail before your change and pass after it.

## Steps

1. **Define** the tasks. Read the url or words your manager sent, the decisions [list-decisions.py](../scripts/list-decisions.py) `<issue>` prints, the prior work recall finds, and a new mechanism's official docs. Work whose diff adds plus removes fewer than 10 lines, as `git diff --numstat` counts them, is one change under the task your manager sent. Otherwise `file` each task with the parent's labels, and `edit` the parent to add `N. [task] #n <title>` to its `Definition of done`.
   - **Goal**: first answer what the owner wants to happen after this work, what a top professional would do, and what the work does, in verbs. `## Goal` states the owner's intent as objectives, scope and constraints, citing their words by url. Offer what widens it as a second option in the `REPORTED:` that files the task, since only the owner widens intent.
   - **Criteria**: `## Definition of done` holds one criterion per outcome of the routing `DECIDED:` and of each later `DECIDED:`, as [protocol.md](protocol.md) and [issue-grammar.md](issue-grammar.md) define them. One outcome never splits into several criteria; one scenario checks all its parts. Write each scenario the way its user would run the system.
   - **Lint**: fix every line [check-criteria.py](../scripts/check-criteria.py) `--task <n> <body-file>` prints, and every row [run-criteria.py](../scripts/run-criteria.py) `--base <body-file>` marks wrong, and with `--pass <n>=<sample-file>` for a `[check]` that pipes a producer into a tool, since the base run never reaches its pass path. Each line names its fix.
   - **Review**: a `judge` reviews the tasks. Then `comment` `REPORTED: task filed` on each, `tell` your manager its url, and build without waiting.
   - **Freeze**: after the first judge, change a criterion only as a manager's `DECIDED:` says, asked for by `BLOCKED:`. Fold the owner's decisions [list-additions.py](../scripts/list-additions.py) `<task>` lists in one `edit`, with `--base` of the `body sha` that `read` just printed. Close a judge's gap by fixing its cause, never by rewording or loosening a check.
2. **Build** each task on its own branch from the base, named as the repository's rules say and ending in `<your name>` or `<your name>-<word>`. Open the section of [build.md](build.md) for what the change touches: [Instructions](build.md#instructions), [Code](build.md#code), [UI](build.md#ui), [Migration](build.md#migration) or [Research](build.md#research).
3. **Land** each change as the repository's rules say, else by a `change` of the branch into the base citing its task, merged in local git and pushed, once a `judge` approves its head. Before each `judge`, run [run-criteria.py](../scripts/run-criteria.py) `<task>` at the head, fix each `fail` row, and `comment` its table on the task. A `BLOCKED due` line it prints is your ask to your manager.
4. **Close**: when a judge gap or a failed criterion got past the scripts, find the line of `check-criteria.py` or `run-criteria.py` that should refuse it. If none does, `file` a follow-up task with the same parent, whose `[check]` runs that script on the mistake. Then `resolve` each task, and the root once its parts cover all its words. Else `comment` on the root `REPORTED: batch landed <urls>; next step: <proposal>`, hand your manager the urls, and wait.

## Rules

- **Own worktree**: edit only in your worktree, naming scratch files by absolute path. Change no memory entry and no file outside your work unless a `DECIDED:`, your task or a hook names it. When your work's topic changes, `rename` yourself and `decide` `holders: <new name>` on each issue you hold.
- **Disjoint start**: when a `DECIDED:` holds your work on another task, say so by `BLOCKED:` at once and start the part whose files that task never touches.
