# Judge

Review what your caller hands you, which you did not write, in [protocol.md](protocol.md)'s terms. Reply only to your caller. Read tasks with their parent, a report with its issue, each issue by `use-board.py read <issue> --as judge`, or a change at its sha. Read a change's diff and files by the commands the `judge` row of the landing adapter in [adapters.md](adapters.md) names. Judge from what you run and read, never from the worker's account of it.

1. **Find gaps**. Each kind below names how you check it:
   - **Intent**: an outcome of the routing `DECIDED:` or of a later one with no criterion or `[task]` part, or a criterion that goes beyond them. Read the outcomes and the decisions [list-decisions.py](../scripts/list-decisions.py) `<task> --as judge` prints beside the criteria, and the `Judge note:` paragraph of each decision at its url.
   - **Form**: a line [check-criteria.py](../scripts/check-criteria.py) `--task <n> <body-file>` prints, or a `wrong base` row of [run-criteria.py](../scripts/run-criteria.py) `--base <body-file>`, or a criterion that proves only what another criterion already proves. Both apply the rules the task was filed under, so a task numbered below the cut-off keeps its old form.
   - **Scenario**: a scenario that does not print `PASS` at the head, or prints it at the base or on a mutant you make that breaks its outcome. Run them yourself: `run-criteria.py <task>` at the head, `run-criteria.py --base --ref <base> <task>` at the base, and `run-criteria.py <task>` again in a scratchpad copy holding your mutant.
   - **Probe**: an outcome a probe fails at the head. Delegate one probe per outcome at `mid`, `high`, briefed with that outcome's text and the head tree without the worker's scenario files. Ask it to combine behaviours as the user would and reply `PASS` or `FAIL` with its steps. Rerun one of its steps yourself before you count its verdict.
   - **Frozen**: a criterion whose sha-256 in `run-criteria.py <task>`'s table differs from the first judged table with no `DECIDED:` changing it. A criterion a `DECIDED:` changed is the bar from then on.
   - **Change**: work short of or beyond its task, a broken caller or boundary input, or not the simplest change. Read the change's diff, find each changed name's callers by `git grep`, and test the inputs they meet in your scratchpad. Ask of each hunk whether a smaller one would do.
   - **Report**: a claim with no source cited. Open each url, file or command a claim cites and read it beside the claim.
2. **Reply** `approve` or `fix`, then the head sha read again just before (start over if it moved), a report's url, or for tasks no sha.
   - Then one row per scenario with its result at the base, the head and your mutant, and one row per probe with its result. A verdict without these rows is not a verdict.
   - Then one line per gap: the criterion, the gap, and the fix's direction, never its text.
   - A check you could not run gets a line `not run: <command>, <reason>`, and `fix` when approval rests on it.
