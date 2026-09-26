# Lead

Lead a goal to reviewed, merged pull requests.

1. `name` yourself after your checkout's GitHub repository, unless already so named; `team-watch` starts with this skill, and the Stop hook names the command to arm it again once you hold a root goal and it is not running. Then ask the owner every question at once with `AskUserQuestion`.
2. `file` the goal, the owner's expectations as its first `DECIDED:` comment, and under it one task per pull request, or a goal per part too large for one level, reopening a closed issue of the same kind instead of filing one, each task labelled with its effort and each `## Definition of done` line a criterion; work for another project is routed as a root goal there, not filed here. `order` by blocked-by each task that waits on another, and each goal that waits on another project's root goal. Then launch the `reviewer` on the goal's url and fix its findings until it posts `APPROVED:`; on each replan, resume that same reviewer with `SendMessage`, naming only the issues that changed.
3. For each open task whose blockers are all closed: `start` it under its topic at its effort with the prompt `/mumu-team:kickoff work <task-url> leader <your address>`; a small change you make yourself, as your rules say.
4. Act on what arrives:
   - `see <task-url>` naming a `BLOCKED:` comment: answer it with `decide.py <task-url>`, with `--criteria` when a criterion changes, then `prompt` the worker `see <task-url>`; when it asks for work that needs its own pull request, the answer is the url of the task you `file` for it, `order`ed before this one, which then goes through 3;
   - `see <pr-url>`: `read` it; once it shows merged, `close` its worker, go to 3 for each task it unblocked, and when every issue under a goal is closed, go to 5 for that goal;
   - `see <task-url>` naming a `BLOCKED:` on an auto-mode refusal: check the exact step it names (`merge.py`, the reviewer's approval, `git -C <worktree> rm` of tracked clean files), then run it yourself;
   - `blocked <name>`: the worker waits at a tool-use prompt, which is the owner's to answer, so tell the owner;
   - `gone <name>` while its task is open: `start` it again with `--continue`, resuming its worktree;
   - `idle <name>`: `read` its task and pull request, answer what waits on you, else `prompt` the worker `see <task-url>`;
   - `team idle <m>m`: it reconciles lost notices: `read` each open task of each root goal you hold and its pull request, and act on each as if its notice had arrived;
   - `working <name>`: nothing;
   - a monitor's expiry notice: arm the command the Stop hook names;
   - the owner changes direction: `decide.py` the change on each issue affected, with `--criteria` when a criterion changes, and `prompt` its worker `see <task-url>`; built work the owner rejects is replanned from the goal's definition of done into new tasks, its pull request closed unmerged and named in them as content to read, never form to follow;
   - the owner stops one task: `stop` it and `close` its worker;
   - the owner asks where it stands: report each task and its worker in `live`.
5. `resolve` the goal with a summary, then `close` each of its workers still live and `clean`; a closed goal whose parent now holds nothing open goes through 5 in turn.
