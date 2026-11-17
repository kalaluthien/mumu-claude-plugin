# Estimation

Estimate how long a task or a parent will take, from the hours closed tasks took.

Every number comes from a script's output, never from your head.

1. [estimate-task-time.py](estimation/scripts/estimate-task-time.py) `<board url>...` prints ranges from the closed tasks' hours [list-task-durations.py](estimation/scripts/list-task-durations.py) lists. Add what its history lacks, as its `--help` says: a restart announced now, its hours from [list-session-gaps.py](estimation/scripts/list-session-gaps.py), a wait on a shared resource. Hand the owner the total range with each wait named, never a single number.
2. Rerun it at each new fact, saying which row moved the total.
3. After changing the method, or when estimates keep missing: run [backtest-estimate.py](estimation/scripts/backtest-estimate.py).
