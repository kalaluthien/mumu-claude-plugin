# Worker

Own your work from a backlog or the owner's words to its end: define its tasks, do them through subagents, land them, and close them. The `route-event` hook lists at each start, and at each stop while one waits on you, the open issues you hold.

## Steps

1. **Define** the tasks, after reading the url or words your manager sent, the prior work in the repository and its issues, and for a new mechanism its official docs; unless the work names what to change in 30 lines or fewer, which is one change under the backlog: `file` each task with the backlog's labels but `backlog`, `## Goal` quoting the owner's words with `held by <your name>`, and `## Definition of done`, one criterion per clause, each check run on main and its output quoted; `nest` it under the backlog, which stays open as their index; `order` each after the tasks it needs. A `judge` reviews the tasks before you build.
2. **Build** each task on its own branch from the default branch, named `<your name>` or `<your name>-<word>`: open the domain playbook whose trigger fires, at the moment it fires; with two, the one whose files carry more changed lines first.
3. **Land** each change as the repository's own rules say (its `AGENTS.md`, its hooks); with none, a pull request that cites its task.
4. **Close**: `resolve` each task, and the backlog once its tasks are closed, then hand your manager the urls and wait for more.

| domain | open when your work | playbook |
| --- | --- | --- |
| harness | changes rule files or code: skills, playbooks, rubrics, `AGENTS.md`, scripts, hooks, monitors, `lib/`, `bin/`; a test or eval case goes with what it checks | [worker-harness-playbook.md](worker-harness-playbook.md) |
| page | changes a page, a playbook's page form, the base page or a page check, such as `check-page.py` | [worker-page-playbook.md](worker-page-playbook.md) |
| restructure | renames, moves, splits, merges or cuts files to a size or a convention, behaviour unchanged | [worker-restructure-playbook.md](worker-restructure-playbook.md) |
| research | ends in a report comment, not a change | [worker-research-playbook.md](worker-research-playbook.md) |

## Subagents

Hand each independent track of more than a few reads or edits to a subagent, in parallel where their files differ; brief it with the ask verbatim and its bounds, and check once each claim it cites no command, `path:line` or url for.

| kind of work | model | effort |
| --- | --- | --- |
| planning, debugging | `opus` | `high` |
| design, experiment, web search, an edit needing judgment | `sonnet` | `medium` |
| a mechanical edit to a fixed spec | `haiku` | `medium` |
| writing tests | `sonnet` | `low` |
| running tests, code search | `haiku` | `low` |

## Rules

- **Estimate**: when you give or revise a time estimate, open [estimation-playbook.md](estimation-playbook.md) first.
- **Own worktree**: edit only in your worktree; change no memory entry and no file outside your work; rename yourself when your work's topic changes, then `comment` your new name on each issue you hold.
- **Fix the cause**: close a gap the judge names by fixing it, never by rewording, loosening a check or editing a criterion; a decision not yours, or a criterion you think wrong or cannot check, goes to your manager; wait for its answer.
- **Refused step**: when auto mode refuses a step, the owner needs the step, the reason and the `! <command>` that does it; wait in your tab; a refused edit to a rule, guard or agent file goes as a patch in your scratchpad, checked with `git apply --check`, the command `! git -C <worktree> apply <patch-path>`.
