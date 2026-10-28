"""Time range of open tasks from the hours of past ones: calculations only, so no session adds durations in its head."""
import os
import random
import statistics

import team_settings

MIN_GROUP = 5
DRAWS = 1000
MIN_COST = 0.05


def quantile(values, level):
    ordered = sorted(values)
    position = (len(ordered) - 1) * level
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def bounds(values, levels):
    """The (low, high) quantiles of VALUES at LEVELS."""
    return quantile(values, levels[0]), quantile(values, levels[1])


def group_key(labels):
    """The scope label, the one that starts with the setting `scope_prefix`, else the first label in sorted order."""
    prefix = team_settings.load(os.getcwd())["scope_prefix"]
    scopes = sorted(label for label in labels if label.startswith(prefix))
    return scopes[0] if scopes else (sorted(labels)[0] if labels else "")


def group(history, labels):
    """(hours of past tasks with the same first label, True when too few and all past tasks were used)."""
    key = group_key(labels)
    same = [row["hours"] for row in history if group_key(row["labels"]) == key]
    return (same, False) if len(same) >= MIN_GROUP else ([row["hours"] for row in history], True)


def total_range(groups, seed=0, levels=(0.1, 0.9)):
    """The LEVELS quantiles (p10-p90 by default) of the sums of one random past duration per task: a bootstrap, never a sum of the bounds."""
    generator = random.Random(seed)
    sums = [sum(generator.choice(hours) for hours in groups) for _ in range(DRAWS)]
    return bounds(sums, levels)


def restart_hours(summaries):
    """Median hours of the restarts that cost time (over MIN_COST hours; the rest are immediate handoffs, which would make
    the median 0); None when no such restart is recorded."""
    hours = [hour for summary in summaries for hour in summary["restart_hours"] if hour > MIN_COST]
    return statistics.median(hours) if hours else None
