---
max_turns: 20
timeout_seconds: 600
allowed_tools: [Skill, Read, Write]
---

Our tool `tiny-queue`, in three parts:

- Storage: `queue/store.py` keeps jobs in the SQLite file `jobs.db`; a job is pending, running, done or failed; `tq push <job>` (in `cli.py`) adds a pending job.
- Running: `tq work` starts `queue/worker.py`, which takes the oldest pending job, marks it running, runs it, then marks it done or failed; `web/app.py` is a Flask page listing the jobs by state.
- Failure: `queue/retry.py` puts a failed job back as pending, at most 3 times; after that it stays failed, and a worker that dies leaves its job running until `tq work --reset` puts it back.

Explain how tiny-queue is built and how it works, part by part, as a page saved to `guide.html` in the current directory.
