#!/usr/bin/env python3
"""Replay `estimate-task-time.py` over each repository's closed tasks in time order.

usage: backtest-estimate.py [--from-json <file>] [--as-of <time> --tasks <n>,<n>...] <owner/repo>...

The first 60% calibrate the range
levels, the last 40% only score: held-out coverage of the per-task range, its median width and median absolute error, for
the estimator and for the baseline (the p10-p90 of all earlier tasks), then how often the bootstrap total covers the
actual sum over 5 consecutive tasks. `--as-of <time> --tasks ...` prints those tasks' ranges from the history before
<time> beside their actual hours. `--from-json` is {"<owner/repo>": [issues]} in place of GitHub."""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import task_backtest  # noqa: E402
import task_history  # noqa: E402
import usage_parser  # noqa: E402


def main(args):
    parser = usage_parser.parser(__doc__, description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-json", type=lambda path: json.load(open(path)))
    parser.add_argument("--as-of")
    parser.add_argument("--tasks", type=lambda value: {int(issue_number) for issue_number in value.split(",")}, default=set())
    parser.add_argument("repos", nargs="*")
    options = parser.parse_args(args)
    fixture, cutoff, numbers = options.from_json, options.as_of, options.tasks
    repos = options.repos or list(fixture or [])
    if not repos:
        print(__doc__, file=sys.stderr)
        return 2
    pooled = [0, 0]
    for repo in repos:
        rows = task_history.rows(fixture[repo] if fixture else task_history.fetch(repo))
        if cutoff:
            size, scored = task_backtest.as_of(rows, cutoff, numbers)
            print(f"{repo} as of {cutoff}: history of {size} tasks closed before it, the {len(numbers)} scored tasks left out\n"
                  "task\tlow h\thigh h\tactual h\tinside")
            hit = 0
            for number, low, high, actual in scored:
                inside = low <= actual <= high
                hit += inside
                print(f"#{number}\t{low:.1f}\t{high:.1f}\t{actual:.1f}\t{'yes' if inside else 'no: add the waits it lacked with --wait <name>=<hours>'}")
            print(f"inside: {hit} of {len(numbers)} (a regression sample, not a pass line)")
            continue
        result = task_backtest.backtest(rows)
        if result is None:
            print(f"{repo}\ttoo few closed tasks ({len(rows)}) to fit and score")
            continue
        estimator, baseline = result["estimator"], result["baseline"]
        print(f"{repo}\t{result['tasks']} tasks, {result['scored']} scored; fitted levels p{result['levels'][0]*100:.0f}-p{result['levels'][1]*100:.0f} "
              f"(fit coverage {result['fit_coverage']:.2f}); total levels p{result['total_levels'][0]*100:.0f}-p{result['total_levels'][1]*100:.0f} "
              f"(fit coverage {result['total_fit_coverage'] if result['total_fit_coverage'] is None else format(result['total_fit_coverage'], '.2f')})")
        print("\tcoverage\tmedian width h\tmedian abs error h")
        print(f"estimator\t{estimator['coverage']:.2f}\t{estimator['width']:.1f}\t{estimator['error']:.1f}")
        print(f"baseline\t{baseline['coverage']:.2f}\t{baseline['width']:.1f}\t{baseline['error']:.1f}")
        print(f"width estimator/baseline\t{estimator['width'] / baseline['width']:.2f}")
        print(f"total of 5 tasks covered\t{result['covered'] / result['runs']:.2f} over {result['runs']} runs "
              )
        pooled[0] += result["covered"]
        pooled[1] += result["runs"]
    if pooled[1]:
        print(f"pooled total coverage\t{pooled[0] / pooled[1]:.2f} over {pooled[1]} runs")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
