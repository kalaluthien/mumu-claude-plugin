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

from rubric.model import reward, tier_scores  # noqa: E402
from rubric.spec import line, violations  # noqa: E402
from rubric.verdicts import problems  # noqa: E402

RESAMPLES = 2000


def read(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit(f"{path}: not a JSON document: {e}")


def load(spec_path, verdict_paths, groups=False):
    """The spec and each verdict file, or exit 1 naming each rule they break."""
    spec, files = read(spec_path), [read(path) for path in verdict_paths]
    out = [f"{spec_path}: {line(rule, where, message)}" for rule, where, message, severity in violations(spec) if severity == "error"]
    if not out:
        for path, verdict_file in zip(verdict_paths, files):
            out += [f"{path}: {line('verdicts-invalid', *problem.split(': ', 1))}" for problem in problems(spec, verdict_file, groups=groups)]
    if out:
        print("\n".join(out))
        sys.exit(1)
    return spec, files


def ranked(spec, verdicts):
    rows = [(answer, tier_scores(spec, verdicts, answer)) for answer in verdicts["answers"]]
    return sorted(rows, key=lambda row: -reward(spec, row[1]))


def scores_text(spec, scores):
    return ", ".join(f"{tier['id']} {tier_score:.3g}" for tier, tier_score in zip(spec["tiers"], scores))


def order(spec, verdicts):
    for answer, scores in ranked(spec, verdicts):
        print(f"{answer}: reward {reward(spec, scores):.6g} ({scores_text(spec, scores)})")
    print("Best first by reward, the sum of each tier's derived weight times its score: a higher tier decides unless "
          "two answers' scores there differ by less than its delta, and a lower tier orders what the higher ones tie.")


def score(spec, verdicts):
    for group_number, group in enumerate(verdicts["groups"], 1):
        rewards = {group_answer: reward(spec, tier_scores(spec, verdicts, group_answer)) for group_answer in group}
        mean, standard_deviation = statistics.fmean(rewards.values()), statistics.pstdev(rewards.values())
        for answer in group:
            advantage = (rewards[answer] - mean) / standard_deviation if standard_deviation > 1e-12 else 0.0
            print(f"group {group_number} {answer}: reward {rewards[answer]:.6g} advantage {advantage:.9f} "
                  f"({scores_text(spec, tier_scores(spec, verdicts, answer))})")
    print("Each advantage is the answer's reward minus its group's mean, over the group's standard deviation, so a "
          "group's advantages sum to 0 and spread 1; a group whose rewards all tie gets 0 and teaches nothing.")


def interval(rows, seed):
    """Per tier, the mean and its 95% percentile bootstrap interval over resampled answers."""
    random_generator, n = random.Random(seed), len(rows)
    means = [statistics.fmean(column) for column in zip(*rows)]
    draws = [[statistics.fmean(column) for column in zip(*(rows[random_generator.randrange(n)] for _ in range(n)))] for _ in range(RESAMPLES)]
    out = []
    for tier_index, mean in enumerate(means):
        sorted_draws = sorted(draw[tier_index] for draw in draws)
        out.append((mean, sorted_draws[int(0.025 * RESAMPLES)], sorted_draws[int(0.975 * RESAMPLES) - 1]))
    return out


def compare(spec, first_verdicts, second_verdicts, seed):
    sides = [interval([tier_scores(spec, system_verdicts, answer) for answer in system_verdicts["answers"]], seed) for system_verdicts in (first_verdicts, second_verdicts)]
    for tier, (first_mean, first_low, first_high), (second_mean, second_low, second_high) in zip(spec["tiers"], *sides):
        print(f"{tier['id']}: A {first_mean:.3f} [{first_low:.3f}, {first_high:.3f}] B {second_mean:.3f} [{second_low:.3f}, {second_high:.3f}]")
    for tier, (first_mean, *_), (second_mean, *_) in zip(spec["tiers"], *sides):
        if abs(first_mean - second_mean) > tier.get("delta", 0):
            print(f"{'A over B' if first_mean > second_mean else 'B over A'} at {tier['id']}")
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
    command = args[0] if args else "help"
    if command in ("order", "score") and len(args) == 3:
        spec, (verdicts,) = load(args[1], args[2:], groups=command == "score")
        (order if command == "order" else score)(spec, verdicts)
        return 0
    if command == "compare" and len(args) == 4:
        spec, (first_verdicts, second_verdicts) = load(args[1], args[2:])
        compare(spec, first_verdicts, second_verdicts, seed)
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
