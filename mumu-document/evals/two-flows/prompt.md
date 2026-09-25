---
max_turns: 16
timeout_seconds: 420
allowed_tools: [Skill, Read, Write]
runs: 3
---

Our tool `tiny-queue`:

- `cli.py`: the `tq` command, `tq push <job>` and `tq work`
- `queue/store.py`: keeps jobs in the SQLite file `jobs.db`
- `queue/worker.py`: takes the oldest job, runs it, marks it done or failed
- `queue/retry.py`: puts a failed job back, at most 3 times
- `web/app.py`: a Flask page listing the jobs
- `tests/`

Show what happens in two use cases - a user pushes a job with `tq push`, and a worker retries a failed job - as a page saved to `flows.html` in the current directory.
