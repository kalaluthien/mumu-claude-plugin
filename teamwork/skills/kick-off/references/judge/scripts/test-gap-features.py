#!/usr/bin/env python3
"""Print whether any feature of a `fix` round's gaps shows, in a table of past rounds, that the judge missed a code fault.

usage: test-gap-features.py [<table.tsv>]

Reads <table.tsv> (default: the skill's assets/soft-rounds.tsv), one row per past `fix` round that named no code fault or failed scenario: its
change, round, what later rounds showed (`missed` a fault present at its head, `made` only faults made after it, `none`, `unknown`),
its changed lines or `-`, and its count of gaps per class. Prints the rate of `missed` with its 95% interval over 2000 resamples of the
changes, the price of a fault on main, in judge rounds, above which another round pays, and per feature the rate by value, the Brier
gain over the base rate cross-validated in five folds by change, and the share of 400 label shuffles that reach that gain; a feature
`predicts` when under 0.05 of them, divided by the count of features tried (Bonferroni), do and each value has 10 rounds. Ends with the features that predict, or `no feature predicts`.
Exits 0, or 2 with this text for a call or table it cannot read. Standard library only, Python 3.9."""

import collections
import hashlib
import pathlib
import random
import sys

TABLE = pathlib.Path(__file__).resolve().parents[3] / "assets" / "soft-rounds.tsv"
FOLDS, SHUFFLES, RESAMPLES, CHANCE, SMALLEST = 5, 400, 2000, 0.05, 10


def fold(change):
    return int(hashlib.sha256(change.encode()).hexdigest(), 16) % FOLDS


def brier_gain(rows, labels, feature):
    """The base rate's squared error less the feature's, each fitted on four folds and scored on the fifth, per round."""
    gains = []
    for held in range(FOLDS):
        train = [(row, label) for row, label in zip(rows, labels) if fold(row["change"]) != held]
        if not train:
            continue
        base = sum(label for _, label in train) / len(train)
        seen = collections.defaultdict(list)
        for row, label in train:
            seen[feature(row)].append(label)
        for row, label in zip(rows, labels):
            if fold(row["change"]) == held:
                group = seen.get(feature(row))
                rate = sum(group) / len(group) if group else base
                gains.append((base - label) ** 2 - (rate - label) ** 2)
    return sum(gains) / len(rows)


def interval(rows, labels, chance):
    """The 2.5% and 97.5% points of the missed rate over RESAMPLES draws of the changes with replacement, since one change's rounds share a fate."""
    by_change = collections.defaultdict(list)
    for row, label in zip(rows, labels):
        by_change[row["change"]].append(label)
    rates = []
    for _ in range(RESAMPLES):
        drawn = [label for group in chance.choices(list(by_change.values()), k=len(by_change)) for label in group]
        rates.append(sum(drawn) / len(drawn))
    rates.sort()
    return rates[RESAMPLES // 40], rates[-RESAMPLES // 40]


def read(path):
    lines = pathlib.Path(path).read_text().splitlines()
    names = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        row = dict(zip(names, line.split("\t")))
        rows.append({"change": row["change"], "round": int(row["round"]), "later": row["later"], "lines": None if row["lines"] == "-" else int(row["lines"]),
                     "classes": {name: int(row[name]) for name in names[4:]}})
    return names[4:], rows


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    if len(args) > 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        classes, table = read(args[0] if args else TABLE)
    except (OSError, ValueError, KeyError, IndexError):
        print(__doc__, file=sys.stderr)
        return 2
    rows = [row for row in table if row["later"] != "unknown"]
    labels = [int(row["later"] == "missed") for row in rows]
    if not 0 < sum(labels) < len(rows):
        print(__doc__, file=sys.stderr)
        return 2
    events, rate = sum(labels), sum(labels) / len(rows)
    chance, predicting = random.Random(len(table)), []
    low, high = interval(rows, labels, chance)
    print(f"{len(table)} past `fix` rounds named no code fault or failed scenario; {len(table) - len(rows)} have no known later outcome.")
    print(f"missed: {events} of {len(rows)} rounds in {len({row['change'] for row, label in zip(rows, labels) if label})} of {len({row['change'] for row in rows})} changes, "
          f"rate {rate:.2f}, 95% interval {low:.2f} to {high:.2f} by resampling changes.")
    print(f"Another round pays only when a fault on main costs more than {1 / high:.1f} to {f'{1 / low:.1f}' if low else 'any number of'} judge rounds.")
    features = {"first round": lambda row: row["round"] == 1,
                "gaps (1, 2 to 3, 4 or more)": lambda row: sum(sum(row["classes"].values()) >= least for least in (2, 4)),
                "lines (under 200, under 600, more)": lambda row: None if row["lines"] is None else sum(row["lines"] >= least for least in (200, 600)),
                **{f"names a {name} gap": (lambda row, name=name: row["classes"][name] > 0) for name in classes}}
    for name, feature in features.items():
        kept = [(row, label) for row, label in zip(rows, labels) if feature(row) is not None]
        kept_rows, kept_labels = [row for row, _ in kept], [label for _, label in kept]
        groups = collections.defaultdict(list)
        for row, label in kept:
            groups[feature(row)].append(label)
        gain = brier_gain(kept_rows, kept_labels, feature)
        reached = 0
        for _ in range(SHUFFLES):
            shuffled = kept_labels[:]
            chance.shuffle(shuffled)
            reached += brier_gain(kept_rows, shuffled, feature) >= gain
        predicts = reached / SHUFFLES < CHANCE / len(features) and min(map(len, groups.values())) >= SMALLEST
        predicting += [name] if predicts else []
        rates = ", ".join(f"{value}: {sum(group)} of {len(group)}" for value, group in sorted(groups.items(), key=lambda pair: str(pair[0])))
        print(f"{'predicts' if predicts else 'no signal'}: {name}; missed {rates}; Brier gain {gain:+.4f}, reached by {reached} of {SHUFFLES} shuffles")
    print(f"features that predict: {', '.join(predicting)}" if predicting else "no feature predicts")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
