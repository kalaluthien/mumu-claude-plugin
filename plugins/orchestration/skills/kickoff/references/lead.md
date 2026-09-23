# Lead

Lead a goal to reviewed, merged pull requests.

1. `name` yourself `<topic>-lead`, the topic being the goal's, then ask the owner every question at once with `AskUserQuestion`.
2. `file` the parent, the owner's expectations among its decisions, and one issue per pull request, each labelled with its effort, then write your mission; launch the `reviewer` on the parent's url and fix its findings until it posts `Approved`.
3. For each issue: `checkout`, `start` it under its name at its effort, add its `Worker:` line to your mission, and `prompt` it `/orchestration:kickoff work <issue-url> leader <your address>`.
4. Poll nothing; act on what arrives, once per state GitHub shows (a `BLOCKED:` already answered, or a merge already handled, needs nothing):
   - `see <issue-url>` naming a `BLOCKED:` comment: `comment` the answer, then `prompt` the worker `see <issue-url>`; when it asks for work that needs its own pull request, the answer is the url of the issue you `file` for it, which then goes through 3;
   - `see <pr-url>`: `read` it; once it shows merged and no issue is open, go to 5;
   - `blocked <name> <url>`: the worker is at a permission prompt, which is the owner's to clear, so tell the owner;
   - `gone <name> <url>` while its issue is open: `start` it again in its worktree, resuming;
   - `stuck <name> <url>`: `read` the issue and its pull request, answer what waits on you, else `prompt` the worker `see <issue-url>`;
   - `lead-heartbeat: team idle ...`: it reconciles lost notices: `read` each open issue and its pull request, and act on each as if its notice had arrived;
   - `idle` or `working <name> <url>`: nothing;
   - the owner changes direction: `comment` the change on each issue affected and `prompt` its worker `see <issue-url>`;
   - a worker's idle line: an issue waiting for a worker: `checkout` it and `prompt` that worker `/orchestration:kickoff work <issue-url> leader <your address>`, and update its `Worker:` line; none waiting: `close` it and remove its line;
   - the owner asks where it stands: report each issue and its worker in `live`.
5. `resolve` the parent with a summary, delete your mission, then `close` each worker and `clean`.
