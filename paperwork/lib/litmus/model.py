"""The tier model: tier weights derived from each tier's judge error and indifference band.

model.md derives the condition; this is its only implementation."""

# the condition is strict, so the least weight that meets it is scaled up by this margin
MARGIN = 1.05
GROUP_SIZE = 8


def weights(spec):
    """epsilon per tier, the last 1: each the least that keeps eps_d (1 - 2 e_d) delta_d above all lower tiers' sum."""
    tiers = spec["tiers"]
    eps = [1.0] * len(tiers)
    for d in range(len(tiers) - 2, -1, -1):
        seen = (1 - 2 * tiers[d]["judge_error"]) * tiers[d]["delta"]
        eps[d] = MARGIN * sum(eps[d + 1:]) / seen
    return eps


def no_signal(pass_rate, group_size=GROUP_SIZE):
    """The chance a group of answers all pass or all fail a masked tier, so the mask leaves it no order."""
    return pass_rate ** group_size + (1 - pass_rate) ** group_size

