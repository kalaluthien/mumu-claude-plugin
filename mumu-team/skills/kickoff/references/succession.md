# Succession

Replace a lead with a fresh session of the same name, never restart it: the successor finds its goals on GitHub.

The original, asked to hand over:

1. `start-lead` your successor at your checkout root, its tab and herdr agent named `<repo>-lead-next` and its Claude `--name <repo>-lead`, with the other flags `ps -o args= -p $CLAUDE_PID` shows but `--continue` and `--resume`, prompted `/mumu-team:kickoff succeed <your pane>`; then stop.

The successor, prompted `succeed <pane>`:

1. `worker-close.py <repo>-lead`, which exits the original at its pane.
2. `name` yourself `<repo>-lead`.
3. Find the root goals you now hold with `gh issue list --label kind:goal --state open --search "no:parent-issue" --json number,title,url`, run in your checkout, and `read` each.
4. `prompt` each worker in `live` whose worktree lies in your checkout `see <its task-url>`, then continue at Lead 4 of [lead.md](lead.md), as [resume.md](resume.md) does.
