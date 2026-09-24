#!/usr/bin/env python3
"""Print an LLM judge's agreement with human labels, and optionally a corrected pass rate.

Input: a CSV with columns `human` and `judge`, each `pass` or `fail` (any case).
Fail is the positive class: TPR is the share of human fails the judge fails, TNR
the share of human passes it passes. With --observed P (the judge's pass share on
unlabelled traces), also print the Rogan-Gladen corrected pass rate and a 95%
bootstrap interval over the labelled rows, and over P too given --unlabelled N.
No rate is printed while |TPR + TNR - 1| is under MARGIN: the judge is near guessing.
"""
import argparse
import csv
import random
import sys

MARGIN = 0.2


def rates(pairs):
    """pairs are (human passed, judge passed); fail is positive."""
    tp = sum(1 for h, j in pairs if not h and not j)
    fn = sum(1 for h, j in pairs if not h and j)
    tn = sum(1 for h, j in pairs if h and j)
    fp = sum(1 for h, j in pairs if h and not j)
    tpr = tp / (tp + fn) if tp + fn else None
    tnr = tn / (tn + fp) if tn + fp else None
    return tpr, tnr, tn + fp, tp + fn


def corrected(p_obs, tpr, tnr):
    denom = tpr + tnr - 1
    if abs(denom) < MARGIN:
        return None
    return min(1.0, max(0.0, (p_obs + tpr - 1) / denom))


def verdict(value, row, column):
    word = value.strip().lower()
    if word not in ("pass", "fail"):
        sys.exit(f"row {row}: {column} is {value!r}, not pass or fail")
    return word == "pass"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv")
    parser.add_argument("--observed", type=float, help="judge pass share on unlabelled traces, 0-1")
    parser.add_argument("--unlabelled", type=int, help="number of unlabelled traces behind --observed")
    parser.add_argument("--resamples", type=int, default=2000)
    args = parser.parse_args()

    if args.observed is not None and not 0 <= args.observed <= 1:
        sys.exit(f"--observed is {args.observed}, not a share between 0 and 1")
    if args.unlabelled is not None and (args.observed is None or args.unlabelled < 1):
        sys.exit("--unlabelled needs --observed and a count of at least 1")
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
        sys.exit(f"|TPR + TNR - 1| is under the margin {MARGIN}: the judge is near guessing, so no rate is printed")
    rng = random.Random(0)
    estimates = []
    for _ in range(args.resamples):
        t, n, _, _ = rates([rng.choice(pairs) for _ in pairs])
        p = args.observed
        if args.unlabelled:
            sd = (args.observed * (1 - args.observed) / args.unlabelled) ** 0.5  # binomial, by its normal approximation
            p = min(1.0, max(0.0, rng.gauss(args.observed, sd)))
        e = corrected(p, t, n) if t is not None and n is not None else None
        if e is not None:
            estimates.append(e)
    estimates.sort()
    lo = estimates[int(0.025 * len(estimates))]
    hi = estimates[min(len(estimates) - 1, int(0.975 * len(estimates)))]
    print(f"observed {args.observed:.3f}  corrected {theta:.3f}  95% interval [{lo:.3f}, {hi:.3f}]"
          f" ({len(estimates)} of {args.resamples} resamples usable)")


if __name__ == "__main__":
    main()
