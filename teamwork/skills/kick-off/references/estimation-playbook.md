# Estimation

Open when you give or revise a time estimate for tasks; run the scripts, never add durations in your head.

1. **History**: `scripts/list-task-durations.py <owner/repo>` lists the hours of closed tasks, each from its pull request's first commit, else from its creation.
2. **Estimate**: `scripts/estimate-task-time.py <issue url>...` prints per task a range and its sample count, and a total range. Hand the owner the total with its range, never a single number.
3. **Name what the history lacks**: it holds the usual restarts, not a power cut or a machine gate announced for now. Add `--expect-restarts <n>` (restart hours come from `scripts/list-session-gaps.py`) and `--wait <name>=<hours>` for each wait on a shared resource.
4. **Revise** at each new fact the same way, with the same command; say which row moved the total.
5. **Check the method** after a change to it, or when estimates keep missing: `scripts/backtest-estimate.py <owner/repo>...` scores held-out coverage; `--as-of <time> --tasks <n>,...` replays named tasks.

Done when the owner has a range with its sample count and each wait named, and every number came from a script's output.
