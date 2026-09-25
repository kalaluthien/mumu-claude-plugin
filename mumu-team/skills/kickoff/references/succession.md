# Succession

Replace a lead with a fresh session of the same name, never restart it: the successor reads the same name-keyed mission, rebuilt from GitHub when missing.

The original, asked to hand over:

1. `start-lead` your successor at your checkout root, its tab and herdr agent named `<repo>-lead-next` and its Claude `--name <repo>-lead`, with the other flags `ps -o args= -p $CLAUDE_PID` shows but `--continue` and `--resume`, prompted `/mumu-team:kickoff succeed <your pane> <parent-url> ...`, one url per goal you hold; then stop.

The successor, prompted `succeed <pane> <parent-url> ...`:

1. `worker-close.py <repo>-lead`, which exits the original at its pane and leaves your mission, the same file, in place.
2. `name` yourself `<repo>-lead`, then run `ensure-monitors.py` and arm each command it prints, as Lead 1 does.
3. `read` each parent url; a goal missing from your mission gets its `GOAL:` and `MISSION:` pair.
4. `prompt` each worker in your mission `see <its issue-url>`, then continue at Lead 4 of [lead.md](lead.md), as [resume.md](resume.md) does.
