---
max_turns: 16
timeout_seconds: 420
allowed_tools: [Skill, Read, Write]
---

In our tool `tiny-queue`, `tq push <job>` (in `cli.py`) stores a job in the SQLite file `jobs.db` through `queue/store.py`; `queue/worker.py` takes the oldest job, runs it and marks it done or failed; `queue/retry.py` puts a failed job back, at most 3 times.

Show what happens in two use cases - a user pushes a job with `tq push`, and a worker retries a failed job - as a page saved to `flows.html` in the current directory.
