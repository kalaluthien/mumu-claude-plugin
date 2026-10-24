# Estimation

Every number comes from a script's output, never from your head.

1. `scripts/estimate-task-time.py <issue url>...` prints per task a range and its sample count, and a total range, from the closed tasks' hours `scripts/list-task-durations.py <owner/repo>` lists. Add what its history lacks, as its `--help` says: `--expect-restarts <n>` for a power cut or machine gate announced now (restart hours from `scripts/list-session-gaps.py`), `--wait <name>=<hours>` per wait on a shared resource. Hand the owner the total range with each wait named, never a single number.
2. Rerun it at each new fact, saying which row moved the total.
3. After changing the method, or when estimates keep missing: `scripts/backtest-estimate.py <owner/repo>...` scores held-out coverage; `--as-of <time> --tasks <n>,...` replays named tasks.
