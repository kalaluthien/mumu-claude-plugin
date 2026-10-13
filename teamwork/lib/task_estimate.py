"""Time range of open tasks from the hours of past ones: calculations only, so no session adds durations in its head."""
import random
import statistics

MIN_GROUP = 5
DRAWS = 1000


def quantile(values, p):
    xs = sorted(values)
    k = (len(xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def group_key(labels):
    """The `scope:` label, else the first label in sorted order."""
    scopes = sorted(x for x in labels if x.startswith("scope:"))
    return scopes[0] if scopes else (sorted(labels)[0] if labels else "")


def group(history, labels):
    """(hours of past tasks with the same first label, True when too few and all past tasks were used)."""
    key = group_key(labels)
    same = [r["hours"] for r in history if group_key(r["labels"]) == key]
    return (same, False) if len(same) >= MIN_GROUP else ([r["hours"] for r in history], True)


def total_range(groups, seed=0):
    """p10-p90 of the sums of one random past duration per task: a bootstrap, never a sum of the bounds."""
    rng = random.Random(seed)
    sums = [sum(rng.choice(g) for g in groups) for _ in range(DRAWS)]
    return quantile(sums, 0.1), quantile(sums, 0.9)


def restart_hours(summaries):
    """Mean hours one restart cost over every restart recorded; None when none restarted."""
    hours = [h for s in summaries for h in s["restart_hours"]]
    return statistics.fmean(hours) if hours else None
