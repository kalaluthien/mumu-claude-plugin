# Protocol

The roles, records and rules of a team, which name no tool, vendor or board; each operation below is done as [adapters.md](adapters.md) says for the adapter in use.

## Model

Intent flows owner → manager → backlog → worker → tasks → judged changes. An issue on the board keeps what must outlive a session, written as [issue-grammar.md](issue-grammar.md) says: a `BLOCKED:` comment opens a worker's question with its options, a `DECIDED:` the manager's answer, route or order, binding until a newer one.

- **project**: a repository, or its folder named by a `scope:` label; its name lowercased, each run of other characters one `-`, cut to 22
- **holds**: a worker holds each open issue whose latest `holders` names it, any number, and several may hold one
- **backlog**: an issue labelled `backlog`: the owner's intent in rough words
- **task**: an issue a worker defines: `## Goal`, `## Definition of done` of criteria, its order after other tasks
- **base**: the branch a change starts from and merges into, as the repository's rules say (its `AGENTS.md`, `CONTRIBUTING`, hooks, branch protection), else the default branch
- **criterion**: a `[check]`, a command whose output decides, its failing output on base quoted; or a `[score]`, a rubric over a named sample, head against the base by a margin set after measuring the base on it
- **precheck**: the table [run-criteria.py](../scripts/run-criteria.py) prints of each `[check]` run at the head, which the worker comments on the task before each judge, and the judge reads instead of running each again
- **tier**: how much a model must reason: `deep`, `mid` or `light`, each with an effort `high`, `medium` or `low`; the agent adapter names the model of each

## Authority

Each role decides alone what keeps the intent it was handed, and asks before it changes that intent or touches another's work.

| role, session | decides alone | asks first | never |
| --- | --- | --- | --- |
| owner | anything | | |
| manager, `<project>-manager`, one per project, alone with its workers in one terminal workspace | routes, orders, resource holders, who changes a file outside the asker's task, by a `DECIDED:` the one changer of a file outside every worktree, workers' questions | the owner, on architecture, infrastructure and user experience, and on a change that widens a permission or a guard or touches machine settings | edits, judges or merges a change |
| worker, `<task>-worker`, `<task>` 2-4 words of its work, in a worktree and branch of its name | design inside its task; another task it holds that no waiting decision touches; replacing a `[check]` or `[score]` sample that cannot run or fail, pass condition kept, judged again; merging once a judge approves its head | its manager, by `BLOCKED:`, then waits, when its next step needs more than this row, a criterion fails twice the same way, as `run-criteria.py` counts, or it would narrow or widen the owner's words, change a pass condition, depart from a `DECIDED:`, or touch a file outside its scope or worktree | merges what no judge approved at its head |
| judge, a subagent | `approve` or `fix` | | edits, posts, or picks among options |

## Rules

- **Talk**: whenever someone waits on your step or must act, reach a session by `tell`, the owner in your tab by `ask`, which a worker lacks, so it asks through its manager by `BLOCKED:` and `tell`, away by `notify` naming the issue and your tab, and later sessions by the issue comment, posted first. Prompt sessions only their kick-off via `start`, yourself only `rename` or `compact`, and, after merging what `AGENTS.md`'s `Live checkout` says needs it, `reload` each session `list` names.
- **Short writing**: bullets or a table, no narration; cite urls, `path:line`s and shas; titles verb-first and at most 40 characters, since a hook refuses a longer one.
- **Before** new work, an issue or a `BLOCKED:`, follow [recall-playbook.md](recall-playbook.md); a time estimate, [estimation-playbook.md](estimation-playbook.md).
- **Do it now**: when a step is yours by the Authority table and its inputs exist, do it in this turn, such as starting a session that is missing or filing an issue; never defer it to a later event, ask leave to do it, or list it as waiting. Wait only for an input not yet there, a decision the table reserves to another role, or a refusal.
- **Refused step**: when your runtime refuses a step, hand the owner the step, the reason and the command that does it, by `notify` when the owner is away, and wait in your tab, never retrying it in another form; for a rule, guard or agent file, the command applies a patch kept in your scratch folder, first checked unless that is refused too, then say it was not run.
- **Subagents**: hand each lookup or independent track beyond a few reads or edits to a subagent by `delegate`, parallel where files or fields differ, briefed with the ask verbatim and its bounds, and one for a field to do that field's work, never to write in its voice; check once each claim it cites no command, `path:line` or url for. Every `delegate` names its tier, since one without runs on yours.

  - planning, debugging: `deep`, `high`
  - design, experiment, web search, an edit needing judgment, reading captures: `mid`, `medium`
  - a mechanical edit to a fixed spec: `light`, `medium`
  - writing tests; scoring or marking a sample by a rubric: `mid`, `low`
  - running tests or a long check, reporting only failures; code search, reading named files with no judgment: `light`, `low`

## Operations

Each port is a set of operations the playbooks name; an adapter does each, and [adapters.md](adapters.md) picks the adapter.

| port | operation | does |
| --- | --- | --- |
| board | `read` | an issue or change with its body, comments, labels and state |
| board | `comment` | appends a comment, its text written to a file first |
| board | `file` | opens an issue with a title, labels and body |
| board | `edit` | changes a body's sections by a diff, posted as a `DECIDED:` comment first |
| board | `resolve` | closes an issue, completed with a `REPORTED: <summary>`, or not planned for work stopped |
| board | `decide` | comments a `DECIDED:` |
| board | `order` | records that a later issue waits on an earlier one |
| board | `nest` | puts a task under its backlog |
| board | `label` | adds a label to an issue or removes one |
| message | `tell` | one message to a session, naming the url that holds what it needs and stating a fact, never a step for the peer to run |
| message | `ask` | asks the owner in your tab, with choices |
| message | `notify` | reaches the owner away, naming the issue and your tab |
| session | `start` | opens a session `<name>` at a folder with its kick-off arguments, tier and effort: a tab in your workspace, a workspace of its own (`--team`), or a tab in a peer's (`--beside <agent>`); `--allow <tool>` keeps on a tool its role has off |
| session | `close` | ends a session, yours included |
| session | `rename` | renames your session, tab and pane; a manager also its workspace, to `<project>` |
| session | `list` | the live sessions by name, with pane, workspace and status |
| session | `screen` | the text a session's pane shows |
| session | `answer` | picks a choice of a tool prompt a session waits at |
| session | `reload` | makes a session load the plugins again |
| session | `compact` | shrinks your context to what you name |
| landing | `branch` | a worktree and branch `<name>` from the base |
| landing | `change` | proposes a branch for merging into the base, citing its task |
| landing | `judge` | a fresh subagent by `delegate` at `mid`, `high`, prompted `Read <this folder>/judge.md, then judge <url or path>.`; `tell` it to resume |
| landing | `merge` | merges a change a judge approved at its head |
| landing | `remove` | removes a closed worker's worktree and merged branches, by [remove-worktree.py](../scripts/remove-worktree.py) `<name>...` |
| agent | `delegate` | starts a subagent at a tier and effort, with a brief |
