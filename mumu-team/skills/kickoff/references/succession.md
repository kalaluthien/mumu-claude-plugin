# Succession

Replace a lead with a fresh session of the same name, never restart it: the successor finds its goals on GitHub.

The original, asked to hand over:

1. `start-lead` your successor with `--succeed <your pane>` at your checkout root, passing after `--` the flags `ps -o args= -p $CLAUDE_PID` shows but the program, `--continue`, `--resume`, `--name` and `--agent`; then stop.

The successor, prompted `succeed <pane>`:

1. `worker-close.py <name>`, `<name>` the original's name, `<repo>-lead` or `<folder>-lead`, which exits the original at its pane.
2. `name` yourself that `<name>`, keeping the `scope:<folder>` of a `<folder>-lead`.
3. Find the root goals you now hold with `gh issue list --label kind:goal --state open --search "no:parent-issue" --json number,title,url`, with `--label scope:<folder>` added for a `<folder>-lead`, run in your checkout, and `read` each.
4. `prompt` each worker in `live` whose worktree lies in your checkout `see <its task-url>`, then continue at Lead 4 of [lead.md](lead.md), as [resume.md](resume.md) does.
