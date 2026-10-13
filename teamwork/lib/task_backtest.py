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


def fit(rows, seed=0):
    """Calibrate on the first FIT of ROWS (oldest first): the narrowest per-task levels and total levels whose coverage
    over the later half of that part reaches TARGET, each with that coverage; None when too few tasks."""
    k = int(len(rows) * FIT)
    if k < task_estimate.MIN_GROUP:
        return None
    levels, cover = LEVELS[-1], None
    for lv in LEVELS:
        part = _score(rows[:k], k // 2, lv)
        cover = sum(s[1] <= s[0] <= s[2] for s in part) / len(part)
        if cover >= TARGET:
            levels = lv
            break
    total_levels, total_cover = LEVELS[-1], None
    for lv in LEVELS:
        hit, runs = _runs(rows, k // 2, k, lv, seed)
        total_cover = hit / runs if runs else None
        if runs and total_cover >= TARGET:
            total_levels = lv
            break
    return levels, cover, total_levels, total_cover


def backtest(rows, seed=0):
    """The fitted levels and fit coverages, the held-out stats of the estimator and the baseline, and the coverage of
    the bootstrap total over each run of RUN held-out tasks. None when too few tasks to fit and score."""
    rows = sorted(rows, key=lambda r: r["end"])
    k = int(len(rows) * FIT)
    fitted = fit(rows, seed)
    if fitted is None or len(rows) - k < RUN:
        return None
    levels, cover, total_levels, total_cover = fitted
    held = _score(rows, k, levels)
    hit, runs = _runs(rows, k, len(rows), total_levels, seed)
    return {"tasks": len(rows), "scored": len(held), "levels": levels, "fit_coverage": cover,
            "estimator": _stats(held, False), "baseline": _stats(held, True), "total_levels": total_levels,
            "total_fit_coverage": total_cover, "covered": hit, "runs": runs}


def as_of(rows, cutoff, numbers):
    """(history size, [(number, low, high, actual hours)]): each task in NUMBERS estimated from the tasks closed before
    CUTOFF with the NUMBERS themselves left out, at the levels fitted on that history as the estimator fits them."""
    prior = sorted((r for r in rows if r["end"] < cutoff and r["number"] not in numbers), key=lambda r: r["end"])
    assert not numbers & {r["number"] for r in prior}, "a scored task is in its own history"
    fitted = fit(prior)
    levels = fitted[0] if fitted else (0.1, 0.9)
    out = []
    for r in rows:
        if r["number"] in numbers:
            hours, _ = task_estimate.group(prior, r["labels"])
            out.append((r["number"], task_estimate.quantile(hours, levels[0]), task_estimate.quantile(hours, levels[1]), r["hours"]))
    return len(prior), out
