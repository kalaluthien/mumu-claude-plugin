#!/usr/bin/env python3
"""Print an LLM judge's agreement with human labels, and optionally a corrected pass rate.

Input: a CSV with columns `human` and `judge`, each `pass` or `fail` (any case).
With --observed P (the judge's pass share on unlabelled traces), also print the
Rogan-Gladen corrected rate and a 95% bootstrap interval over the labelled rows.
"""
import argparse
import csv
import random
import sys


def rates(pairs):
    tp = sum(1 for h, j in pairs if h and j)
    fn = sum(1 for h, j in pairs if h and not j)
    tn = sum(1 for h, j in pairs if not h and not j)
    fp = sum(1 for h, j in pairs if not h and j)
    tpr = tp / (tp + fn) if tp + fn else None
    tnr = tn / (tn + fp) if tn + fp else None
    return tpr, tnr, tp + fn, tn + fp


def corrected(p_obs, tpr, tnr):
    denom = tpr + tnr - 1
    if abs(denom) < 1e-6:
        return None
    return min(1.0, max(0.0, (p_obs + tnr - 1) / denom))


def verdict(value, row, column):
    word = value.strip().lower()
    if word not in ("pass", "fail"):
        sys.exit(f"row {row}: {column} is {value!r}, not pass or fail")
    return word == "pass"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv")
    parser.add_argument("--observed", type=float, help="judge pass share on unlabelled traces, 0-1")
    parser.add_argument("--resamples", type=int, default=2000)
    args = parser.parse_args()

    if args.observed is not None and not 0 <= args.observed <= 1:
        sys.exit(f"--observed is {args.observed}, not a share between 0 and 1")
    with open(args.csv, newline="") as f:
        reader = csv.DictReader(f)
        missing = {"human", "judge"} - set(reader.fieldnames or [])
        if missing:
            sys.exit(f"{args.csv}: no column {', '.join(sorted(missing))}")
        pairs = [(verdict(r["human"], i, "human"), verdict(r["judge"], i, "judge"))
                 for i, r in enumerate(reader, start=2)]
    tpr, tnr, n_pass, n_fail = rates(pairs)
    print(f"rows {len(pairs)}: human pass {n_pass}, human fail {n_fail}")
    if tpr is None or tnr is None:
        sys.exit("need at least one human pass and one human fail")
    print(f"TPR {tpr:.3f}  TNR {tnr:.3f}")
    if args.observed is None:
        return

    theta = corrected(args.observed, tpr, tnr)
    if theta is None:
        sys.exit("TPR + TNR is 1: the judge is guessing, so no rate is printed")
    rng = random.Random(0)
    estimates = []
    for _ in range(args.resamples):
        t, n, _, _ = rates([rng.choice(pairs) for _ in pairs])
        e = corrected(args.observed, t, n) if t is not None and n is not None else None
        if e is not None:
            estimates.append(e)
    estimates.sort()
    lo = estimates[int(0.025 * len(estimates))]
    hi = estimates[min(len(estimates) - 1, int(0.975 * len(estimates)))]
    print(f"observed {args.observed:.3f}  corrected {theta:.3f}  95% interval [{lo:.3f}, {hi:.3f}]"
          f" ({len(estimates)} of {args.resamples} resamples usable)")


if __name__ == "__main__":
    main()
