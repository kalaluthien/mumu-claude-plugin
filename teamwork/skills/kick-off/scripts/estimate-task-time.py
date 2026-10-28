#!/usr/bin/env python3
"""Print a time range per open task, its sample count and a total range at levels fitted on the history, from the hours past tasks of the same first label
took (all past tasks when fewer than 5 share it).

usage: estimate-task-time.py [--from-json <file>] [--gaps-json <file>] [--expect-restarts <n>] [--wait <name>=<hours>]...
                             [--seed <n>] [<issue url>...]

The total is a bootstrap over those hours, repeatable by `--seed`.
Past hours already hold the usual restarts and waits, so the script adds only what the history lacks: `--expect-restarts
<n>` adds n restarts at the median hours of a restart that cost time (from `--gaps-json`, the output of `list-session-gaps.py --json`,
else the transcripts of every named session), and each `--wait` adds its hours once, as a row of its own.
`--from-json` is a fixture {"history": [...], "tasks": [{"number": 1, "labels": [...]}]} in place of GitHub."""
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402
import claude_config  # noqa: E402
import session_gaps  # noqa: E402
import task_backtest  # noqa: E402
import task_estimate  # noqa: E402
import task_history  # noqa: E402
import usage_parser  # noqa: E402


def parse_options(argv):
    parser = usage_parser.parser(__doc__, description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-json")
    parser.add_argument("--gaps-json")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--expect-restarts", type=float, default=0.0)
    parser.add_argument("--wait", action="append", default=[], type=lambda value: (value.partition("=")[0], float(value.partition("=")[2])))
    parser.add_argument("urls", nargs="*")
    return parser.parse_args(argv)


def load(options, urls):
    if options.from_json:
        fixture = json.load(open(options.from_json))
        return task_history.rows(fixture["history"]), fixture["tasks"]
    if not urls:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    tasks, history = [], {}
    for url in urls:
        match = re.match(r"https://github.com/([^/]+/[^/]+)/issues/(\d+)", url)
        if not match:
            print(__doc__, file=sys.stderr)
            sys.exit(2)
        repo, number = match.groups()
        if repo not in history:
            history[repo] = task_history.rows(task_history.fetch(repo))
        issue = board.fresh(number, repo, comments=False)
        if issue is None:
            sys.exit(f"estimate-task-time.py: the REST read of {url} failed")
        tasks.append({"number": issue["number"], "labels": issue["labels"], "repo": repo})
    return [row for rows in history.values() for row in rows], tasks


def main(args):
    options = parse_options(args)
    history, tasks = load(options, options.urls)
    groups = []
    fitted = task_backtest.fit(sorted(history, key=lambda row: row["end"]), options.seed)
    levels, total_levels = (fitted[0], fitted[2]) if fitted else ((0.1, 0.9), (0.1, 0.9))
    short = [] if not fitted else [
        *([f"per task below the {task_backtest.TARGET:.0%} target at every level, so the widest"] if fitted[1] < task_backtest.TARGET else []),
        *([f"total: no run of {task_backtest.RUN} tasks to fit, so the widest"] if fitted[3] is None else [])]
    print(f"levels p{levels[0]*100:.0f}-p{levels[1]*100:.0f} per task, p{total_levels[0]*100:.0f}-p{total_levels[1]*100:.0f} total"
          f" ({'fitted on the first 60% of the history, as backtest-estimate.py scores them' if fitted else 'default: too few past tasks to fit'}"
          f"{''.join('; ' + shortfall for shortfall in short)})")
    print("task\tlow h\thigh h\tsamples\tnote")
    for task in tasks:
        hours, fallback = task_estimate.group(history, task["labels"])
        if not hours:
            print(f"#{task['number']}\t-\t-\t0\tno range: no past task exists")
            continue
        groups.append(hours)
        low, high = task_estimate.bounds(hours, levels)
        print(f"#{task['number']}\t{low:.1f}\t{high:.1f}\t{len(hours)}\t{'all past tasks used' if fallback else 'same first label'}")
    low, high = task_estimate.total_range(groups, options.seed, total_levels) if groups else (None, None)
    extra = 0.0
    if options.expect_restarts:
        gaps = json.load(open(options.gaps_json)) if options.gaps_json else session_gaps.summaries(claude_config.folder() / "projects")
        each = task_estimate.restart_hours(gaps)
        if each is None:
            sys.exit("estimate-task-time.py: no restart is recorded, so its hours are unknown; pass --wait instead.")
        extra += options.expect_restarts * each
        print(f"restart\t{options.expect_restarts * each:.1f}h\t({options.expect_restarts:g} restarts x {each:.1f}h median)")
    for name, hours in options.wait:
        extra += hours
        print(f"wait {name}\t{hours:.1f}h")
    if not groups:
        return print(f"total\t-\t-\tno range: no past task exists{', so the rows above are not summed' if extra else ''}")
    print(f"total\t{low + extra:.1f}\t{high + extra:.1f}\t{task_estimate.DRAWS} bootstrap sums over {len(tasks)} tasks"
          f"{', plus the rows above' if extra else ''}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
