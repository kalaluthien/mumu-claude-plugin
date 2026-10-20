#!/usr/bin/env python3
"""litmus: measure how far a judge's verdicts can be trusted, per criterion.

  measure-judge.py alpha spec.json runs/                  Krippendorff's alpha across the verdict files in runs/
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

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4] / "lib"))

from litmus.spec import line, violations  # noqa: E402
from litmus.verdicts import criteria, problems  # noqa: E402

# Krippendorff, Content Analysis, 2nd ed., 2004, p. 241: the agreement needed to draw conclusions from the data
BAR = 0.800
KINDS = ("paraphrase", "padding", "length", "order-swap", "mentioned-not-committed")


def read(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit(f"{path}: not a JSON document: {e}")


def load(spec_path, verdict_paths, complete):
    spec, files = read(spec_path), [read(p) for p in verdict_paths]
    out = [f"{spec_path}: {line(r, w, m)}" for r, w, m, sev in violations(spec) if sev == "error"]
    if not out:
        for p, v in zip(verdict_paths, files):
            out += [f"{p}: {line('verdicts-invalid', *t.split(': ', 1))}" for t in problems(spec, v, complete=complete)]
    if out:
        print("\n".join(out))
        sys.exit(1)
    return spec, files


def nominal_alpha(units):
    """Krippendorff's alpha for nominal values, each unit the values its coders gave; None when every value is one."""
    o = Counter()
    for values in units:
        m = len(values)
        for i, c in enumerate(values):
            for j, k in enumerate(values):
                if i != j:
                    o[c, k] += 1 / (m - 1)
    n_c = Counter()
    for (c, _), w in o.items():
        n_c[c] += w
    n = sum(n_c.values())
    expected = sum(n_c[c] * n_c[k] for c in n_c for k in n_c if c != k)
    if not expected:
        return None
    return 1 - (n - 1) * sum(w for (c, k), w in o.items() if c != k) / expected


def alpha(spec, runs):
    names = sorted({a for run in runs for a in run["answers"]})
    for c in criteria(spec):
        units = [[run["answers"][a][c["id"]] for run in runs if c["id"] in run["answers"].get(a, {})] for a in names]
        paired = [u for u in units if len(u) > 1]
        if not paired:
            print(f"{c['id']}: alpha undefined, no answer graded by two runs")
            continue
        x = nominal_alpha(paired)
        if x is None:
            print(f"{c['id']}: alpha undefined, every verdict the same")
            continue
        print(f"{c['id']}: alpha {x:.3f}")
        if x < BAR:
            print(f"rewrite {c['id']}: alpha {x:.3f} < {BAR:.3f}")
    print(f"Alpha is how far the runs agree beyond chance, 1 full agreement and 0 chance. Below {BAR:.3f}, Krippendorff's "
          "bar for drawing conclusions, a criterion's verdicts are not trusted: rewrite it, never reweight it.")


def kappa(truth, guess):
    n, labels = len(truth), set(truth) | set(guess)
    seen = sum(t == g for t, g in zip(truth, guess)) / n
    chance = sum(truth.count(x) * guess.count(x) for x in labels) / n ** 2
    return (seen - chance) / (1 - chance) if chance < 1 else float("nan")


def macro_f1(truth, guess):
    def f1(x):
        tp = sum(t == x and g == x for t, g in zip(truth, guess))
        wrong = sum((t == x) != (g == x) for t, g in zip(truth, guess))
        return 2 * tp / (2 * tp + wrong)
    return statistics.fmean(f1(x) for x in sorted(set(truth) | set(guess)))


def human(spec, judge, people):
    for c in criteria(spec):
        shared = [a for a in judge["answers"] if c["id"] in judge["answers"][a] and c["id"] in people["answers"].get(a, {})]
        if not shared:
            print(f"{c['id']}: no answer both graded")
            continue
        guess = [judge["answers"][a][c["id"]] for a in shared]
        truth = [people["answers"][a][c["id"]] for a in shared]
        gap = statistics.fmean(guess) - statistics.fmean(truth)
        print(f"{c['id']}: kappa {kappa(truth, guess):.3f} f1 {macro_f1(truth, guess):.3f} met-gap {gap:+.3f}")
    print("Kappa is agreement with people beyond chance; macro F1 weighs met and unmet alike; met-gap is the judge's "
          "share of met verdicts minus the people's, positive when the judge is lenient. Record them in the spec's "
          "judge calibration.")


def bias(spec, verdicts):
    answers = verdicts["answers"]
    bad = [a for a in answers if "~" in a and (a.split("~", 1)[0] not in answers or a.split("~", 1)[1] not in KINDS)]
    if bad:
        print("\n".join(line("verdicts-invalid", f"verdicts.answers.{a}", f"perturbs no answer, or its kind is not one "
                             f"of {', '.join(KINDS)}") for a in bad))
        sys.exit(1)
    for kind in KINDS:
        pairs = [(a.split("~", 1)[0], a) for a in answers if a.endswith("~" + kind)]
        if not pairs:
            continue
        for tier in spec["tiers"]:
            if tier.get("pairwise"):
                continue
            ids = [c["id"] for c in tier["criteria"]]
            flip = statistics.fmean(answers[b][k] != answers[p][k] for b, p in pairs for k in ids)
            limit = tier.get("judge_error")
            tail = f" > judge_error {limit:g}" if limit is not None and flip > limit else ""
            print(f"{kind} {tier['id']}: flip {flip:.2f}{tail}")
    print("Flip is the share of a tier's verdicts that change when only the named surface of an answer changes; above "
          "the tier's judge_error the judge reacts to that surface, so the bias adds up across the tier.")


def main(args):
    cmd = args[0] if args else "help"
    if cmd == "alpha" and len(args) == 3:
        runs = sorted(pathlib.Path(args[2]).glob("*.json"))
        if len(runs) < 2:
            print(f"{args[2]}: alpha needs two or more verdict files", file=sys.stderr)
            return 2
        spec, files = load(args[1], runs, complete=False)
        alpha(spec, files)
        return 0
    if cmd == "human" and len(args) == 4:
        spec, (judge, people) = load(args[1], args[2:], complete=False)
        human(spec, judge, people)
        return 0
    if cmd == "bias" and len(args) == 3:
        spec, (verdicts,) = load(args[1], args[2:], complete=True)
        bias(spec, verdicts)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
