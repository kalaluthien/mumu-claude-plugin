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
    return *task_estimate.bounds(hours, levels), statistics.median(hours)


def _score(rows, start, levels):
    """Per task from START on: (actual, low, high, median guess, baseline low, baseline high, baseline median)."""
    out = []
    for index in range(start, len(rows)):
        prior = rows[:index]
        low, high, mid = _estimate(prior, rows[index]["labels"], levels)
        every = [row["hours"] for row in prior]
        out.append((rows[index]["hours"], low, high, mid, *task_estimate.bounds(every, (0.1, 0.9)), statistics.median(every)))
    return out


def _runs(rows, start, stop, levels, seed):
    """Coverage of the bootstrap total over each run of RUN tasks that starts in START..STOP-RUN, and the run count."""
    covered = runs = 0
    for index in range(start, stop - RUN + 1):
        groups = [task_estimate.group(rows[:index], rows[i]["labels"])[0] for i in range(index, index + RUN)]
        low, high = task_estimate.total_range(groups, seed, levels)
        covered += low <= sum(row["hours"] for row in rows[index:index + RUN]) <= high
        runs += 1
    return covered, runs


def _spread(scored, base):
    cut = 4 if base else 1
    cover = sum(score[cut] <= score[0] <= score[cut + 1] for score in scored) / len(scored)
    return {"coverage": cover, "width": statistics.median(score[cut + 1] - score[cut] for score in scored),
            "error": statistics.median(abs(score[0] - score[cut + 2]) for score in scored)}


def _narrowest(cover_at):
    """The first of LEVELS whose coverage reaches TARGET, else the widest, with the coverage last measured."""
    cover = None
    for candidate in LEVELS:
        cover = cover_at(candidate)
        if cover is not None and cover >= TARGET:
            return candidate, cover
    return LEVELS[-1], cover


def _share(hit, runs):
    return hit / runs if runs else None


def _covered(scored):
    return _share(sum(score[1] <= score[0] <= score[2] for score in scored), len(scored))


def fit(rows, seed=0):
    """Calibrate on the first FIT of ROWS (oldest first): the narrowest per-task levels and total levels whose coverage
    over the later half of that part reaches TARGET, each with that coverage; None when too few tasks."""
    split = int(len(rows) * FIT)
    if split < task_estimate.MIN_GROUP:
        return None
    levels, cover = _narrowest(lambda candidate: _covered(_score(rows[:split], split // 2, candidate)))
    total_levels, total_cover = _narrowest(lambda candidate: _share(*_runs(rows, split // 2, split, candidate, seed)))
    return levels, cover, total_levels, total_cover


def backtest(rows, seed=0):
    """The fitted levels and fit coverages, the held-out stats of the estimator and the baseline, and the coverage of
    the bootstrap total over each run of RUN held-out tasks. None when too few tasks to fit and score."""
    rows = sorted(rows, key=lambda row: row["end"])
    split = int(len(rows) * FIT)
    fitted = fit(rows, seed)
    if fitted is None or len(rows) - split < RUN:
        return None
    levels, cover, total_levels, total_cover = fitted
    held = _score(rows, split, levels)
    hit, runs = _runs(rows, split, len(rows), total_levels, seed)
    return {"tasks": len(rows), "scored": len(held), "levels": levels, "fit_coverage": cover,
            "estimator": _spread(held, False), "baseline": _spread(held, True), "total_levels": total_levels,
            "total_fit_coverage": total_cover, "covered": hit, "runs": runs}


def as_of(rows, cutoff, numbers):
    """(history size, [(number, low, high, actual hours)]): each task in NUMBERS estimated from the tasks closed before
    CUTOFF with the NUMBERS themselves left out, at the levels fitted on that history as the estimator fits them."""
    prior = sorted((row for row in rows if row["end"] < cutoff and row["number"] not in numbers), key=lambda row: row["end"])
    fitted = fit(prior)
    levels = fitted[0] if fitted else (0.1, 0.9)
    out = []
    for row in rows:
        if row["number"] in numbers:
            hours, _ = task_estimate.group(prior, row["labels"])
            out.append((row["number"], *task_estimate.bounds(hours, levels), row["hours"]))
    return len(prior), out
