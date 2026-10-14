#!/usr/bin/env python3
"""usage: estimate-task-time.py [--from-json <file>] [--gaps-json <file>] [--expect-restarts <n>] [--wait <name>=<hours>]...
                               [--seed <n>] [<issue url>...]

Print a time range per open task, its sample count and a total range at levels fitted on the history, from the hours past tasks of the same first label
took (all past tasks when fewer than 5 share it). The total is a bootstrap over those hours, repeatable by `--seed`.
Past hours already hold the usual restarts and waits, so the script adds only what the history lacks: `--expect-restarts
<n>` adds n restarts at the median hours of a restart that cost time (from `--gaps-json`, the output of `list-session-gaps.py --json`,
else the transcripts of every named session), and each `--wait` adds its hours once, as a row of its own.
`--from-json` is a fixture {"history": [...], "tasks": [{"number": 1, "labels": [...]}]} in place of GitHub."""
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import session_gaps  # noqa: E402
import task_backtest  # noqa: E402
import task_estimate  # noqa: E402
import task_history  # noqa: E402


def options(argv):
    opt, waits, urls = {"seed": 0, "expect-restarts": 0.0}, [], []
    while argv:
        a = argv.pop(0)
        if a in ("--from-json", "--gaps-json", "--seed", "--expect-restarts", "--wait") and argv:
            v = argv.pop(0)
            if a == "--wait":
                name, _, hours = v.partition("=")
                waits.append((name, float(hours)))
            else:
                opt[a[2:]] = float(v) if a in ("--seed", "--expect-restarts") else v
        elif a.startswith("--"):
            sys.exit(__doc__)
        else:
            urls.append(a)
    return opt, waits, urls


def load(opt, urls):
    if "from-json" in opt:
        fixture = json.load(open(opt["from-json"]))
        return task_history.rows(fixture["history"]), fixture["tasks"]
    if not urls:
        sys.exit(__doc__)
    tasks, history = [], {}
    for url in urls:
        match = re.match(r"https://github.com/([^/]+/[^/]+)/issues/(\d+)", url)
        if not match:
            sys.exit(__doc__)
        repo, number = match.groups()
        if repo not in history:
            history[repo] = task_history.rows(task_history.fetch(repo))
        issue = task_history._gh("issue", "view", url, "--json", "number,labels")
        tasks.append({"number": issue["number"], "labels": [x["name"] for x in issue["labels"]], "repo": repo})
    return [r for rows in history.values() for r in rows], tasks


def main(argv):
    opt, waits, urls = options(argv)
    history, tasks = load(opt, urls)
    groups = []
    fitted = task_backtest.fit(sorted(history, key=lambda r: r["end"]), int(opt["seed"]))
    levels, total_levels = (fitted[0], fitted[2]) if fitted else ((0.1, 0.9), (0.1, 0.9))
    short = [] if not fitted else [
        *([f"per task below the {task_backtest.TARGET:.0%} target at every level, so the widest"] if fitted[1] < task_backtest.TARGET else []),
        *([f"total: no run of {task_backtest.RUN} tasks to fit, so the widest"] if fitted[3] is None else [])]
    print(f"levels p{levels[0]*100:.0f}-p{levels[1]*100:.0f} per task, p{total_levels[0]*100:.0f}-p{total_levels[1]*100:.0f} total"
          f" ({'fitted on the first 60% of the history, as backtest-estimate.py scores them' if fitted else 'default: too few past tasks to fit'}"
          f"{''.join('; ' + s for s in short)})")
    print("task\tlow h\thigh h\tsamples\tnote")
    for t in tasks:
        hours, fallback = task_estimate.group(history, t["labels"])
        if not hours:
            print(f"#{t['number']}\t-\t-\t0\tno range: no past task exists")
            continue
        groups.append(hours)
        low, high = task_estimate.quantile(hours, levels[0]), task_estimate.quantile(hours, levels[1])
        print(f"#{t['number']}\t{low:.1f}\t{high:.1f}\t{len(hours)}\t{'all past tasks used' if fallback else 'same first label'}")
    low, high = task_estimate.total_range(groups, int(opt["seed"]), total_levels) if groups else (None, None)
    extra = 0.0
    if opt["expect-restarts"]:
        gaps = json.load(open(opt["gaps-json"])) if "gaps-json" in opt else session_gaps.summaries(
            pathlib.Path(os.path.expanduser("~/.claude/projects")))
        each = task_estimate.restart_hours(gaps)
        if each is None:
            sys.exit("estimate-task-time.py: no restart is recorded, so its hours are unknown; pass --wait instead.")
        extra += opt["expect-restarts"] * each
        print(f"restart\t{opt['expect-restarts'] * each:.1f}h\t({opt['expect-restarts']:g} restarts x {each:.1f}h median)")
    for name, hours in waits:
        extra += hours
        print(f"wait {name}\t{hours:.1f}h")
    if not groups:
        return print(f"total\t-\t-\tno range: no past task exists{', so the rows above are not summed' if extra else ''}")
    print(f"total\t{low + extra:.1f}\t{high + extra:.1f}\t{task_estimate.DRAWS} bootstrap sums over {len(tasks)} tasks"
          f"{', plus the rows above' if extra else ''}")


if __name__ == "__main__":
    main(sys.argv[1:])
