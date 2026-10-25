"""A grading spec against its grammar (rubric.schema.json) and the rules the grammar cannot state."""
import json
import pathlib
import re

from rubric.model import GROUP_SIZE, no_signal, weights
from schema.model import shape

GRAMMAR = pathlib.Path(__file__).resolve().parents[2] / "skills/rubric/references/spec/assets/rubric.schema.json"
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
    for t, tier in enumerate(spec.get("tiers") or []):
        if not isinstance(tier, dict):
            continue
        out += [(r, f"spec.tiers[{t}].{k}", "is derived, never written") for k, r in SCHEMA["$defs"]["tier"]["x-forbidden"].items() if k in tier]
        for c, crit in enumerate(tier.get("criteria") or []):
            if isinstance(crit, dict):
                out += [(r, f"spec.tiers[{t}].criteria[{c}].{k}", "is not part of the grammar")
                        for k, r in SCHEMA["$defs"]["criterion"]["x-forbidden"].items() if k in crit]
    return out


def without_forbidden(spec):
    clean = json.loads(json.dumps(spec))
    for tier in clean.get("tiers") or []:
        if isinstance(tier, dict):
            for k in SCHEMA["$defs"]["tier"]["x-forbidden"]:
                tier.pop(k, None)
            for crit in tier.get("criteria") or []:
                if isinstance(crit, dict):
                    for k in SCHEMA["$defs"]["criterion"]["x-forbidden"]:
                        crit.pop(k, None)
    return clean


def violations(spec):
    """Every violation as (rule, path, message, severity): the grammar's first, then the rules that need a valid shape."""
    if not isinstance(spec, dict):
        return [(r, *t.split(": ", 1), "error") for r, t in shape(spec, SCHEMA, "spec")]
    rows = [(r, w, m, "error") for r, w, m in forbidden(spec)]
    wrong = shape(without_forbidden(spec), SCHEMA, "spec")
    rows += [(r, *t.split(": ", 1), "error") for r, t in wrong]
    if isinstance(spec.get("tiers"), list) and not spec["tiers"]:   # shape() reads no minItems
        rows.append(("form", "spec.tiers", "holds no tier", "error"))
    if rows:   # nothing else reads true until the spec fits the grammar
        return rows
    return [(r, w, m, RULES[r][0]) for r, w, m in narrow(spec)]


def narrow(spec):
    tiers = spec["tiers"]
    out = []
    where = {}
    for t, tier in enumerate(tiers):
        for c, crit in enumerate(tier.get("criteria", [])):
            where.setdefault(crit["id"], (t, f"spec.tiers[{t}].criteria[{c}]"))
    ids = [tier["id"] for tier in tiers] + [c["id"] for tier in tiers for c in tier.get("criteria", [])]
    out += [("id-duplicate", "spec", f"{i} is used {ids.count(i)} times") for i in sorted(set(ids)) if ids.count(i) > 1]
    for t, tier in enumerate(tiers):
        at = f"spec.tiers[{t}]"
        if tier.get("pairwise") and t != len(tiers) - 1:
            out.append(("pairwise-not-last", at, f"{tier['id']} is pairwise but tier {t + 1} of {len(tiers)}"))
        if not tier.get("pairwise") and not tier.get("criteria"):
            out.append(("tier-empty", at, f"{tier['id']} has no criteria"))
        if t < len(tiers) - 1:
            out += [("threshold-missing", at, f"{tier['id']} names no {k}") for k in ("delta", "judge_error") if k not in tier]
        if "judge_error" in tier and not 0 <= tier["judge_error"] < 0.5:
            out.append(("judge-error-range", f"{at}.judge_error", f"{tier['judge_error']} is not in [0, 0.5)"))
        if "delta" in tier and not 0 < tier["delta"] <= 1:
            out.append(("delta-range", f"{at}.delta", f"{tier['delta']} is not in (0, 1]"))
        if tier.get("mask_below") and "pass_rate" in tier:
            dead = no_signal(tier["pass_rate"], spec.get("group_size", GROUP_SIZE))
            if dead > NO_SIGNAL:
                out.append(("mask-no-signal", at, f"{dead:.0%} of groups get no signal at pass_rate {tier['pass_rate']}"))
        for c, crit in enumerate(tier.get("criteria", [])):
            cat = f"{at}.criteria[{c}]"
            if (m := VAGUE.search(crit["text"])) and not crit.get("anchors"):
                out.append(("criterion-vague", cat, f"{m.group(0).strip()!r} has no anchors"))
            if (n := len(CONJUNCTION.findall(crit["text"]))) >= 2:
                out.append(("criterion-conjunction", cat, f"{n} conjunctions; split it unless they are one condition"))
            if crit["check"] == "judge" and not (crit.get("variants_ok") and crit.get("near_miss")):
                out.append(("boundary-missing", cat, "no variants_ok or no near_miss to test its boundary"))
    out += exchanges(spec, where)
    if not any(RULES[r][0] == "error" for r, _, _ in out):
        eps = weights(spec)
        if eps[-1] / eps[0] < TINY:
            out.append(("weight-tiny", f"spec.tiers[{len(tiers) - 1}]", f"its weight is {eps[-1] / eps[0]:.1e} of the top's: "
                        "normalise advantages per group, merge tiers, or lower the top tiers' judge_error"))
    return out


def exchanges(spec, where):
    tiers, out, seen = spec["tiers"], [], set()
    for x, ex in enumerate(spec["exchange"]):
        at = f"spec.exchange[{x}]"
        if ex["a"] not in where or ex["b"] not in where:
            out.append(("exchange-unknown", at, f"{ex['a']}/{ex['b']} names a criterion the spec does not have"))
            continue
        if ex["a"] == ex["b"]:
            out.append(("exchange-unknown", at, f"{ex['a']} is set against itself, which tests nothing"))
            continue
        seen.add(frozenset((ex["a"], ex["b"])))
        ta, tb = where[ex["a"]][0], where[ex["b"]][0]
        want = "same" if ta == tb else "a_over_b" if ta < tb else "b_over_a"
        if ex["result"] != want:
            out.append(("exchange-contradicts", at, f"{ex['a']}/{ex['b']} says {ex['result']} but their tiers say {want}"))
    for t, tier in enumerate(tiers):
        mine = [c["id"] for c in tier.get("criteria", [])]
        below = [c["id"] for c in tiers[t + 1].get("criteria", [])] if t + 1 < len(tiers) else []
        for cid in mine:
            peers = [p for p in mine if p != cid]
            if peers and not any(frozenset((cid, p)) in seen for p in peers):
                out.append(("exchange-peer-missing", where[cid][1], f"{cid} has no exchange with a peer in {tier['id']}"))
            if below and not any(frozenset((cid, b)) in seen for b in below):
                out.append(("exchange-below-missing", where[cid][1], f"{cid} has no exchange with {tiers[t + 1]['id']}"))
    return out
