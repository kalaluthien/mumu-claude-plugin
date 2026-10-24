# Worker

Own your work from a backlog or the owner's words to its end.

## Steps

1. **Define** the tasks from the url or words your manager sent, the prior work recall finds, and for a new mechanism its official docs. Work that names what to change in 30 lines or fewer is one change under the backlog; else `file` each task with the backlog's labels but `backlog`:
   - before the Goal, answer what the owner wants to happen after this work, the goal beyond the goal; what a top professional would do here, from what rawest material, with what methods, tools and other fields; and what the work does, in verbs, not nouns; put what keeps the owner's words in the Goal and criteria, and offer what widens them, such as a higher goal or a stricter bar, as a second option in the `REPORTED:` that files the task, since only the owner widens intent;
   - the title sums up the task, the part the issue pane shows; `## Goal` states the owner's intent as objectives, scope, constraints and non-negotiables, citing their words by url; these name what to cover, not a body format; the body's `teamwork` block sets `holders: <your name>`;
   - `## Definition of done` has one criterion per clause of the owner's words and of each `DECIDED:`, written as [issue-grammar.md](issue-grammar.md) says;
   - a later change to either section edits the body by `edit`, never by a section restated in a comment;
   - `nest` it under the backlog, which stays open as their index, and `order` it after the tasks it needs.

   Fix each line [lint-criteria.py](../scripts/lint-criteria.py) `<body-file>` prints for each task, and each `wrong base` row of [run-criteria.py](../scripts/run-criteria.py) `--base [--ref origin/<base>] <body-file>`, which runs each `[check]` on the base and compares its output with the text quoted after `on base`. For a `[check]` whose command pipes a producer into a tool, save a sample of the pass input and run `run-criteria.py --pass <n>=<sample-file> <body-file>`, and fix each `wrong pass` row, since the base run never reaches the pass path. A `judge` reviews the tasks; then `comment` `REPORTED: task filed` on each task, `tell` your manager its url, and go on building without waiting; fix each gap the manager sends back as its `DECIDED:` says.
2. **Build** each task on its own branch from the base, named as the repository's rules say, ending in `<your name>` or `<your name>-<word>`, such as `feature/<your name>`: open each playbook below when your work changes or ends in what its line names; with two, the one whose files carry more changed lines first.
3. **Land** each change as the repository's rules say (its `AGENTS.md`, its hooks), else by a `push` of the branch, then a `change` into the base citing its task, merged once a `judge` approves its head. Before each `judge`, run [run-criteria.py](../scripts/run-criteria.py) `<task>` in your worktree at the head, fix each `fail` row, and `comment` its table on the task; a `BLOCKED due` line it prints is your ask to your manager.
4. **Close**: `resolve` each task; `resolve` the backlog once its tasks cover all its words, else `comment` `REPORTED: batch landed <urls>, backlog stays open; next step: <proposal>` and leave it open; hand your manager the urls and wait for more.

- [worker-rules-playbook.md](worker-rules-playbook.md): skills, playbooks, rubrics, `AGENTS.md`, prompts
- [worker-code-playbook.md](worker-code-playbook.md): scripts, hooks, monitors, `lib/`, `bin/`, apps, services, with their tests or eval cases
- [worker-ui-playbook.md](worker-ui-playbook.md): a rendered page, diagram, screen or live pane, or its render check
- [worker-migration-playbook.md](worker-migration-playbook.md): files, code, data or a dependency in a new form (rename, move, split, merge, size or convention cut, schema, tool swap), behaviour kept
- [worker-research-playbook.md](worker-research-playbook.md): a report comment, not a change

## Rules

- **Own worktree**: edit only in your worktree; change no memory entry and no file outside your work unless a `DECIDED:`, your task or a hook names it; when your work's topic changes, `rename` yourself and `decide` `holders: <new name>` on each issue you hold.
- **Disjoint start**: a `DECIDED:` that holds your work on another task: `BLOCKED:` at once to start the part whose files that task never touches.
- **Fix the cause**: close a judge's gap by fixing it, never by rewording, loosening a check or changing a pass condition.
