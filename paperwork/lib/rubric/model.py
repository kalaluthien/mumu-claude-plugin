"""The tier model: tier weights derived from each tier's judge error and indifference band.

model.md derives the condition; this is its only implementation."""

# the condition is strict, so the least weight that meets it is scaled up by this margin
MARGIN = 1.05
GROUP_SIZE = 8


def weights(spec):
    """epsilon per tier, the last 1: each the least that keeps eps_d (1 - 2 e_d) delta_d above all lower tiers' sum."""
    tiers = spec["tiers"]
    epsilons = [1.0] * len(tiers)
    for tier_index in range(len(tiers) - 2, -1, -1):
        seen = (1 - 2 * tiers[tier_index]["judge_error"]) * tiers[tier_index]["delta"]
        epsilons[tier_index] = MARGIN * sum(epsilons[tier_index + 1:]) / seen
    return epsilons


def no_signal(pass_rate, group_size=GROUP_SIZE):
    """The chance a group of answers all pass or all fail a masked tier, so the mask leaves it no order."""
    return pass_rate ** group_size + (1 - pass_rate) ** group_size


def group_of(verdicts, answer):
    """The answers graded beside this one: its group, else every answer in the file."""
    return next((group for group in verdicts.get("groups", []) if answer in group), list(verdicts["answers"]))


def tier_scores(spec, verdicts, answer):
    """u_d per tier: the mean of its criteria's verdicts, a - criterion counted as 1 - c; a pairwise tier's share of
    the group the answer beats; 0 below a masked tier that scores under its pass mark."""
    given, out, masked = verdicts["answers"][answer], [], False
    for tier in spec["tiers"]:
        if masked:
            out.append(0.0)
            continue
        if tier.get("pairwise"):
            others = [other for other in group_of(verdicts, answer) if other != answer]
            score = len(set(given.get("beats", [])) & set(others)) / len(others) if others else 0.0
        else:
            criteria = tier["criteria"]
            score = sum(given[criterion["id"]] if criterion["polarity"] == "+" else 1 - given[criterion["id"]] for criterion in criteria) / len(criteria)
        out.append(score)
        masked = tier.get("mask_below", False) and score < tier.get("pass", 1)
    return out


def reward(spec, scores):
    return sum(weight * score for weight, score in zip(weights(spec), scores))
