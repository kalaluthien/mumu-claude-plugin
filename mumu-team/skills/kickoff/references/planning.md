# Planning

Route, file and split work, the only place routing rules live.

## Routing

Route every request, the owner's included, before taking it:

| the work is for | you |
| --- | --- |
| backlog: the owner's words kept for later, for any project | file them as said, labelled `kind:backlog`, in that project's repository, with the `scope:<folder>` routing picks where it has such labels; no parent, no format, no worker |
| this project, your cwd's checkout | take it as a goal or a root task, led from Lead 2; a handed-off goal is a root goal here until Lead 2 finds it one task. With `scope:` labels, it is yours only for your folder: by the plugin its words name, else the folder it touches, else the owner's to pick; another folder's goes to its lead as `handoff` step 3 says |
| another project | follow `${CLAUDE_PLUGIN_ROOT}/skills/handoff/SKILL.md`, read with `Read`, then `order` the work here that needs it after its root goal |
| every project: a shared rule or tool changing | `broadcast` its issue url |
| several projects | one root goal or root task per project, each routed as above |

A notice from another lead that is not a goal for you is answered by a plain `comment` on its issue.

## Filing

- Hold any number of root goals and root tasks at once. File a goal only when it holds two or more tasks, related or not; one task is a root task, a chore one at `effort:low`, and a goal too large for one level is split into goals.
- Search the issues first, `gh issue list -R <repo> --state all --search <words>`: work of the same kind as a closed issue (#67 and #84 both hid a skill from the `/` menu) reopens it with `gh issue reopen`, widens its criteria with `decide.py --criteria` and is led under a new attempt; otherwise file a new issue that links it.
- File the fewest tasks at the widest scope: work sharing a mechanism is one task, split by feature, never by layer, and a new finding or a review's defect widens the task it relates to. File them all, then write the order and cross-references.
- A defect you find is fixed in the current work or filed as a task of the current goal, and you say which; noted on an issue with no owner, it is dropped.
- Research whose result later pull requests read is a task with a worker, driven one step per prompt, never a subagent whose result lives only in scratch.
- A hunch the owner asks you to interpret goes in as `reading: <yours>` beside their words, never as their decision.
- Ask the owner only architecture, infrastructure and user-experience questions, all at once with `AskUserQuestion`, and have them confirm only those criteria; decide the rest and record it as `DECIDED:` on the goal.

## Small change

The one change you make yourself: the owner's words spell it out, in one file and about 5 changed lines, with no script logic. Make it in a worktree off the default branch, `pr` it on the task reopened or filed for it, launch the `reviewer` with the model `review-model.py` prints, `merge` it at its `APPROVED:` head, and remove the worktree and branch as `clean` does.

## Folder leads

A repository with `scope:<folder>` labels (`gh label list --search scope:`) runs one lead per plugin folder, each at the checkout root, and no `<repo>-lead`.

- Your folder is the `scope:` label of the goal you were started or handed, else the plugin folder its words name: `name` yourself `<folder>-lead`. Label `scope:<folder>` each root goal and root task you hold, and add `--label scope:<folder>` to every `gh issue list` of them.
- Act only on a worker whose task is, or sits under, a root goal or root task you hold: `team-watch` lists every worker of the checkout.
- Before changing another folder's files, taking a goal across folders, or a shared operation (`clean`'s pull, `/reload-plugins`), propose it through `SendMessage` to every live lead concerned, found with `ListAgents`, and act after their answers; only what it leads to is recorded. An objection: revise and ask again; two proposals colliding: the first sent wins; past two objections, or no answer after one resend: ask the owner. Work across folders is led by the lead that received it first.
