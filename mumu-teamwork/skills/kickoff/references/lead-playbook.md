# Lead

1. `rename` yourself what `lead-name.py [<task-url>]` prints, unless already so named, and run `${CLAUDE_PLUGIN_ROOT}/skills/kickoff/scripts/repo-settings.py <checkout>`. Then ask the owner as Filing says.
2. `file` the work as Filing says: one root task per pull request or report, a handed-off one relabelled with its effort, the owner's expectations as its first `DECIDED:` and each `## Definition of done` line a criterion. `order` each task that waits on another, in this or another project's repository. Then launch the `judge` on each task's url until it posts `APPROVED:`; on a replan, name to it only the issues that changed.
3. For each open task whose blockers are all closed, and each share whose `after` shares have merged: `start` it under its topic or share at its effort with `--lead <your address>`, or make a small change yourself.
4. Act on what arrives, polling nothing, once per state GitHub shows:
   - `see <task-url>` naming a `BLOCKED:`: `decide` it, then `prompt` the worker `see <task-url>`; answer work that needs its own pull request with the url of the task you `file` and `order` before this one, a narrower scope included, which is a `checks.json` change and never granted on the worker's task;
   - `see <pr-url>`, `see <task-url>` of a report task, or `see <backlog-url>`: once `read` shows it merged, closed, or its survey's `APPROVED:`, go to 5 for it;
   - `blocked <name>`: tell the owner the worker waits at a tool-use prompt;
   - `gone <name>` while its task is open: `start` it again with `--continue`;
   - `idle <name>`: `read` its task and pull request, answer what waits on you, else `prompt` the worker `see <task-url>`;
   - `team idle <m>m`, `usage reset <time>: ...`, a monitor's expiry notice, a `/reload-plugins`, or you resumed: go to Succession;
   - `working <name>`: nothing;
   - the owner changes direction: `decide` the change on each issue affected and `prompt` its worker `see <task-url>`; replan built work the owner rejects on the same task, as Filing's reopen says, its pull request closed unmerged and named on the task; build from its content, never its form;
   - the owner stops a task: `stop` it, `close` its worker, and `comment` on it its pull request and what is left;
   - the owner asks where work stands: `read` each task named, else each you hold, and report one row per task: its state, its pull request or report comment, and its worker's `agent_status` in `live`, or none.
5. Work done: `close` its worker and `clean`; go to 3 for each task it unblocked. When you then hold no open root task and no worker is live, propose to exit to every other live lead `ListAgents` shows, of any repository; once each answers `OK`, run `session-close.py --self`. The only live lead, or one given an objection, stays and `prompt`s itself `/compact Keep only: each task closed this session with its url, PR and one-line result; open backlog issues; drop tool output.` While your own exit proposal is pending, object to another lead's.

## Succession

Continue a lead's work from GitHub, in a session resumed or in a fresh one of the same name, never a restart.

The original, asked to hand over: `start-lead` your successor with `--succeed <your pane>` at your checkout root; then stop.

The successor, prompted `succeed <pane>`: `close` the original by its name, and `rename` yourself that name.

Then, and on resuming:

1. Arm the command the Stop hook names when no team-watch of yours is live.
2. List the root tasks you hold with `gh issue list --state open --search "no:parent-issue -label:backlog" --json number,title,url` in your checkout.
3. `read` each and its pull request or report comment; `prompt` each worker in `live` whose worktree lies in your checkout `see <its task-url>`.
4. Continue at Lead 4, acting on each open task as if its notice had arrived.

## Routing

Route every request, the owner's included, before taking it:

| the work is for | you |
| --- | --- |
| backlog: the owner's words kept for later, for any project | `file` them as said, labelled `backlog` and, where the repository has them, `scope:<folder>`, in that project's repository, with no parent and no format; the owner asking to survey one: `start` it under a topic at effort low or medium with `--survey --lead <your address>`; the owner starting one: remove its `backlog` label and replace its body by the contract |
| this project | take it as a root task, from Lead 2; with `scope:` labels, only for your folder, found as `handoff` step 2 says, and another folder's goes to its lead |
| another project | follow `${CLAUDE_PLUGIN_ROOT}/skills/handoff/SKILL.md`, read with `Read`, then `order` the work here that needs it after its root task |
| every project: a shared rule or tool changing | `broadcast` its issue url |
| several projects | one root task per project, each routed as above |

Answer another lead's notice that is not a task for you with a plain `comment` on its issue.

## Filing

- Hold any number of root tasks at once, a chore one at `effort:low`.
- Open each criterion of a new task with its kind, `[exists]`, `[test]` or `[quality]`; a task filed before kinds keeps its criteria.
- Before posting a plan's criteria, run each "no FAIL" guard they name on main, and confirm each criterion's check still reads its input once the change lands.
- Give a task that changes how work is split, run, reviewed or tested a criterion replaying past merged pull requests, their checks and session transcripts against the change, because a process change argued only from its design misses the cases history already holds.
- Search the issues first, `gh issue list -R <repo> --state all --search <words>`. Reopen a closed issue of the same kind of work: `gh issue reopen`, then `decide` with `--criteria` to widen its criteria, then `gh issue edit --title --body-file` to rewrite its title and `## Goal` to the new gap, each after the last, never in parallel, and grep the body for the old wording; lead it under a new attempt. When its fixes touch files another open task rewrites, `decide` on both which task owns each fix and `order` them, before the judge. Otherwise `file` a new issue that links it.
- File the fewest tasks at the widest scope: work sharing a mechanism is one task, split by feature, never by layer; a new finding or a judge's defect widens the task it relates to. File them all, then `order` them and write the cross-references.
- Split work, into tasks or a task into shares, only where its order has slack and its conflict can be made indirect: one merge at the end is enough, an interface agreed first lets each part be built apart, or what the parts share is knowledge each only reads.
- Fix a defect you find in the current work or `file` it as its own task, and say which.
- `file` research that later pull requests build on as a task with a worker, driven one step per prompt; run research for your own judgement, or in a skill the owner invokes, in subagents, and give its result to the owner or an issue.
- Put a hunch the owner asks you to interpret as `reading: <yours>` beside their words, never as their decision.
- Ask the owner only architecture, infrastructure and user-experience questions, all at once with `AskUserQuestion`, and have them confirm only those criteria; decide the rest and `decide` it on the task.
- `file` a user-experience question with an industry best practice as a research task first, and ask the owner after its report.
- Before asking the owner, search earlier `DECIDED:` comments and closed issues for the same case, `gh search issues "<words>" -R <repo> --include-prs`; found, follow that decision and tell the owner, citing its url.

## Shares

- Add `## Shares` to a split task's body, each share's `with` one of `merge at the end`, `interface agreed first` or `knowledge read only`; run shares in parallel, else in sequence by `after`.
- `decide` each interface agreed first on the task before its shares start.
- `resolve` the task once every share has merged.

## Small change

Make one change yourself only when the owner's words spell it out, in one file and about 5 changed lines, with no script logic: in a worktree off the default branch, `pr` it on the task reopened or filed for it, run the checks `scope` prints, the `judge` among them when printed, `merge` it, and remove the worktree and branch as `clean` does.

## Folder leads

In a repository with `scope:<folder>` labels (`gh label list --search scope:`):

- Your folder is the one your `<folder>-lead` name was started with, else the `scope:` label of the task you were started or handed, else the plugin folder its words name, labelled on it first. Label `scope:<folder>` each root task you hold, and add `--label scope:<folder>` to every `gh issue list` of them.
- Before changing another folder's files, taking a task across folders that you received first, or a shared operation (`clean`'s pull, `/reload-plugins`), send a proposal to every live lead concerned; of two proposals colliding, the first sent wins.
