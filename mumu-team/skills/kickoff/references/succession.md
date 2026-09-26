# Succession

Continue a lead's work from GitHub, in a session resumed or in a fresh one of the same name, never a restart.

Resume, and a successor once named:

1. Find the root goals and root tasks you hold with `gh issue list --state open --search "no:parent-issue label:kind:goal,kind:task" --json number,title,url`, with `--label scope:<folder>` added for a `<folder>-lead`, run in your checkout.
2. `read` each, the goals and tasks under it, and each task's pull request; `prompt` each worker in `live` whose worktree lies in your checkout `see <its task-url>`.
3. Continue at Lead 4 of lead-goal.md, acting on each open task as if its notice had arrived.

The original, asked to hand over: `start-lead` your successor with `--succeed <your pane>` at your checkout root, passing after `--` the flags `ps -o args= -p $CLAUDE_PID` shows but the program, `--continue`, `--resume`, `--name` and `--agent`; then stop.

The successor, prompted `succeed <pane>`: `worker-close.py <name>`, `<name>` the original's name, which exits the original; `name` yourself that name, keeping the `scope:<folder>` of a `<folder>-lead`; then resume as above.
