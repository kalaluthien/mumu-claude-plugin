"""A grading spec against its grammar (rubric.schema.json) and the rules the grammar cannot state."""
import json
import pathlib
import re

from rubric.model import GROUP_SIZE, no_signal, weights
from schema.model import shape

GRAMMAR = pathlib.Path(__file__).resolve().parents[2] / "skills/card/references/spec/assets/rubric.schema.json"
SCHEMA = json.loads(GRAMMAR.read_text(encoding="utf-8"))

# the source rubric-authoring skill's word lists, English and Korean
VAGUE = re.compile(r"\b(appropriate|adequate|proper(ly)?|complete(ly)?|clear(ly)?|good|reasonable|relevant|sufficient)\b"
                   r"|적절|충분|완전한|명확|타당한|잘 ", re.I)
CONJUNCTION = re.compile(r"\band\b|그리고|및|하고 ", re.I)
# below this share of the top tier's weight, a lower tier's signal drowns in float noise unless advantages are normalised
TINY = 1e-3
NO_SIGNAL = 0.5

# rule: (severity, what it asks); the grammar states the first group by x-rule, x-required-rule or x-forbidden
RULES = {
    "form": ("error", "the spec fits the grammar's shape"),
    "version-missing": ("error", "the spec names the grammar version it is written in"),
    "polarity-unknown": ("error", "a criterion's polarity is + or -"),
    "provenance-missing": ("error", "a criterion cites where it came from: an expert failure, a near-miss, an exchange or a source rubric"),
    "epsilon-hand-set": ("error", "no tier or criterion carries a hand-set weight; check-spec.py weights derives them"),
    "verdict-unknown": ("error", "a criterion asks for a verdict of 0 or 1 only, so it carries no scale"),
    "id-duplicate": ("error", "each tier and criterion id is used once"),
    "tier-empty": ("error", "a tier that is not pairwise holds criteria"),
    "pairwise-not-last": ("error", "a pairwise tier is the last tier"),
    "threshold-missing": ("error", "every tier above the last names its delta and its judge_error"),
    "judge-error-range": ("error", "a judge_error is at least 0 and below 0.5, since at 0.5 a verdict carries no order"),
    "delta-range": ("error", "a delta is above 0 and at most 1"),
    "exchange-unknown": ("error", "an exchange names two different criteria of the spec"),
    "exchange-contradicts": ("error", "an exchange's result matches where its two criteria sit"),
    "exchange-peer-missing": ("error", "each criterion with a tier peer has an exchange with one"),
    "exchange-below-missing": ("error", "each criterion has an exchange with one of the next tier's criteria"),
    "criterion-vague": ("warning", "a vague word in a criterion has anchors that say what it means"),
    "criterion-conjunction": ("warning", "a criterion with two or more conjunctions is still one proposition"),
    "boundary-missing": ("warning", "a judge criterion carries variants it must pass and near-misses it must fail"),
    "mask-no-signal": ("warning", f"a mask leaves at most {NO_SIGNAL:.0%} of groups all passing or all failing"),
    "weight-tiny": ("warning", f"the lowest tier keeps at least {TINY:g} of the top tier's weight"),
}


def line(rule, where, message):
    return f"{where}: {rule}: {message}"


def forbidden(spec):
    """Each key the grammar names in x-forbidden, as its rule, so a hand-set number reads as what it is."""
    out = []
    for tier_index, tier in enumerate(spec.get("tiers") or []):
        if not isinstance(tier, dict):
            continue
        out += [(rule, f"spec.tiers[{tier_index}].{k}", "is derived, never written") for k, rule in SCHEMA["$defs"]["tier"]["x-forbidden"].items() if k in tier]
        for criterion_index, criterion in enumerate(tier.get("criteria") or []):
            if isinstance(criterion, dict):
                out += [(rule, f"spec.tiers[{tier_index}].criteria[{criterion_index}].{k}", "is not part of the grammar")
                        for k, rule in SCHEMA["$defs"]["criterion"]["x-forbidden"].items() if k in criterion]
    return out


def without_forbidden(spec):
    clean = json.loads(json.dumps(spec))
    for tier in clean.get("tiers") or []:
        if isinstance(tier, dict):
            for k in SCHEMA["$defs"]["tier"]["x-forbidden"]:
                tier.pop(k, None)
            for criterion in tier.get("criteria") or []:
                if isinstance(criterion, dict):
                    for k in SCHEMA["$defs"]["criterion"]["x-forbidden"]:
                        criterion.pop(k, None)
    return clean


def violations(spec):
    """Every violation as (rule, path, message, severity): the grammar's first, then the rules that need a valid shape."""
    if not isinstance(spec, dict):
        return [(rule, *text.split(": ", 1), "error") for rule, text in shape(spec, SCHEMA, "spec")]
    rows = [(rule, where, message, "error") for rule, where, message in forbidden(spec)]
    wrong = shape(without_forbidden(spec), SCHEMA, "spec")
    rows += [(rule, *text.split(": ", 1), "error") for rule, text in wrong]
    if isinstance(spec.get("tiers"), list) and not spec["tiers"]:   # shape() reads no minItems
        rows.append(("form", "spec.tiers", "holds no tier", "error"))
    if rows:   # nothing else reads true until the spec fits the grammar
        return rows
    return [(rule, where, message, RULES[rule][0]) for rule, where, message in narrow(spec)]


def narrow(spec):
    tiers = spec["tiers"]
    out = []
    where = {}
    for tier_index, tier in enumerate(tiers):
        for criterion_index, criterion in enumerate(tier.get("criteria", [])):
            where.setdefault(criterion["id"], (tier_index, f"spec.tiers[{tier_index}].criteria[{criterion_index}]"))
    ids = [tier["id"] for tier in tiers] + [entry["id"] for tier in tiers for entry in tier.get("criteria", [])]
    out += [("id-duplicate", "spec", f"{identifier} is used {ids.count(identifier)} times") for identifier in sorted(set(ids)) if ids.count(identifier) > 1]
    for tier_index, tier in enumerate(tiers):
        at = f"spec.tiers[{tier_index}]"
        if tier.get("pairwise") and tier_index != len(tiers) - 1:
            out.append(("pairwise-not-last", at, f"{tier['id']} is pairwise but tier {tier_index + 1} of {len(tiers)}"))
        if not tier.get("pairwise") and not tier.get("criteria"):
            out.append(("tier-empty", at, f"{tier['id']} has no criteria"))
        if tier_index < len(tiers) - 1:
            out += [("threshold-missing", at, f"{tier['id']} names no {field}") for field in ("delta", "judge_error") if field not in tier]
        if "judge_error" in tier and not 0 <= tier["judge_error"] < 0.5:
            out.append(("judge-error-range", f"{at}.judge_error", f"{tier['judge_error']} is not in [0, 0.5)"))
        if "delta" in tier and not 0 < tier["delta"] <= 1:
            out.append(("delta-range", f"{at}.delta", f"{tier['delta']} is not in (0, 1]"))
        if tier.get("mask_below") and "pass_rate" in tier:
            dead = no_signal(tier["pass_rate"], spec.get("group_size", GROUP_SIZE))
            if dead > NO_SIGNAL:
                out.append(("mask-no-signal", at, f"{dead:.0%} of groups get no signal at pass_rate {tier['pass_rate']}"))
        for criterion_index, criterion in enumerate(tier.get("criteria", [])):
            criterion_path = f"{at}.criteria[{criterion_index}]"
            if (match := VAGUE.search(criterion["text"])) and not criterion.get("anchors"):
                out.append(("criterion-vague", criterion_path, f"{match.group(0).strip()!r} has no anchors"))
            if (n := len(CONJUNCTION.findall(criterion["text"]))) >= 2:
                out.append(("criterion-conjunction", criterion_path, f"{n} conjunctions; split it unless they are one condition"))
            if criterion["check"] == "judge" and not (criterion.get("variants_ok") and criterion.get("near_miss")):
                out.append(("boundary-missing", criterion_path, "no variants_ok or no near_miss to test its boundary"))
    out += exchanges(spec, where)
    if not any(RULES[rule][0] == "error" for rule, _, _ in out):
        epsilons = weights(spec)
        if epsilons[-1] / epsilons[0] < TINY:
            out.append(("weight-tiny", f"spec.tiers[{len(tiers) - 1}]", f"its weight is {epsilons[-1] / epsilons[0]:.1e} of the top's: "
                        "normalise advantages per group, merge tiers, or lower the top tiers' judge_error"))
    return out


def exchanges(spec, where):
    tiers, out, seen = spec["tiers"], [], set()
    for exchange_index, exchange in enumerate(spec["exchange"]):
        at = f"spec.exchange[{exchange_index}]"
        if exchange["a"] not in where or exchange["b"] not in where:
            out.append(("exchange-unknown", at, f"{exchange['a']}/{exchange['b']} names a criterion the spec does not have"))
            continue
        if exchange["a"] == exchange["b"]:
            out.append(("exchange-unknown", at, f"{exchange['a']} is set against itself, which tests nothing"))
            continue
        seen.add(frozenset((exchange["a"], exchange["b"])))
        first_tier, second_tier = where[exchange["a"]][0], where[exchange["b"]][0]
        want = "same" if first_tier == second_tier else "a_over_b" if first_tier < second_tier else "b_over_a"
        if exchange["result"] != want:
            out.append(("exchange-contradicts", at, f"{exchange['a']}/{exchange['b']} says {exchange['result']} but their tiers say {want}"))
    for tier_index, tier in enumerate(tiers):
        mine = [criterion["id"] for criterion in tier.get("criteria", [])]
        below = [criterion["id"] for criterion in tiers[tier_index + 1].get("criteria", [])] if tier_index + 1 < len(tiers) else []
        for criterion_id in mine:
            peers = [peer for peer in mine if peer != criterion_id]
            if peers and not any(frozenset((criterion_id, peer)) in seen for peer in peers):
                out.append(("exchange-peer-missing", where[criterion_id][1], f"{criterion_id} has no exchange with a peer in {tier['id']}"))
            if below and not any(frozenset((criterion_id, below_id)) in seen for below_id in below):
                out.append(("exchange-below-missing", where[criterion_id][1], f"{criterion_id} has no exchange with {tiers[tier_index + 1]['id']}"))
    return out
