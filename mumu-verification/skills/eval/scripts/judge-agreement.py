#!/usr/bin/env python3
"""Print an LLM judge's TPR and TNR against human labels (fail is positive), and a corrected pass rate.

Input: a CSV with columns `human` and `judge`, each `pass` or `fail`. With --observed P,
the judge's pass share on unlabelled traces, also print (P + TPR - 1) / (TPR + TNR - 1)
and a 95% bootstrap interval, over P too given --unlabelled N; none while |TPR + TNR - 1| < MARGIN.
"""
import argparse
import csv
import random
import sys

MARGIN = 0.2


def rates(pairs):
    """pairs are (human passed, judge passed); returns TPR, TNR, human passes, human fails."""
    fails, passes = [j for h, j in pairs if not h], [j for h, j in pairs if h]
    tpr = fails.count(False) / len(fails) if fails else None
    tnr = passes.count(True) / len(passes) if passes else None
    return tpr, tnr, len(passes), len(fails)


def corrected(p, tpr, tnr):
    if tpr is None or tnr is None or abs(tpr + tnr - 1) < MARGIN:
        return None
    return min(1.0, max(0.0, (p + tpr - 1) / (tpr + tnr - 1)))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv")
    parser.add_argument("--observed", type=float)
    parser.add_argument("--unlabelled", type=int)
    args = parser.parse_args()
    p = args.observed
    if p is not None and not 0 <= p <= 1 or args.unlabelled is not None and (p is None or args.unlabelled < 1):
        sys.exit("--observed is a share 0-1; --unlabelled needs --observed and a count of at least 1")
    with open(args.csv, newline="") as f:
        rows = [(r.get("human") or "", r.get("judge") or "") for r in csv.DictReader(f)]
    if any(v.strip().lower() not in ("pass", "fail") for row in rows for v in row):
        sys.exit(f"{args.csv}: every human and judge value must be pass or fail")
    pairs = [tuple(v.strip().lower() == "pass" for v in row) for row in rows]
    tpr, tnr, n_pass, n_fail = rates(pairs)
    print(f"rows {len(pairs)}: human pass {n_pass}, human fail {n_fail}")
    if tpr is None or tnr is None:
        sys.exit("need at least one human pass and one human fail")
    print(f"TPR {tpr:.3f}  TNR {tnr:.3f}")
    if p is None:
        return
    theta = corrected(p, tpr, tnr)
    if theta is None:
        sys.exit(f"|TPR + TNR - 1| is under the margin {MARGIN}: the judge is near guessing, so no rate is printed")
    rng, estimates = random.Random(0), []
    sd = (p * (1 - p) / args.unlabelled) ** 0.5 if args.unlabelled else 0
    for _ in range(2000):
        e = corrected(min(1.0, max(0.0, rng.gauss(p, sd))), *rates([rng.choice(pairs) for _ in pairs])[:2])
        estimates += [] if e is None else [e]
    estimates.sort()
    lo, hi = estimates[int(0.025 * len(estimates))], estimates[min(len(estimates) - 1, int(0.975 * len(estimates)))]
    print(f"observed {p:.3f}  corrected {theta:.3f}  95% interval [{lo:.3f}, {hi:.3f}]")


if __name__ == "__main__":
    main()
