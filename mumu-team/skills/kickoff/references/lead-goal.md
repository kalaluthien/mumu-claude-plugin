# Lead

1. `name` yourself after your checkout's GitHub repository, or `<folder>-lead` as Folder leads says, unless already so named. Then ask the owner every question at once with `AskUserQuestion`.
2. `file` the work as Filing says: a root task when it is one task, a handed-off root goal relabelled `kind:task` and `effort:<effort>`; else a goal, the owner's expectations as its first `DECIDED:` comment, and under it one task per pull request or report, each labelled with its effort and each `## Definition of done` line a criterion. `order` by blocked-by each task that waits on another, and each goal or task that waits on another project's root goal or root task. Then launch the `reviewer` on the goal's or root task's url and fix its findings until it posts `APPROVED:`; on each replan, resume that same reviewer, naming only the issues that changed.
3. For each open task whose blockers are all closed: `start` it under its topic at its effort with `--leader <your address>`, or make a small change yourself.
4. Act on what arrives:
   - `see <task-url>` naming a `BLOCKED:` comment: answer it with `decide`, then `prompt` the worker `see <task-url>`; work that needs its own pull request is answered with the url of the task you `file` for it, `order`ed before this one, which then goes through 3;
   - `see <task-url>` naming a `BLOCKED:` on an auto-mode refusal: check the exact step it names (`merge.py`, the reviewer's approval, `git -C <worktree> rm` of tracked clean files), then run it yourself;
   - `see <pr-url>`, or `see <task-url>` of a report task closed at its `APPROVED:`: `read` it; once it shows merged or closed, `close` its worker, go to 3 for each task it unblocked, and when every issue under a goal is closed, or a root task closes, go to 5 for it;
   - `blocked <name>`: the worker waits at a tool-use prompt, which is the owner's to answer, so tell the owner;
   - `gone <name>` while its task is open: `start` it again with `--continue`;
   - `idle <name>`: `read` its task and pull request, answer what waits on you, else `prompt` the worker `see <task-url>`;
   - `team idle <m>m`, or you resumed: `read` each open root task and each open task of each root goal you hold, and its pull request or report comment, and act on each as if its notice had arrived;
   - `working <name>`: nothing; a monitor's expiry notice: arm the command the Stop hook names;
   - the owner changes direction: `decide` the change on each issue affected and `prompt` its worker `see <task-url>`; built work the owner rejects is replanned from the goal's definition of done into new tasks, its pull request closed unmerged and named in them as content to read, never form to follow;
   - the owner stops a task or goal: `stop` it and each open task and goal under it, deepest first, unless the owner keeps the goal open, `close` their workers, and `comment` on the goal each task, its pull request and what is left;
   - the owner asks where work stands: `read` each goal named, else each you hold, down to each task's pull request or report comment, and report one row per task: its state, that pull request or comment, and its worker's `agent_status` in `live`, or none.
5. `resolve` the goal with a summary, a root task being closed already, then `close` each of its workers and `clean`; a closed goal whose parent now holds nothing open goes through 5 in turn. When you then hold no open root goal or root task and no worker is live, `prompt` yourself `/compact Keep only: each goal and task closed this session with its url, PR and one-line result; open backlog issues; drop tool output.`

## Succession

Continue a lead's work from GitHub, in a session resumed or in a fresh one of the same name, never a restart.

Resume, and a successor once named:

1. Find the root goals and root tasks you hold with `gh issue list --state open --search "no:parent-issue label:kind:goal,kind:task" --json number,title,url`, with `--label scope:<folder>` added for a `<folder>-lead`, run in your checkout.
2. `read` each, the goals and tasks under it, and each task's pull request; `prompt` each worker in `live` whose worktree lies in your checkout `see <its task-url>`.
3. Continue at Lead 4, acting on each open task as if its notice had arrived.

The original, asked to hand over: `start-lead` your successor with `--succeed <your pane>` at your checkout root, passing after `--` the flags `ps -o args= -p $CLAUDE_PID` shows but the program, `--continue`, `--resume`, `--name` and `--agent`; then stop.

The successor, prompted `succeed <pane>`: `worker-close.py <name>`, `<name>` the original's name, which exits the original; `name` yourself that name, keeping the `scope:<folder>` of a `<folder>-lead`; then resume as above.

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
