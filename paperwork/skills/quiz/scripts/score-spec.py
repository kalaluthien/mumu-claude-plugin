#!/usr/bin/env python3
"""Apply a grading spec to a verdict file, whose format the grammar holds as $defs/verdicts.

usage: score-spec.py order spec.json verdicts.json                 answers best first, one per line, with tier scores
       score-spec.py score spec.json verdicts.json                 per group, each answer's tier scores, reward and advantage
       score-spec.py compare spec.json a.json b.json [--seed n]    per tier each system's mean with a 95% bootstrap interval,
                                                                   then which system is ahead, each delta the indifference band

Exit status 0 means done, 1 an invalid spec or verdict file, 2 a usage error.
"""
import json
import pathlib
import random
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from quiz.model import group_of, reward, tier_scores  # noqa: E402
from quiz.spec import line, violations  # noqa: E402
from quiz.verdicts import problems  # noqa: E402

RESAMPLES = 2000


def read(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit(f"{path}: not a JSON document: {e}")


def load(spec_path, verdict_paths, groups=False):
    """The spec and each verdict file, or exit 1 naming each rule they break."""
    spec, files = read(spec_path), [read(p) for p in verdict_paths]
    out = [f"{spec_path}: {line(r, w, m)}" for r, w, m, sev in violations(spec) if sev == "error"]
    if not out:
        for p, v in zip(verdict_paths, files):
            out += [f"{p}: {line('verdicts-invalid', *t.split(': ', 1))}" for t in problems(spec, v, groups=groups)]
    if out:
        print("\n".join(out))
        sys.exit(1)
    return spec, files


def ranked(spec, verdicts):
    rows = [(a, tier_scores(spec, verdicts, a)) for a in verdicts["answers"]]
    return sorted(rows, key=lambda row: -reward(spec, row[1]))


def scores_text(spec, scores):
    return ", ".join(f"{t['id']} {u:.3g}" for t, u in zip(spec["tiers"], scores))


def order(spec, verdicts):
    for a, scores in ranked(spec, verdicts):
        print(f"{a}: reward {reward(spec, scores):.6g} ({scores_text(spec, scores)})")
    print("Best first by reward, the sum of each tier's derived weight times its score: a higher tier decides unless "
          "two answers' scores there differ by less than its delta, and a lower tier orders what the higher ones tie.")


def score(spec, verdicts):
    for g, group in enumerate(verdicts["groups"], 1):
        rewards = {a: reward(spec, tier_scores(spec, verdicts, a)) for a in group}
        mean, sd = statistics.fmean(rewards.values()), statistics.pstdev(rewards.values())
        for a in group:
            adv = (rewards[a] - mean) / sd if sd > 1e-12 else 0.0
            print(f"group {g} {a}: reward {rewards[a]:.6g} advantage {adv:.9f} "
                  f"({scores_text(spec, tier_scores(spec, verdicts, a))})")
    print("Each advantage is the answer's reward minus its group's mean, over the group's standard deviation, so a "
          "group's advantages sum to 0 and spread 1; a group whose rewards all tie gets 0 and teaches nothing.")


def interval(rows, seed):
    """Per tier, the mean and its 95% percentile bootstrap interval over resampled answers."""
    rng, n = random.Random(seed), len(rows)
    means = [statistics.fmean(col) for col in zip(*rows)]
    draws = [[statistics.fmean(col) for col in zip(*(rows[rng.randrange(n)] for _ in range(n)))] for _ in range(RESAMPLES)]
    out = []
    for d, m in enumerate(means):
        col = sorted(x[d] for x in draws)
        out.append((m, col[int(0.025 * RESAMPLES)], col[int(0.975 * RESAMPLES) - 1]))
    return out


def compare(spec, a, b, seed):
    sides = [interval([tier_scores(spec, v, x) for x in v["answers"]], seed) for v in (a, b)]
    for tier, (ma, la, ha), (mb, lb, hb) in zip(spec["tiers"], *sides):
        print(f"{tier['id']}: A {ma:.3f} [{la:.3f}, {ha:.3f}] B {mb:.3f} [{lb:.3f}, {hb:.3f}]")
    for tier, (ma, *_), (mb, *_) in zip(spec["tiers"], *sides):
        if abs(ma - mb) > tier.get("delta", 0):
            print(f"{'A over B' if ma > mb else 'B over A'} at {tier['id']}")
            break
    else:
        print("indifferent")
    print("The first tier, highest first, whose means differ by more than its delta decides; a smaller difference is "
          "inside the indifference band and hands the decision down. An interval that overlaps the other system's "
          "says the decision may not survive a new sample of answers.")


def main(args):
    seed = 0
    if "--seed" in args:
        i = args.index("--seed")
        if i + 1 >= len(args) or not args[i + 1].lstrip("-").isdigit():
            print(__doc__, file=sys.stderr)
            return 2
        seed, args = int(args[i + 1]), args[:i] + args[i + 2:]
    cmd = args[0] if args else "help"
    if cmd in ("order", "score") and len(args) == 3:
        spec, (verdicts,) = load(args[1], args[2:], groups=cmd == "score")
        (order if cmd == "order" else score)(spec, verdicts)
        return 0
    if cmd == "compare" and len(args) == 4:
        spec, (a, b) = load(args[1], args[2:])
        compare(spec, a, b, seed)
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
