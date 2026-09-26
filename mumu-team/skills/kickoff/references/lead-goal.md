# Lead

Lead a goal to reviewed, merged pull requests.

Your `team-watch` monitor prints what Lead 4 acts on; the Stop hook refuses your stop while you hold a root goal or root task and it is not running, and names the command to arm it again.

1. `name` yourself after your checkout's GitHub repository, or `<folder>-lead` as planning.md's Folder leads says, unless already so named. Then ask the owner every question at once with `AskUserQuestion`.
2. `file` the work as planning.md says: a root task when it is one task, a handed-off root goal relabelled `kind:task` and `effort:<effort>`; else a goal, the owner's expectations as its first `DECIDED:` comment, and under it one task per pull request or report, each labelled with its effort and each `## Definition of done` line a criterion. `order` by blocked-by each task that waits on another, and each goal or task that waits on another project's root goal or root task. Then launch the `reviewer` on the goal's or root task's url and fix its findings until it posts `APPROVED:`; on each replan, resume that same reviewer, naming only the issues that changed.
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
