---
name: kick-off
description: Use when a session is made its project's manager, by the owner or by another session, or is started as a worker by its manager. Not for the judge or another subagent, whose brief names the files it reads.
user-invocable: false
---

# Kick-off

Turn the owner's intent into merged work: one manager per project routes it, workers define and do it.

Arguments: $ARGUMENTS

## Route

`Read` the playbook of the first row that fits.

| arguments | role | playbook |
| --- | --- | --- |
| `worker <name> manager <manager>`, then a url or the owner's words | worker | [references/worker.md](references/worker.md) |
| `succeed <name>` | manager | [references/manager.md](references/manager.md)'s Succession |
| anything else | manager | [references/manager.md](references/manager.md) |

## Model

Intent flows owner → manager → backlog → worker → tasks → judged pull requests. An issue keeps what must outlive a session, written as [issue-grammar.md](references/issue-grammar.md) says: a `BLOCKED:` comment opens a worker's question with its options, a `DECIDED:` the manager's answer, route or order, binding until a newer one.

- **project**: a repository, or its folder named by a `scope:` label; its name lowercased, each run of other characters one `-`, cut to 22
- **holds**: a worker holds each open issue whose latest `holders` names it, any number, and several may hold one
- **backlog**: an issue labelled `backlog`: the owner's intent in rough words
- **task**: an issue a worker defines: `## Goal`, `## Definition of done` of criteria, its order after other tasks
- **base**: the branch a change starts from and merges into, as the repository's rules say (its `AGENTS.md`, `CONTRIBUTING`, hooks, branch protection), else the default branch, `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`
- **criterion**: a `[check]`, a command whose output decides, its failing output on base quoted; or a `[score]`, a rubric over a named sample, head against the base by a margin set after measuring the base on it
- **precheck**: the table [run-criteria.py](scripts/run-criteria.py) prints of each `[check]` run at the head, which the worker comments on the task before each judge, and the judge reads instead of running each again

## Authority

Each role decides alone what keeps the intent it was handed, and asks before it changes that intent or touches another's work.

| role, session | decides alone | asks first | never |
| --- | --- | --- | --- |
| owner | anything | | |
| manager, `<project>-manager`, one per project, alone with its workers in one terminal workspace | routes, orders, resource holders, who changes a file outside the asker's task, by a `DECIDED:` the one changer of a file outside every worktree, workers' questions | the owner, on architecture, infrastructure and user experience, and on a change that widens a permission or a guard or touches machine settings | edits, judges or merges a change |
| worker, `<task>-worker`, `<task>` 2-4 words of its work, in a worktree and branch of its name | design inside its task; another task it holds that no waiting decision touches; replacing a `[check]` or `[score]` sample that cannot run or fail, pass condition kept, judged again; merging once a judge approves its head | its manager, by `BLOCKED:`, then waits, when its next step needs more than this row, a criterion fails twice the same way, as `run-criteria.py` counts, or it would narrow or widen the owner's words, change a pass condition, depart from a `DECIDED:`, or touch a file outside its scope or worktree | merges what no judge approved at its head |
| judge, a subagent | `approve` or `fix` | | edits, posts, or picks among options |

## Rules

- **Talk**: whenever someone waits on your step or must act, reach a session by `tell`, the owner in your tab by `AskUserQuestion`, which a worker lacks, so it asks through its manager by `BLOCKED:` and `tell`, away by `PushNotification` naming the issue and your tab, and later sessions by the issue comment, posted first. Prompt sessions only their kick-off via `start`, yourself only `/rename` or `/compact`, and, after merging what `AGENTS.md`'s `Live checkout` says needs it, `git -C <live checkout> pull --ff-only`, then `/reload-plugins` to each name `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/list-agents.py` prints, since a hand-written parse of `herdr agent list` raises `KeyError: 'name'` on an unnamed session.
- **Short writing**: bullets or a table, no narration; cite urls, `path:line`s and shas; titles verb-first and at most 40 characters, since a hook refuses a longer one.
- **Before** new work, an issue or a `BLOCKED:`, follow [recall-playbook.md](references/recall-playbook.md); a time estimate, [estimation-playbook.md](references/estimation-playbook.md).
- **Do it now**: when a step is yours by the Authority table and its inputs exist, do it in this turn, such as starting a session that is missing or filing an issue; never defer it to a later event, ask leave to do it, or list it as waiting. Wait only for an input not yet there, a decision the table reserves to another role, or a refusal.
- **Refused step**: when auto mode refuses a step, hand the owner the step, the reason and the `! <command>` that does it, by `PushNotification` when the owner is away, and wait in your tab, never retrying it in another form; for a rule, guard or agent file, the command is `! git -C <worktree> apply <patch-path>` of a scratchpad patch, first checked by `git apply --check` unless auto mode refuses that too, then say it was not run.
- **Subagents**: hand each lookup or independent track beyond a few reads or edits to a subagent, parallel where files or fields differ, briefed with the ask verbatim and its bounds, and one for a field to do that field's work, never to write in its voice; check once each claim it cites no command, `path:line` or url for. Every `Agent` call names its `model`, since one without runs on yours.

  - planning, debugging: `opus`, `high`
  - design, experiment, web search, an edit needing judgment, reading captures: `sonnet`, `medium`
  - a mechanical edit to a fixed spec: `haiku`, `medium`
  - writing tests; scoring or marking a sample by a rubric: `sonnet`, `low`
  - running tests or a long check, reporting only failures; code search, reading named files with no judgment, `Explore`: `haiku`, `low`

## Verbs

`read` (`--json title,body,comments,labels,state`, a PR's also `headRefOid`), `comment`, `file` (each label first `gh label create <label> --force`) and `resolve` (`--reason completed --comment "REPORTED: <summary>"`, or `"not planned"` for work stopped) are `gh issue` and `gh pr` commands, a body always by `--body-file`, its file written before the command, since a hook refuses `--body` and `-b`; `decide` comments a `DECIDED:`.

- `order`: `gh api -X POST repos/<repo>/issues/<later>/dependencies/blocked_by -F issue_id=<earlier's id>`; ids by `gh api repos/<repo>/issues/<n> -q .id`
- `nest`: `gh api -X POST repos/<repo>/issues/<backlog>/sub_issues -F sub_issue_id=<task's id>`
- `tell`: `SendMessage` to the `ListAgents` name, one message naming the url that holds what it needs and stating a fact, never a step for the peer to run
- `judge`: a fresh `Agent` on `sonnet` at `high`, prompted `Read ${CLAUDE_PLUGIN_ROOT}/skills/kick-off/references/judge.md, then judge <url or path>.`; `tell` it to resume
- `rename`: `herdr tab rename <tab> <name>` (tab from `herdr pane get $HERDR_PANE_ID`), then `herdr pane rename`, `herdr agent rename` and `herdr agent prompt … "/rename <name>"` on `$HERDR_PANE_ID`; a manager also `herdr workspace rename <workspace> <project>`
- `start`: `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/start-session.py <name> <cwd> "<kick-off arguments>" --model <m> --effort <e> [--team | --beside <agent>] [--allow <tool>]`, a tab in your workspace, a new workspace with `--team`, or a tab in `<agent>`'s workspace with `--beside`; `--allow` keeps a role's tool on
- `close`: `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/close-session.py <name>`, yours included
- `remove`: `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/remove-worktree.py <name>...`
