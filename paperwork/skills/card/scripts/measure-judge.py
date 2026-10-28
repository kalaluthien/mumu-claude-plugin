#!/usr/bin/env python3
"""Measure how far a judge's verdicts can be trusted, per criterion.

usage: measure-judge.py alpha spec.json runs/                  Krippendorff's alpha across the verdict files in runs/
       measure-judge.py human spec.json judge.json human.json  Cohen's kappa, macro F1 and MET-rate gap against people
       measure-judge.py bias spec.json verdicts.json           per perturbation kind and tier, the share of verdicts that
                                                               change; an answer <a>~<kind> perturbs answer <a>

Exit status 0 means done, 1 an invalid spec or verdict file, 2 a usage error.
"""
import json
import pathlib
import statistics
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from rubric.spec import line, violations  # noqa: E402
from rubric.verdicts import criteria, problems  # noqa: E402

# Krippendorff, Content Analysis, 2nd ed., 2004, p. 241: the agreement needed to draw conclusions from the data
BAR = 0.800
KINDS = ("paraphrase", "padding", "length", "order-swap", "mentioned-not-committed")


def read(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit(f"{path}: not a JSON document: {e}")


def load(spec_path, verdict_paths, complete):
    spec, files = read(spec_path), [read(path) for path in verdict_paths]
    out = [f"{spec_path}: {line(rule, where, message)}" for rule, where, message, severity in violations(spec) if severity == "error"]
    if not out:
        for path, verdict_file in zip(verdict_paths, files):
            out += [f"{path}: {line('verdicts-invalid', *problem.split(': ', 1))}" for problem in problems(spec, verdict_file, complete=complete)]
    if out:
        print("\n".join(out))
        sys.exit(1)
    return spec, files


def nominal_alpha(units):
    """Krippendorff's alpha for nominal values, each unit the values its coders gave; None when every value is one."""
    coincidences = Counter()
    for values in units:
        unit_size = len(values)
        for index, value in enumerate(values):
            for other_index, other_value in enumerate(values):
                if index != other_index:
                    coincidences[value, other_value] += 1 / (unit_size - 1)
    value_totals = Counter()
    for (value, _), weight in coincidences.items():
        value_totals[value] += weight
    n = sum(value_totals.values())
    expected = sum(value_totals[first_value] * value_totals[second_value] for first_value in value_totals for second_value in value_totals if first_value != second_value)
    if not expected:
        return None
    return 1 - (n - 1) * sum(pair_weight for (first_value, second_value), pair_weight in coincidences.items() if first_value != second_value) / expected


def alpha(spec, runs):
    names = sorted({answer for run in runs for answer in run["answers"]})
    for criterion in criteria(spec):
        units = [[run["answers"][answer][criterion["id"]] for run in runs if criterion["id"] in run["answers"].get(answer, {})] for answer in names]
        paired = [unit for unit in units if len(unit) > 1]
        if not paired:
            print(f"{criterion['id']}: alpha undefined, no answer graded by two runs")
            continue
        agreement = nominal_alpha(paired)
        if agreement is None:
            print(f"{criterion['id']}: alpha undefined, every verdict the same")
            continue
        print(f"{criterion['id']}: alpha {agreement:.3f}")
        if agreement < BAR:
            print(f"rewrite {criterion['id']}: alpha {agreement:.3f} < {BAR:.3f}")
    print(f"Alpha is how far the runs agree beyond chance, 1 full agreement and 0 chance. Below {BAR:.3f}, Krippendorff's "
          "bar for drawing conclusions, a criterion's verdicts are not trusted: rewrite it, never reweight it.")


def kappa(truth, guess):
    n, labels = len(truth), set(truth) | set(guess)
    seen = sum(truth_label == guess_label for truth_label, guess_label in zip(truth, guess)) / n
    chance = sum(truth.count(label) * guess.count(label) for label in labels) / n ** 2
    return (seen - chance) / (1 - chance) if chance < 1 else float("nan")


def macro_harmonic_score(truth, guess):
    def harmonic_score(label):
        true_positives = sum(truth_label == label and guess_label == label for truth_label, guess_label in zip(truth, guess))
        wrong = sum((truth_label == label) != (guess_label == label) for truth_label, guess_label in zip(truth, guess))
        return 2 * true_positives / (2 * true_positives + wrong)
    return statistics.fmean(harmonic_score(label) for label in sorted(set(truth) | set(guess)))


def human(spec, judge, people):
    for criterion in criteria(spec):
        shared = [answer for answer in judge["answers"] if criterion["id"] in judge["answers"][answer] and criterion["id"] in people["answers"].get(answer, {})]
        if not shared:
            print(f"{criterion['id']}: no answer both graded")
            continue
        guess = [judge["answers"][answer][criterion["id"]] for answer in shared]
        truth = [people["answers"][answer][criterion["id"]] for answer in shared]
        gap = statistics.fmean(guess) - statistics.fmean(truth)
        print(f"{criterion['id']}: kappa {kappa(truth, guess):.3f} f1 {macro_harmonic_score(truth, guess):.3f} met-gap {gap:+.3f}")
    print("Kappa is agreement with people beyond chance; macro F1 weighs met and unmet alike; met-gap is the judge's "
          "share of met verdicts minus the people's, positive when the judge is lenient. Record them in the spec's "
          "judge calibration.")


def bias(spec, verdicts):
    answers = verdicts["answers"]
    bad = [answer for answer in answers if "~" in answer and (answer.split("~", 1)[0] not in answers or answer.split("~", 1)[1] not in KINDS)]
    if bad:
        print("\n".join(line("verdicts-invalid", f"verdicts.answers.{answer}", f"perturbs no answer, or its kind is not one "
                             f"of {', '.join(KINDS)}") for answer in bad))
        sys.exit(1)
    for kind in KINDS:
        pairs = [(answer.split("~", 1)[0], answer) for answer in answers if answer.endswith("~" + kind)]
        if not pairs:
            continue
        for tier in spec["tiers"]:
            if tier.get("pairwise"):
                continue
            ids = [criterion["id"] for criterion in tier["criteria"]]
            flip = statistics.fmean(answers[base_answer][criterion_id] != answers[perturbed_answer][criterion_id] for base_answer, perturbed_answer in pairs for criterion_id in ids)
            limit = tier.get("judge_error")
            tail = f" > judge_error {limit:g}" if limit is not None and flip > limit else ""
            print(f"{kind} {tier['id']}: flip {flip:.2f}{tail}")
    print("Flip is the share of a tier's verdicts that change when only the named surface of an answer changes; above "
          "the tier's judge_error the judge reacts to that surface, so the bias adds up across the tier.")


def main(args):
    command = args[0] if args else "help"
    if command == "alpha" and len(args) == 3:
        runs = sorted(pathlib.Path(args[2]).glob("*.json"))
        if len(runs) < 2:
            print(f"{args[2]}: alpha needs two or more verdict files", file=sys.stderr)
            return 2
        spec, files = load(args[1], runs, complete=False)
        alpha(spec, files)
        return 0
    if command == "human" and len(args) == 4:
        spec, (judge, people) = load(args[1], args[2:], complete=False)
        human(spec, judge, people)
        return 0
    if command == "bias" and len(args) == 3:
        spec, (verdicts,) = load(args[1], args[2:], complete=True)
        bias(spec, verdicts)
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
