# Lead

Lead a goal to reviewed, merged pull requests.

1. `name` yourself after your checkout's GitHub repository, unless already so named, write your mission's `GOAL:` line so your monitors keep running, then ask the owner every question at once with `AskUserQuestion`.
2. `file` the parent, the owner's expectations among its decisions, and one issue per pull request, each labelled with its effort and each `## Definition of done` line a criterion; work for another project is routed, not filed here. Add the goal to your mission, then launch the `reviewer` on the parent's url and fix its findings until it posts `APPROVED:`.
3. For each issue: `checkout` it in your own checkout, `start` it under its name at its effort, add its `WORKER:` line to your mission, and `prompt` it `/mumu-team:kickoff work <issue-url> leader <your address>`.
4. Act on what arrives:
   - `see <issue-url>` naming a `BLOCKED:` comment: `comment` the answer, then `prompt` the worker `see <issue-url>`; when it asks for work that needs its own pull request, the answer is the url of the issue you `file` for it, which then goes through 3;
   - `see <issue-url>` naming `BLOCKED: stuck on <criterion>`, or two workers escalating after one round of consensus: decide; a changed criterion is edited into the issue and `comment`ed as `CRITERIA CHANGED: <old> → <new>`; then `prompt` each worker `see <issue-url>`;
   - `see <pr-url>`: `read` it; once it shows merged and no issue of its goal is open, go to 5 for that goal;
   - `blocked <name> <url>`: the worker is at a permission prompt, which is the owner's to clear, so tell the owner;
   - `gone <name> <url>` while its issue is open: `start` it again in its worktree, resuming;
   - `stuck <name> <url>`: `read` the issue and its pull request, answer what waits on you, else `prompt` the worker `see <issue-url>`;
   - `lead-heartbeat: team idle ...`: it reconciles lost notices: `read` each open issue of each goal and its pull request, and act on each as if its notice had arrived;
   - `idle` or `working <name> <url>`: nothing;
   - the owner changes direction: `comment` the change on each issue affected, as `CRITERIA CHANGED:` when a criterion changes, and `prompt` its worker `see <issue-url>`; built work the owner rejects is replanned from the goal's definition of done into new issues, its pull request closed unmerged and named in them as content to read, never form to follow;
   - the owner stops one issue: `comment` `STOPPED: <reason>` on it, `gh pr ready --undo <pr-url>`, `close` its worker and remove its `WORKER:` line;
   - a worker's idle line: an issue waiting for a worker: `checkout` it and `prompt` that worker `/mumu-team:kickoff work <issue-url> leader <your address>`, and update its `WORKER:` line; none waiting: `close` it and remove its line;
   - the owner asks where it stands: report each issue and its worker in `live`.
5. `resolve` the parent with a summary, remove its goal from your mission, then `close` each of its workers and `clean`. When no goal is left, delete your mission, which stops the `worker-watch` and `lead-heartbeat` monitors within a poll, so `/exit` meets no background-work dialog.
