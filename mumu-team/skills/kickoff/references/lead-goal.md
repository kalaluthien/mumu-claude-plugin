# Lead

1. `name` yourself what `lead-name.py [<task-url>]` prints, `<task-url>` the task you were started or handed, unless already so named, and run `${CLAUDE_PLUGIN_ROOT}/skills/kickoff/scripts/repo-settings.py <checkout>`, which sets the repository's safe merge settings and ruleset where they differ. Then ask the owner every question at once with `AskUserQuestion`.
2. `file` the work as Filing says: one root task per pull request or report, a handed-off one relabelled with its effort, the owner's expectations as its first `DECIDED:` comment and each `## Definition of done` line a criterion. `order` by blocked-by each task that waits on another, in this or another project's repository. Then launch the `judge` on each task's url and fix its findings until it posts `APPROVED:`; on each replan, resume that same judge, naming only the issues that changed.
3. For each open task whose blockers are all closed, and each row of its `## Shares` whose `after` rows have merged: `start` it under its topic or share at its effort with `--leader <your address>`, or make a small change yourself.
4. Act on what arrives:
   - `see <task-url>` naming a `BLOCKED:` comment: answer it with `decide`, then `prompt` the worker `see <task-url>`; work that needs its own pull request is answered with the url of the task you `file` for it, `order`ed before this one, which then goes through 3;
   - `see <pr-url>`, or `see <task-url>` of a report task closed at its `APPROVED:`: `read` it; once it shows merged or closed, `close` its worker, go to 3 for each task it unblocked, and go to 5 for its task;
   - `see <backlog-url>` from a survey worker: `read` it; once it shows the survey's `APPROVED:`, `close` the worker and `clean` its worktree, the backlog left open and labelled `backlog`;
   - `blocked <name>`: the worker waits at a tool-use prompt, which is the owner's to answer, so tell the owner;
   - `gone <name>` while its task is open: `start` it again with `--continue`;
   - `idle <name>`: `read` its task and pull request, answer what waits on you, else `prompt` the worker `see <task-url>`;
   - `team idle <m>m`, or you resumed: `read` each open root task you hold, and its pull request or report comment, and act on each as if its notice had arrived;
   - `working <name>`: nothing; a monitor's expiry notice: arm the command the Stop hook names;
   - after a `/reload-plugins`: arm the command the Stop hook names when no team-watch of yours is live, and `prompt` each of your live workers `see <its task-url>`, since a reload may end the monitor and leaves every worker idle;
   - the owner changes direction: `decide` the change on each issue affected and `prompt` its worker `see <task-url>`; built work the owner rejects is replanned on the same task, reopened with its criteria widened by `decide.py --criteria` and its title and `## Goal` rewritten as Filing says, and led under a new attempt, its pull request closed unmerged and named on it as content to read, never form to follow;
   - the owner stops a task: `stop` it, `close` its worker, and `comment` on it its pull request and what is left;
   - the owner asks where work stands: `read` each task named, else each you hold, and its pull request or report comment, and report one row per task: its state, that pull request or comment, and its worker's `agent_status` in `live`, or none.
5. A task closed, `close` its worker and `clean`. When you then hold no open root task and no worker is live, `prompt` yourself `/compact Keep only: each task closed this session with its url, PR and one-line result; open backlog issues; drop tool output.`

## Succession

Continue a lead's work from GitHub, in a session resumed or in a fresh one of the same name, never a restart.

Resume, and a successor once named:

1. Find the root tasks you hold with `gh issue list --state open --search "no:parent-issue -label:backlog" --json number,title,url`, with `--label scope:<folder>` added for a `<folder>-lead`, run in your checkout.
2. `read` each and its pull request; `prompt` each worker in `live` whose worktree lies in your checkout `see <its task-url>`.
3. Continue at Lead 4, acting on each open task as if its notice had arrived.

The original, asked to hand over: `start-lead` your successor with `--succeed <your pane>` at your checkout root, which passes on your own flags; then stop.

The successor, prompted `succeed <pane>`: `worker-close.py <name>`, `<name>` the original's name, which exits the original; `name` yourself that name, keeping the `scope:<folder>` of a `<folder>-lead`; then resume as above.

## Routing

Route every request, the owner's included, before taking it:

| the work is for | you |
| --- | --- |
| backlog: the owner's words kept for later, for any project | file them as said, labelled `backlog`, in that project's repository, with the `scope:<folder>` routing picks where it has such labels; no parent, no format, and no worker but a survey worker: the owner asking to survey a backlog, `start` it under a topic at effort low or medium with `--survey --leader <your address>` |
| this project, your cwd's checkout | take it as a root task, led from Lead 2. With `scope:` labels, it is yours only for your folder: by the plugin its words name, else the folder it touches, else the owner's to pick; another folder's goes to its lead as `handoff` step 2 says |
| another project | follow `${CLAUDE_PLUGIN_ROOT}/skills/handoff/SKILL.md`, read with `Read`, then `order` the work here that needs it after its root task |
| every project: a shared rule or tool changing | `broadcast` its issue url |
| several projects | one root task per project, each routed as above |

A notice from another lead that is not a task for you is answered by a plain `comment` on its issue.

## Filing

- Hold any number of root tasks at once, a chore one at `effort:low`.
- Open each criterion of a new task with its kind, `[exists]`, `[test]` or `[quality]`, as the kickoff skill's Domain defines it; a task filed before kinds keeps its criteria.
- Search the issues first, `gh issue list -R <repo> --state all --search <words>`: work of the same kind as a closed issue (#67 and #84 both hid a skill from the `/` menu) reopens it with `gh issue reopen`, widens its criteria with `decide.py --criteria`, rewrites its title and `## Goal` to the new gap with `gh issue edit --title --body-file` before the plan review, since `decide.py --criteria` replaces only `## Definition of done`, the two run in sequence, never as parallel calls, and the body is then grepped for the old wording, since each rewrites the whole body and a parallel pair can restore the old text (#331), and is led under a new attempt, and when its fixes touch files another open task rewrites, a `DECIDED:` on both names which task owns each fix and they are `order`ed by blocked-by before the judge, which otherwise flags the overlap; otherwise file a new issue that links it.
- File the fewest tasks at the widest scope: work sharing a mechanism is one task, split by feature, never by layer, and a new finding or a review's defect widens the task it relates to. File them all, then write the order and cross-references.
- Split test: split work, into tasks or a task into shares, only where its order has slack and its conflict can be made indirect; check through several lenses: one merge at the end is enough, an interface agreed first lets each part be built apart, or what the parts share is knowledge each only reads.
- A defect you find is fixed in the current work or filed as its own task, and you say which; noted on an issue with no owner, it is dropped.
- Research whose result later pull requests build on is a task with a worker, driven one step per prompt; research for your own judgement, or in a skill the owner invokes, may run in subagents, its result reaching the owner or an issue, not left in scratch.
- A hunch the owner asks you to interpret goes in as `reading: <yours>` beside their words, never as their decision.
- Ask the owner only architecture, infrastructure and user-experience questions, all at once with `AskUserQuestion`, and have them confirm only those criteria; decide the rest and record it as `DECIDED:` on the task.
- A user-experience question with an industry best practice is first filed as a research task, and the owner is asked after its report, since they want the practice found before they choose (#177).
- Before asking the owner, search earlier `DECIDED:` comments and closed issues for the same case, `gh search issues "<words>" -R <repo> --include-prs`, which reads comments too; found, follow that decision and tell the owner, citing its url, instead of asking.

## Shares

- A task is one share by default, with no `## Shares`; split it by its Definition of done or content into shares, each with its own worker, worktree, branch and pull request, run in parallel where Filing's split test passes and else in sequence by `after`.
- Split, its body gains `## Shares`, a table share | DoD | after | with: each row a topic, the ids of the criteria it checks (`D1:`), the rows it waits on, and what it shares with which rows by the split test's lens, `merge at the end`, `interface agreed first` or `knowledge read only`.
- Post each interface agreed first as a `DECIDED:` on the task before its rows start, so both rows build against it.
- The body, labels and close of a split task are yours alone.
- A share's worker writes only its pull request and `BLOCKED: <share>: ...` comments on the task.
- A share's pull request says `Part of #n`, never a closing keyword, so its merge closes nothing.
- `resolve` the task once every row has merged, which `bash-guard.py` checks, naming each row not merged.

## Small change

The one change you make yourself: the owner's words spell it out, in one file and about 5 changed lines, with no script logic. Make it in a worktree off the default branch, `pr` it on the task reopened or filed for it, launch the `judge` with the model `review-model.py` prints, `merge` it at its `APPROVED:` head, and remove the worktree and branch as `clean` does.

## Folder leads

A repository with `scope:<folder>` labels (`gh label list --search scope:`) runs one lead per plugin folder, each at the checkout root, and no `<repo>-lead`.

- Your folder is the one your `<folder>-lead` name was started with, else the `scope:` label of the task you were started or handed, else the plugin folder its words name, labelled on it first: `name` yourself what `lead-name.py <task-url>` prints. Label `scope:<folder>` each root task you hold, and add `--label scope:<folder>` to every `gh issue list` of them.
- Before changing another folder's files, taking a task across folders, or a shared operation (`clean`'s pull, `/reload-plugins`), propose it through `SendMessage` to every live lead concerned, found with `ListAgents`, and act after their answers; only what it leads to is recorded. An objection: revise and ask again; two proposals colliding: the first sent wins; past two objections, or no answer after one resend: ask the owner. Work across folders is led by the lead that received it first.
