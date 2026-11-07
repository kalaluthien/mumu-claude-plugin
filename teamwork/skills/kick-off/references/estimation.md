# Estimation

Estimate how long a task or a parent will take, from the hours closed tasks took.

Every number comes from a script's output, never from your head.

1. [estimate-task-time.py](../scripts/estimate-task-time.py) `<board url>...`, the `git+file://…/<n>` url of a task, prints per task a range and its sample count, and a total range, from the closed tasks' hours [list-task-durations.py](../scripts/list-task-durations.py) `<repository>` lists. Add what its history lacks, as its `--help` says: `--expect-restarts <n>` for a power cut or machine gate announced now (restart hours from [list-session-gaps.py](../scripts/list-session-gaps.py)), `--wait <name>=<hours>` per wait on a shared resource. Hand the owner the total range with each wait named, never a single number.
2. Rerun it at each new fact, saying which row moved the total.
3. After changing the method, or when estimates keep missing: [backtest-estimate.py](../scripts/backtest-estimate.py) `<repository>...` scores held-out coverage; `--as-of <time> --tasks <n>,...` replays named tasks.
