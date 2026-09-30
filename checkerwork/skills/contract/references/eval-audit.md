# Eval: audit

A suite exists and the question is whether to trust it, or a run failed or flips. Check, reading the files and the failed transcripts:

0. A failed or flipping run first, before any edit: read each failed run's `error` field in the `--json` output (`cases[].arms.<arm>[].error`) and each grader's `explanation` and `evidence`, since a crash, a turn limit or an expired login is the harness, not the change; read the failed transcripts, kept with `--keep-temp` ([eval/runner-playbook.md](eval/runner-playbook.md) § Transcripts); put each failure in one bucket and do what its row says ([eval/buckets-playbook.md](eval/buckets-playbook.md)); after the fix, rerun the case as its bucket's row says, on the committed copy beside the default branch's, and report both.

1. Each grader traces to a failure mode seen in a trace ([eval/analysis-playbook.md](eval/analysis-playbook.md)), answers pass or fail, and is code where code can decide ([eval/graders-playbook.md](eval/graders-playbook.md)).
2. Each judge has TPR and TNR on a held-out split ([eval/judge-playbook.md](eval/judge-playbook.md) § Validate).
3. Each case runs more than once from a clean directory, regression and capability kept apart, and a suite that long passed everything is retired or refreshed ([eval/runner-playbook.md](eval/runner-playbook.md)).
4. A trigger case reports its fire and quiet rates apart ([eval/graders-playbook.md](eval/graders-playbook.md)).

Report what fails, most harmful first, naming the file and the fix.
