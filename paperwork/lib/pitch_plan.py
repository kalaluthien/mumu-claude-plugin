"""Pitch plan: load, check, ids, answer parse, apply and render.

A plan is {"title", "parts": [Part]}; the grammar is in the pitch skill's
references/grammar.md. Every function here is a calculation: no file or
network access besides load_file.
"""
import hashlib
import json
import re

KIND_RE = re.compile(r"^[a-z][a-z-]*$")
PART_KEYS = {"text", "kind", "source", "parts", "pick", "else"}
OPTION_KEYS = {"text", "parts", "then"}
QUESTION_KEYS = {"text", "pick", "else"}
LEAF_KEYS = {"text", "parts"}
OPTION_PART_KEYS = {"text", "kind", "source", "parts"}


class PlanError(Exception):
    """A plan the checker refuses: where, which named rule, and why."""

    def __init__(self, path, rule, detail):
        super().__init__(f"{path}: {rule}: {detail}")
        self.path, self.rule, self.detail = path, rule, detail


class AnswerError(Exception):
    def __init__(self, line, detail):
        super().__init__(f"line {line}: {detail}")
        self.line, self.detail = line, detail


# -- load ------------------------------------------------------------------

def _no_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise PlanError("$", "duplicate-key", f"key '{key}' is written twice in one object")
        seen[key] = value
    return seen


def load(text):
    """Parse JSON text; a duplicate key is refused because json keeps only the last."""
    try:
        return json.loads(text, object_pairs_hook=_no_duplicates)
    except json.JSONDecodeError as e:
        raise PlanError("$", "bad-json", str(e))


def load_file(path):
    with open(path, encoding="utf-8") as f:
        return load(f.read())


# -- check -----------------------------------------------------------------

def _obj(value, path, errors):
    if not isinstance(value, dict):
        errors.append((path, "wrong-type", "expected an object"))
        return False
    return True


def _keys(d, allowed, path, errors):
    for k in d:
        if k not in allowed:
            errors.append((f"{path}.{k}", "unknown-key", f"'{k}' is not part of the grammar here"))


def _text(d, path, errors):
    t = d.get("text")
    if not isinstance(t, str) or not t.strip():
        errors.append((f"{path}.text", "empty-text", "text must be a non-empty string"))


def _parts(value, path, errors, in_option=False):
    if not isinstance(value, list):
        errors.append((path, "wrong-type", "parts must be a list"))
        return
    for i, p in enumerate(value, 1):
        _part(p, f"{path}[{i}]", errors, in_option)


def _leaf_list(d, path, errors, keys, with_then):
    for name, opt in _options(d):
        _option(opt, f"{path}.{name}", errors, keys, with_then)


def _options(d):
    """(name, option) pairs of a Decision or Question, pick first, in pressing order."""
    out = []
    if "pick" in d:
        out.append(("pick", d["pick"]))
    extra = d.get("else")
    if isinstance(extra, list):
        out += [(f"else[{i}]", o) for i, o in enumerate(extra, 1)]
    return out


def _option(o, path, errors, keys, with_then):
    if not _obj(o, path, errors):
        return
    _keys(o, keys, path, errors)
    _text(o, path, errors)
    if "parts" in o:
        _parts(o["parts"], f"{path}.parts", errors, in_option=True)
    if with_then and "then" in o:
        q = o["then"]
        if _obj(q, f"{path}.then", errors):
            _question(q, f"{path}.then", errors)


def _question(q, path, errors):
    _keys(q, QUESTION_KEYS, path, errors)
    _text(q, path, errors)
    _decision_shape(q, path, errors, LEAF_KEYS, False)


def _decision_shape(d, path, errors, option_keys, with_then):
    if "else" in d and "pick" not in d:
        errors.append((f"{path}.else", "else-needs-pick", "a Decision with other options needs the agent's pick"))
    if "pick" not in d and "else" not in d:
        errors.append((path, "pick-missing", "a Question needs a pick"))
    if "else" in d and not isinstance(d["else"], list):
        errors.append((f"{path}.else", "wrong-type", "else must be a list of options"))
        return
    _leaf_list(d, path, errors, option_keys, with_then)


def _part(p, path, errors, in_option=False):
    if not _obj(p, path, errors):
        return
    _keys(p, OPTION_PART_KEYS if in_option else PART_KEYS, path, errors)
    if in_option:
        for k in ("pick", "else"):
            if k in p:
                errors.append((f"{path}.{k}", "decision-in-option", "an option's parts hold no Decision"))
    _text(p, path, errors)
    if "kind" in p and not (isinstance(p["kind"], str) and KIND_RE.match(p["kind"])):
        errors.append((f"{path}.kind", "bad-kind", "kind is a lowercase word, letters and '-' only"))
    if "source" in p and not isinstance(p["source"], str):
        errors.append((f"{path}.source", "wrong-type", "source must be a string"))
    if "parts" in p:
        _parts(p["parts"], f"{path}.parts", errors, in_option)
    if not in_option and ("pick" in p or "else" in p):
        _decision_shape(p, path, errors, OPTION_KEYS, True)


def check(plan):
    """Return a list of (path, rule, detail); empty means the plan is accepted."""
    errors = []
    if not _obj(plan, "$", errors):
        return errors
    _keys(plan, {"title", "parts"}, "$", errors)
    t = plan.get("title")
    if not isinstance(t, str) or not t.strip():
        errors.append(("$.title", "empty-text", "title must be a non-empty string"))
    if "parts" not in plan:
        errors.append(("$.parts", "missing-key", "a plan needs parts"))
    else:
        _parts(plan["parts"], "$.parts", errors)
    return errors


# -- ids -------------------------------------------------------------------

def walk(parts, prefix=""):
    """Depth-first over parts only, 1-based, dot-joined: yields (id, part)."""
    for i, p in enumerate(parts, 1):
        pid = f"{prefix}{i}"
        yield pid, p
        yield from walk(p.get("parts", []), pid + ".")


def index(plan):
    return dict(walk(plan["parts"]))


def options(d):
    """The options of a Decision or Question as pressed: pick is 1, then else in order."""
    return ([d["pick"]] if "pick" in d else []) + list(d.get("else", []))


def is_decision(p):
    return "pick" in p


# -- answer ----------------------------------------------------------------

_ENTRY = re.compile(r"^- (\d+(?:\.\d+)*) (.+)$")
_PICK = re.compile(r"^pick (\d+)(?: then (\d+))?$")
_TEXT_VERBS = ("other", "struck", "comment", "edited")


def parse_answer(md):
    """Parse the Answer form into [(line, id, verb, arg)]; verb is pick/other/struck/comment/edited."""
    out = []
    for n, raw in enumerate(md.splitlines(), 1):
        line = raw.rstrip()
        if not line.strip() or line.startswith("# "):
            continue
        m = _ENTRY.match(line)
        if not m:
            raise AnswerError(n, "cannot parse this line; expected '- <id> <verb>'")
        pid, rest = m.groups()
        pm = _PICK.match(rest)
        if pm:
            out.append((n, pid, "pick", (int(pm.group(1)), int(pm.group(2)) if pm.group(2) else None)))
            continue
        verb, sep, arg = rest.partition(":")
        if verb not in _TEXT_VERBS or not sep or not arg.strip():
            raise AnswerError(n, "cannot parse this line; expected 'pick N [then M]' or '<verb>: <text>'")
        out.append((n, pid, verb, arg.strip()))
    return out


def _promote(d, n):
    """Make option n (1-based) the pick; the rest follow in their old order."""
    opts = options(d)
    chosen, rest = opts[n - 1], opts[:n - 1] + opts[n:]
    d["pick"] = chosen
    if rest:
        d["else"] = rest
    else:
        d.pop("else", None)


def apply_answer(plan, entries):
    """Return the next plan. Ids refer to the plan as given; struck parts go last."""
    new = json.loads(json.dumps(plan))
    ids = index(new)
    parent = {}
    for pid, _ in walk(new["parts"]):
        parent[pid] = pid.rpartition(".")[0]
    choice = {}
    struck = set()
    for n, pid, verb, arg in entries:
        part = ids.get(pid)
        if part is None:
            raise AnswerError(n, f"unknown part id {pid}")
        if verb in ("pick", "other"):
            if not is_decision(part):
                raise AnswerError(n, f"part {pid} has no options")
            if pid in choice:
                raise AnswerError(n, f"part {pid} is answered twice")
            choice[pid] = n
        if verb == "pick":
            k, then = arg
            opts = options(part)
            if not 1 <= k <= len(opts):
                raise AnswerError(n, f"pick {k} is out of range 1-{len(opts)} for part {pid}")
            if then is not None:
                q = opts[k - 1].get("then")
                if q is None:
                    raise AnswerError(n, f"option {k} of part {pid} has no follow-up")
                if not 1 <= then <= len(options(q)):
                    raise AnswerError(n, f"then {then} is out of range 1-{len(options(q))} for part {pid}")
    for n, pid, verb, arg in entries:
        part = ids[pid]
        if verb == "pick":
            k, then = arg
            _promote(part, k)
            if then is not None:
                _promote(part["pick"]["then"], then)
        elif verb == "other":
            old = options(part)
            part["pick"] = {"text": arg}
            part["else"] = old
        elif verb == "comment":
            part.setdefault("parts", []).append({"kind": "comment", "text": arg})
        elif verb == "edited":
            part["text"] = arg
        elif verb == "struck":
            struck.add(pid)
    for pid in sorted(struck, key=lambda s: -len(s)):
        par = parent[pid]
        siblings = new["parts"] if not par else ids[par]["parts"]
        for i, p in enumerate(siblings):
            if p is ids[pid]:
                del siblings[i]
                break
    return new


_HEAD = re.compile(r"^# Answer: (.+) · plan ([0-9a-f]{8})$")


def stamp(plan):
    """Eight hex digits naming this exact plan version."""
    raw = json.dumps(plan, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


def check_head(plan, md):
    """Refuse an Answer made from another plan or version, since its ids would land on other Parts."""
    for n, raw in enumerate(md.splitlines(), 1):
        if not raw.strip():
            continue
        m = _HEAD.match(raw.rstrip())
        if not m:
            raise AnswerError(n, "the first line must be '# Answer: <title> · plan <stamp>'")
        if m.group(1) != plan["title"]:
            raise AnswerError(n, f"this Answer is for '{m.group(1)}', not '{plan['title']}'")
        if m.group(2) != stamp(plan):
            raise AnswerError(n, f"this Answer is for plan {m.group(2)}, but this version is {stamp(plan)}; build its page again")
        return
    raise AnswerError(1, "the Answer is empty")
