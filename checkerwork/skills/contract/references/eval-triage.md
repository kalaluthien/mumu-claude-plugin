# Eval: triage

An eval run failed or flips: name why before any edit.

1. Read each failed run's `error` field in the `--json` output (`cases[].arms.<arm>[].error`) and each grader's `explanation` and `evidence`: a crash, a turn limit or an expired login is the harness, not the change.
2. Read the failed transcripts ([eval/runner-playbook.md](eval/runner-playbook.md) § Transcripts); keep them with `--keep-temp`, since the runner deletes them.
3. Put each failure in one bucket, then do what its row says: [eval/buckets-playbook.md](eval/buckets-playbook.md).
4. After the fix, rerun the case at the runs that showed the failure, on the committed copy beside the default branch's, and report both.
