"""Tree plan: load, check, ids, answer parse, apply and render.

A plan is {"title", "parts": [Part]}; the grammar is in the tree skill's
references/grammar.md. Every function here is a calculation: no file or
network access besides load_file.
"""
import hashlib
import json
import re

KIND_PATTERN = re.compile(r"^[a-z][a-z-]*$")
# A source a reader can open: a link off the writer's machine, or a person and the day they said it, dot-free since the page draws it.
SOURCE_URL_PATTERN = re.compile(r"^https?://(?!localhost\b|127\.0\.0\.1\b|\[::1\])[^\s/]+\.[^\s/]+(/\S*)?$")
SOURCE_PERSON_PATTERN = re.compile(r"^[^/\\:,]+, \d{4}-\d{2}-\d{2}$")
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
    with open(path, encoding="utf-8") as file:
        return load(file.read())


# -- check -----------------------------------------------------------------

def _expect_object(value, path, errors):
    if not isinstance(value, dict):
        errors.append((path, "wrong-type", "expected an object"))
        return False
    return True


def _keys(node, allowed, path, errors):
    for k in node:
        if k not in allowed:
            errors.append((f"{path}.{k}", "unknown-key", f"'{k}' is not part of the grammar here"))


def _text(node, path, errors):
    text = node.get("text")
    if not isinstance(text, str) or not text.strip():
        errors.append((f"{path}.text", "empty-text", "text must be a non-empty string"))


def _parts(value, path, errors, in_option=False):
    if not isinstance(value, list):
        errors.append((path, "wrong-type", "parts must be a list"))
        return
    for i, part in enumerate(value, 1):
        _part(part, f"{path}[{i}]", errors, in_option)


def _leaf_list(decision, path, errors, keys, with_then):
    for name, option in _options(decision):
        _option(option, f"{path}.{name}", errors, keys, with_then)


def _options(decision):
    """(name, option) pairs of a Decision or Question, pick first, in pressing order."""
    out = []
    if "pick" in decision:
        out.append(("pick", decision["pick"]))
    extra = decision.get("else")
    if isinstance(extra, list):
        out += [(f"else[{i}]", option) for i, option in enumerate(extra, 1)]
    return out


def _option(option, path, errors, keys, with_then):
    if not _expect_object(option, path, errors):
        return
    _keys(option, keys, path, errors)
    _text(option, path, errors)
    if "parts" in option:
        _parts(option["parts"], f"{path}.parts", errors, in_option=True)
    if with_then and "then" in option:
        question = option["then"]
        if _expect_object(question, f"{path}.then", errors):
            _question(question, f"{path}.then", errors)


def _question(question, path, errors):
    _keys(question, QUESTION_KEYS, path, errors)
    _text(question, path, errors)
    _decision_shape(question, path, errors, LEAF_KEYS, False)


def _decision_shape(decision, path, errors, option_keys, with_then):
    if "else" in decision and "pick" not in decision:
        errors.append((f"{path}.else", "else-needs-pick", "a Decision with other options needs the agent's pick"))
    if "pick" not in decision and "else" not in decision:
        errors.append((path, "pick-missing", "a Question needs a pick"))
    if "else" in decision and not isinstance(decision["else"], list):
        errors.append((f"{path}.else", "wrong-type", "else must be a list of options"))
        return
    _leaf_list(decision, path, errors, option_keys, with_then)


def _part(part, path, errors, in_option=False):
    if not _expect_object(part, path, errors):
        return
    _keys(part, OPTION_PART_KEYS if in_option else PART_KEYS, path, errors)
    if in_option:
        for k in ("pick", "else"):
            if k in part:
                errors.append((f"{path}.{k}", "decision-in-option", "an option's parts hold no Decision"))
    _text(part, path, errors)
    if "kind" in part and not (isinstance(part["kind"], str) and KIND_PATTERN.match(part["kind"])):
        errors.append((f"{path}.kind", "bad-kind", "kind is a lowercase word, letters and '-' only"))
    if "source" in part and not isinstance(part["source"], str):
        errors.append((f"{path}.source", "wrong-type", "source must be a string"))
    elif isinstance(part.get("source"), str) and not (SOURCE_URL_PATTERN.match(part["source"]) or SOURCE_PERSON_PATTERN.match(part["source"])):
        errors.append((f"{path}.source", "unreadable-source", "a source is a link a person can open, or '<person>, YYYY-MM-DD'"))
    if part.get("kind") == "evidence" and not part.get("source"):
        errors.append((path, "evidence-needs-source", "evidence needs a source a person can open"))
    if "parts" in part:
        _parts(part["parts"], f"{path}.parts", errors, in_option)
    if not in_option and ("pick" in part or "else" in part):
        _decision_shape(part, path, errors, OPTION_KEYS, True)


def check(plan):
    """Return a list of (path, rule, detail); empty means the plan is accepted."""
    errors = []
    if not _expect_object(plan, "$", errors):
        return errors
    _keys(plan, {"title", "parts"}, "$", errors)
    title = plan.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append(("$.title", "empty-text", "title must be a non-empty string"))
    if "parts" not in plan:
        errors.append(("$.parts", "missing-key", "a plan needs parts"))
    else:
        _parts(plan["parts"], "$.parts", errors)
    return errors


# -- ids -------------------------------------------------------------------

def walk(parts, prefix=""):
    """Depth-first over parts only, 1-based, dot-joined: yields (id, part)."""
    for i, part in enumerate(parts, 1):
        part_id = f"{prefix}{i}"
        yield part_id, part
        yield from walk(part.get("parts", []), part_id + ".")


def index(plan):
    return dict(walk(plan["parts"]))


def options(decision):
    """The options of a Decision or Question as pressed: pick is 1, then else in order."""
    return ([decision["pick"]] if "pick" in decision else []) + list(decision.get("else", []))


def is_decision(part):
    return "pick" in part


# -- answer ----------------------------------------------------------------

_ENTRY = re.compile(r"^- (\d+(?:\.\d+)*) (.+)$")
_PICK = re.compile(r"^pick (\d+)(?: then (\d+))?$")
_TEXT_VERBS = ("other", "struck", "comment", "edited")


def parse_answer(markdown):
    """Parse the Answer form into [(line, id, verb, argument)]; verb is pick/other/struck/comment/edited."""
    out = []
    for line_number, raw in enumerate(markdown.splitlines(), 1):
        line = raw.rstrip()
        if not line.strip() or line.startswith("# "):
            continue
        entry_match = _ENTRY.match(line)
        if not entry_match:
            raise AnswerError(line_number, "cannot parse this line; expected '- <id> <verb>'")
        part_id, rest = entry_match.groups()
        pick_match = _PICK.match(rest)
        if pick_match:
            out.append((line_number, part_id, "pick", (int(pick_match.group(1)), int(pick_match.group(2)) if pick_match.group(2) else None)))
            continue
        verb, separator, argument = rest.partition(":")
        if verb not in _TEXT_VERBS or not separator or not argument.strip():
            raise AnswerError(line_number, "cannot parse this line; expected 'pick N [then M]' or '<verb>: <text>'")
        out.append((line_number, part_id, verb, argument.strip()))
    return out


def _promote(decision, position):
    """Make option number `position` (1-based) the pick; the rest follow in their old order."""
    option_list = options(decision)
    chosen, rest = option_list[position - 1], option_list[:position - 1] + option_list[position:]
    decision["pick"] = chosen
    if rest:
        decision["else"] = rest
    else:
        decision.pop("else", None)


def apply_answer(plan, entries):
    """Return the next plan. Ids refer to the plan as given; struck parts go last."""
    new = json.loads(json.dumps(plan))
    ids = index(new)
    parent = {}
    for part_id, _ in walk(new["parts"]):
        parent[part_id] = part_id.rpartition(".")[0]
    choice = {}
    struck = set()
    for line_number, part_id, verb, argument in entries:
        part = ids.get(part_id)
        if part is None:
            raise AnswerError(line_number, f"unknown part id {part_id}")
        if verb in ("pick", "other"):
            if not is_decision(part):
                raise AnswerError(line_number, f"part {part_id} has no options")
            if part_id in choice:
                raise AnswerError(line_number, f"part {part_id} is answered twice")
            choice[part_id] = line_number
        if verb == "pick":
            picked, then = argument
            option_list = options(part)
            if not 1 <= picked <= len(option_list):
                raise AnswerError(line_number, f"pick {picked} is out of range 1-{len(option_list)} for part {part_id}")
            if then is not None:
                follow_up = option_list[picked - 1].get("then")
                if follow_up is None:
                    raise AnswerError(line_number, f"option {picked} of part {part_id} has no follow-up")
                if not 1 <= then <= len(options(follow_up)):
                    raise AnswerError(line_number, f"then {then} is out of range 1-{len(options(follow_up))} for part {part_id}")
    for line_number, part_id, verb, argument in entries:
        part = ids[part_id]
        if verb == "pick":
            picked, then = argument
            _promote(part, picked)
            if then is not None:
                _promote(part["pick"]["then"], then)
        elif verb == "other":
            old = options(part)
            part["pick"] = {"text": argument}
            part["else"] = old
        elif verb == "comment":
            part.setdefault("parts", []).append({"kind": "comment", "text": argument})
        elif verb == "edited":
            part["text"] = argument
        elif verb == "struck":
            struck.add(part_id)
    for part_id in sorted(struck, key=lambda struck_id: -len(struck_id)):
        parent_id = parent[part_id]
        siblings = new["parts"] if not parent_id else ids[parent_id]["parts"]
        for i, sibling in enumerate(siblings):
            if sibling is ids[part_id]:
                del siblings[i]
                break
    return new


_HEAD = re.compile(r"^# Answer: (.+) · plan ([0-9a-f]{8})$")


def stamp(plan):
    """Eight hex digits naming this exact plan version."""
    raw = json.dumps(plan, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


def check_head(plan, markdown):
    """Refuse an Answer made from another plan or version, since its ids would land on other Parts."""
    for line_number, raw in enumerate(markdown.splitlines(), 1):
        if not raw.strip():
            continue
        head_match = _HEAD.match(raw.rstrip())
        if not head_match:
            raise AnswerError(line_number, "the first line must be '# Answer: <title> · plan <stamp>'")
        if head_match.group(1) != plan["title"]:
            raise AnswerError(line_number, f"this Answer is for '{head_match.group(1)}', not '{plan['title']}'")
        if head_match.group(2) != stamp(plan):
            raise AnswerError(line_number, f"this Answer is for plan {head_match.group(2)}, but this version is {stamp(plan)}; build its page again")
        return
    raise AnswerError(1, "the Answer is empty")
