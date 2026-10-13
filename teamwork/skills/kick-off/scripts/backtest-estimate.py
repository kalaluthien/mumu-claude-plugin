#!/usr/bin/env python3
"""usage: backtest-estimate.py [--from-json <file>] [--as-of <time> --tasks <n>,<n>...] <owner/repo>...

Replay `estimate-task-time.py` over each repository's closed tasks in time order. The first 60% calibrate the range
levels, the last 40% only score: held-out coverage of the per-task range, its median width and median absolute error, for
the estimator and for the baseline (the p10-p90 of all earlier tasks), then how often the bootstrap total covers the
actual sum over 5 consecutive tasks. `--as-of <time> --tasks ...` prints those tasks' ranges from the history before
<time> beside their actual hours. `--from-json` is {"<owner/repo>": [issues]} in place of GitHub."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import task_backtest  # noqa: E402
import task_history  # noqa: E402


def main(argv):
    fixture, cutoff, numbers, repos = None, None, set(), []
    while argv:
        a = argv.pop(0)
        if a == "--from-json" and argv:
            fixture = json.load(open(argv.pop(0)))
        elif a == "--as-of" and argv:
            cutoff = argv.pop(0)
        elif a == "--tasks" and argv:
            numbers = {int(n) for n in argv.pop(0).split(",")}
        elif a.startswith("--"):
            sys.exit(__doc__)
        else:
            repos.append(a)
    repos = repos or list(fixture or [])
    if not repos:
        sys.exit(__doc__)
    pooled = [0, 0]
    for repo in repos:
        rows = task_history.rows(fixture[repo] if fixture else task_history.fetch(repo))
        if cutoff:
            print(f"{repo} as of {cutoff}\ntask\tlow h\thigh h\tactual h\tinside")
            hit = 0
            for number, low, high, actual in task_backtest.as_of(rows, cutoff, numbers):
                inside = low <= actual <= high
                hit += inside
                print(f"#{number}\t{low:.1f}\t{high:.1f}\t{actual:.1f}\t{'yes' if inside else 'no: add the waits it lacked with --wait <name>=<hours>'}")
            print(f"inside: {hit} of {len(numbers)}")
            continue
        r = task_backtest.backtest(rows)
        if r is None:
            print(f"{repo}\ttoo few closed tasks ({len(rows)}) to fit and score")
            continue
        e, b = r["estimator"], r["baseline"]
        print(f"{repo}\t{r['tasks']} tasks, {r['scored']} scored; fitted levels p{r['levels'][0]*100:.0f}-p{r['levels'][1]*100:.0f} "
              f"(fit coverage {r['fit_coverage']:.2f}); total levels p{r['total_levels'][0]*100:.0f}-p{r['total_levels'][1]*100:.0f} "
              f"(fit coverage {r['total_fit_coverage'] if r['total_fit_coverage'] is None else format(r['total_fit_coverage'], '.2f')})")
        print("\tcoverage\tmedian width h\tmedian abs error h")
        print(f"estimator\t{e['coverage']:.2f}\t{e['width']:.1f}\t{e['error']:.1f}")
        print(f"baseline\t{b['coverage']:.2f}\t{b['width']:.1f}\t{b['error']:.1f}")
        print(f"width estimator/baseline\t{e['width'] / b['width']:.2f}")
        print(f"total of 5 tasks covered\t{r['covered'] / r['runs']:.2f} over {r['runs']} runs "
              )
        pooled[0] += r["covered"]
        pooled[1] += r["runs"]
    if pooled[1]:
        print(f"pooled total coverage\t{pooled[0] / pooled[1]:.2f} over {pooled[1]} runs")


if __name__ == "__main__":
    main(sys.argv[1:])
