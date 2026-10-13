"""Walk-forward score of the time estimate on past tasks: the first FIT of a repository's tasks calibrate the range
levels, the rest only score, each estimated from the tasks closed before it."""
import statistics

import task_estimate

FIT = 0.6
RUN = 5
# (low, high) quantile levels, narrowest first; calibration picks the first whose fit-part coverage reaches TARGET
LEVELS = [(0.1, 0.9), (0.05, 0.95), (0.02, 0.98), (0.0, 1.0)]
TARGET = 0.65  # the lower edge of the coverage the estimate must reach


def _estimate(prior, labels, levels):
    hours, _ = task_estimate.group(prior, labels)
    return task_estimate.quantile(hours, levels[0]), task_estimate.quantile(hours, levels[1]), statistics.median(hours)


def _score(rows, start, levels):
    """Per task from START on: (actual, low, high, median guess, baseline low, baseline high, baseline median)."""
    out = []
    for j in range(start, len(rows)):
        prior = rows[:j]
        low, high, mid = _estimate(prior, rows[j]["labels"], levels)
        every = [r["hours"] for r in prior]
        out.append((rows[j]["hours"], low, high, mid, task_estimate.quantile(every, 0.1), task_estimate.quantile(every, 0.9),
                    statistics.median(every)))
    return out


def _runs(rows, start, stop, levels, seed):
    """Coverage of the bootstrap total over each run of RUN tasks that starts in START..STOP-RUN, and the run count."""
    covered = runs = 0
    for j in range(start, stop - RUN + 1):
        groups = [task_estimate.group(rows[:j], rows[i]["labels"])[0] for i in range(j, j + RUN)]
        low, high = task_estimate.total_range(groups, seed, levels)
        covered += low <= sum(r["hours"] for r in rows[j:j + RUN]) <= high
        runs += 1
    return covered, runs


def _stats(scored, base):
    cut = 4 if base else 1
    cover = sum(s[cut] <= s[0] <= s[cut + 1] for s in scored) / len(scored)
    return {"coverage": cover, "width": statistics.median(s[cut + 1] - s[cut] for s in scored),
            "error": statistics.median(abs(s[0] - s[cut + 2]) for s in scored)}


def backtest(rows, seed=0):
    """The fitted levels and fit coverage, the held-out stats of the estimator and the baseline, and the coverage of
    the bootstrap total over each run of RUN held-out tasks. None when too few tasks to fit and score."""
    rows = sorted(rows, key=lambda r: r["end"])
    k = int(len(rows) * FIT)
    if k < task_estimate.MIN_GROUP or len(rows) - k < RUN:
        return None
    levels, fit_cover = LEVELS[-1], None
    for lv in LEVELS:
        fit = _score(rows[:k], k // 2, lv)
        fit_cover = sum(s[1] <= s[0] <= s[2] for s in fit) / len(fit)
        if fit_cover >= TARGET:
            levels = lv
            break
    held = _score(rows, k, levels)
    total_levels, total_fit = LEVELS[-1], None
    for lv in LEVELS:
        covered, runs = _runs(rows, k // 2, k, lv, seed)
        total_fit = covered / runs if runs else None
        if runs and total_fit >= TARGET:
            total_levels = lv
            break
    covered, runs = _runs(rows, k, len(rows), total_levels, seed)
    return {"tasks": len(rows), "scored": len(held), "levels": levels, "fit_coverage": fit_cover,
            "estimator": _stats(held, False), "baseline": _stats(held, True), "total_levels": total_levels, "total_fit_coverage": total_fit, "covered": covered, "runs": runs}


def as_of(rows, cutoff, numbers):
    """For each task in NUMBERS: (number, low, high, actual hours), estimated from the tasks closed before CUTOFF."""
    prior = [r for r in rows if r["end"] < cutoff]
    out = []
    for r in rows:
        if r["number"] in numbers:
            hours, _ = task_estimate.group(prior, r["labels"])
            out.append((r["number"], task_estimate.quantile(hours, 0.1), task_estimate.quantile(hours, 0.9), r["hours"]))
    return out
