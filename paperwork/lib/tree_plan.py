"""Tree plan: load, check, ids, decision graph, answer parse and apply.

A plan is {"title", "parts": [Part]}; the grammar is in the tree skill's
references/grammar.md. Every function here is a calculation: no file or
network access besides load_file.
"""
import hashlib
import itertools
import json
import re

KIND_PATTERN = re.compile(r"^[a-z][a-z-]*$")
# A source a reader can open: a link off the writer's machine, or a person and the day they said it, dot-free since the page draws it.
SOURCE_URL_PATTERN = re.compile(r"^https?://(?!localhost\b|127\.0\.0\.1\b|\[::1\])[^\s/]+\.[^\s/]+(/\S*)?$")
SOURCE_PERSON_PATTERN = re.compile(r"^[^/\\:,]+, \d{4}-\d{2}-\d{2}$")
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
PLAN_KEYS = {"title", "files", "parts"}
OPTION_KEYS = {"text", "parts", "name", "requires", "excludes", "files"}
PLAIN_KEYS = {"text", "kind", "source", "parts"}
DECISION_KEYS = PLAIN_KEYS | {"pick", "else", "name", "requires"}
OTHER = 0  # the answer position of the free-text Other, which is no written option


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


def _options(decision):
    """(name, option) pairs of a Decision, pick first, in pressing order."""
    out = []
    if "pick" in decision:
        out.append(("pick", decision["pick"]))
    extra = decision.get("else")
    if isinstance(extra, list):
        out += [(f"else[{i}]", option) for i, option in enumerate(extra, 1)]
    return out


def _files(node, path, errors):
    if "files" in node and (not isinstance(node["files"], int) or isinstance(node["files"], bool) or node["files"] < 0):
        errors.append((f"{path}.files", "wrong-type", "files is a whole number, the writer's estimate"))


def _relations(node, keys, path, errors):
    for key in keys:
        if key in node and not (isinstance(node[key], list) and all(isinstance(ref, str) for ref in node[key])):
            errors.append((f"{path}.{key}", "wrong-type", f"{key} must be a list of '<decision>.<option>' names"))
    if "name" in node and not (isinstance(node["name"], str) and NAME_PATTERN.match(node["name"])):
        errors.append((f"{path}.name", "bad-name", "a name is lowercase letters, digits and '-'"))


def _option(option, path, errors):
    if not _expect_object(option, path, errors):
        return
    _keys(option, OPTION_KEYS, path, errors)
    _text(option, path, errors)
    _files(option, path, errors)
    _relations(option, ("requires", "excludes"), path, errors)
    if "parts" in option:
        _parts(option["parts"], f"{path}.parts", errors, in_option=True)


def _decision_shape(decision, path, errors):
    if "else" in decision and "pick" not in decision:
        errors.append((f"{path}.else", "else-needs-pick", "a Decision with other options needs the agent's pick"))
    if "else" in decision and not isinstance(decision["else"], list):
        errors.append((f"{path}.else", "wrong-type", "else must be a list of options"))
        return
    for name, option in _options(decision):
        _option(option, f"{path}.{name}", errors)
    _relations(decision, ("requires",), path, errors)


def _part(part, path, errors, in_option=False):
    if not _expect_object(part, path, errors):
        return
    _keys(part, DECISION_KEYS if ("pick" in part or "else" in part) and not in_option else PLAIN_KEYS, path, errors)
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
    if part.get("kind") in ("evidence", "quote") and not part.get("source"):
        errors.append((path, f"{part['kind']}-needs-source", f"{part['kind']} needs a source a person can open"))
    if "parts" in part:
        _parts(part["parts"], f"{path}.parts", errors, in_option)
    if not in_option and ("pick" in part or "else" in part):
        _decision_shape(part, path, errors)


def check(plan):
    """Return a list of (path, rule, detail); empty means the plan is accepted."""
    errors = []
    if not _expect_object(plan, "$", errors):
        return errors
    _keys(plan, PLAN_KEYS, "$", errors)
    _files(plan, "$", errors)
    title = plan.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append(("$.title", "empty-text", "title must be a non-empty string"))
    if "parts" not in plan:
        errors.append(("$.parts", "missing-key", "a plan needs parts"))
    else:
        _parts(plan["parts"], "$.parts", errors)
    # The graph reads a plan of the right shape, so its rules wait until the shape holds.
    return errors or _graph_errors(plan)


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


def holds_decision(part):
    return is_decision(part) or any(holds_decision(child) for child in part.get("parts", []))


# -- decision graph --------------------------------------------------------

def decisions(plan):
    return [(part_id, part) for part_id, part in walk(plan["parts"]) if is_decision(part)]


def _step(decision, chosen):
    """(cause, blockers): the requires that leaves the Decision not needed, else None, and each option's blocking name."""
    held = lambda ref: chosen.get(ref.partition(".")[0]) == ref.partition(".")[2]
    cause = next((ref for ref in decision.get("requires", []) if not held(ref)), None)
    return cause, [next((ref for ref in option.get("requires", []) if not held(ref)),
                        next((ref for ref in option.get("excludes", []) if held(ref)), None)) for option in options(decision)]


def evaluate(plan, answers=None):
    """{Decision id: {cause, blockers, choice, answered}} in one pass, since a relation names only an earlier Decision.

    answers maps a Decision id to an option's position, or OTHER. choice is the position in force, or None when the
    Decision is not needed: a blocked answer falls back to the pick, then to the first open option.
    """
    answers = answers or {}
    chosen, state = {}, {}
    for part_id, decision in decisions(plan):
        cause, blockers = _step(decision, chosen)
        option_list = options(decision)
        openings = [position for position, blocker in enumerate(blockers, 1) if blocker is None]
        answer = answers.get(part_id)
        answered = cause is None and (answer == OTHER or answer in openings)
        choice = None if cause else answer if answered else next(iter(openings), None)
        state[part_id] = {"cause": cause, "blockers": blockers, "choice": choice, "answered": answered}
        chosen[decision.get("name")] = option_list[choice - 1].get("name") if choice else None
    return state


def settled(entry):
    """Relations left one of several options and no answer, so the page folds the Decision; a plan's lone option still asks."""
    open_count = sum(blocker is None for blocker in entry["blockers"])
    return entry["cause"] is None and not entry["answered"] and open_count == 1 and len(entry["blockers"]) > 1


def waiting(state):
    return [part_id for part_id, entry in state.items() if entry["cause"] is None and not entry["answered"] and not settled(entry)]


def _flat(parts):
    for part in parts:
        yield part
        yield from _flat(part.get("parts", []))


def _in_force(parts, state, struck, prefix=""):
    """Each Part these answers keep, with the option in force of each needed Decision and that option's Parts."""
    for i, part in enumerate(parts, 1):
        part_id = f"{prefix}{i}"
        entry = state.get(part_id)
        if part_id in struck or (entry and entry["cause"]):
            continue
        yield part
        if entry and entry["choice"]:
            option = options(part)[entry["choice"] - 1]
            yield option
            yield from _flat(option.get("parts", []))
        yield from _in_force(part.get("parts", []), state, struck, part_id + ".")


def _inside(part_id, struck):
    return any(part_id == struck_id or part_id.startswith(struck_id + ".") for struck_id in struck)


def summary(plan, answers=None, struck=()):
    """The numbers on the page's top: {files, left, risks}; files is None when the plan estimates none."""
    state = evaluate(plan, answers)
    kept = list(_in_force(plan["parts"], state, struck))
    estimates = [plan["files"]] if "files" in plan else []
    estimates += [node["files"] for node in kept if "files" in node]
    return {"files": sum(estimates) if estimates else None, "left": len([part_id for part_id in waiting(state) if not _inside(part_id, struck)]),
            "risks": sum(node.get("kind") == "risk" for node in kept)}


def presses(plan):
    """Every (Decision id, option position) a person could press."""
    return [(part_id, position) for part_id, part in decisions(plan) for position in range(1, len(options(part)) + 1)]


def reachable(plan, part_id, position):
    """Answers of the named Decisions that open this option, or None when none do."""
    named = [(other_id, part) for other_id, part in decisions(plan) if "name" in part and other_id != part_id]
    for chosen in itertools.product(*[[(other_id, n + 1) for n in range(len(options(part)))] for other_id, part in named]):
        state = evaluate(plan, dict(chosen))
        if state[part_id]["cause"] is None and state[part_id]["blockers"][position - 1] is None:
            return {other_id: n for other_id, n in chosen if state[other_id]["answered"]}
    return None


def changes(plan, answers, part_id, position):
    """The other Decisions this press would change, the page's effect marks."""
    before, after = evaluate(plan, answers), evaluate(plan, {**answers, part_id: position})
    fields = ("cause", "blockers", "choice")
    return {other for other in before if other != part_id and any(before[other][field] != after[other][field] for field in fields)}


def _dead_end(graph, chosen):
    """The id of the first needed Decision some answers leave with no open option, or None."""
    for i, (part_id, decision) in enumerate(graph):
        cause, blockers = _step(decision, chosen)
        name = decision.get("name")
        if cause:
            chosen = {**chosen, name: None}
            continue
        openings = [option for option, blocker in zip(options(decision), blockers) if blocker is None]
        if not openings:
            return part_id
        if name:
            # Only a named Decision can change a later one, so only it branches; an Other answer is one more branch, satisfying no relation.
            branches = [option.get("name") for option in openings] + [None]
            return next(filter(None, (_dead_end(graph[i + 1:], {**chosen, name: branch}) for branch in branches)), None)
    return None


def _graph_errors(plan):
    errors, earlier = [], {}
    graph = decisions(plan)
    every = set()
    for part_id, decision in graph:
        if any(part_id.startswith(other + ".") for other, _ in graph):
            errors.append((f"part {part_id}", "nested-decision", "a Decision's parts hold no Decision; write a later Decision with requires"))
        names = [option["name"] for option in options(decision) if "name" in option]
        if decision.get("name") in every or len(names) != len(set(names)):
            errors.append((f"part {part_id}", "duplicate-name", "a Decision's name, or an option's within it, is written twice"))
        every |= {decision["name"]} if "name" in decision else set()
    for part_id, decision in graph:
        refs = list(decision.get("requires", []))
        for option in options(decision):
            refs += option.get("requires", []) + option.get("excludes", [])
        for ref in refs:
            target, _, option_name = ref.partition(".")
            if target in earlier:
                if option_name not in earlier[target]:
                    errors.append((f"part {part_id}", "unknown-ref", f"'{ref}' names no option of '{target}'"))
            elif target in every:
                errors.append((f"part {part_id}", "forward-ref", f"'{ref}' names a Decision not before this one"))
            else:
                errors.append((f"part {part_id}", "unknown-ref", f"'{ref}' names no Decision"))
        if "name" in decision:
            earlier[decision["name"]] = {option.get("name") for option in options(decision)}
    if errors:
        return errors
    for part_id, entry in evaluate(plan).items():
        if entry["cause"] is None and entry["blockers"][0]:
            errors.append((f"part {part_id}", "default-blocked", f"the pick is blocked by '{entry['blockers'][0]}' when every pick stands"))
    dead = _dead_end(graph, {})
    if dead:
        errors.append((f"part {dead}", "dead-end", "some answers leave this Decision with no open option"))
    return errors or _unused_names(graph)


def _references(graph):
    used = set()
    for _, decision in graph:
        used.update(decision.get("requires", []))
        for option in options(decision):
            used.update(option.get("requires", []) + option.get("excludes", []))
    return used


def _unused_names(graph):
    used = _references(graph)
    errors = []
    for part_id, decision in graph:
        if "name" in decision and not any(ref.startswith(decision["name"] + ".") for ref in used):
            errors.append((f"part {part_id}", "unused-name", f"no relation names '{decision['name']}'"))
        errors += [(f"part {part_id}", "unused-name", f"no relation names option '{option['name']}'")
                   for option in options(decision) if "name" in option and f"{decision.get('name')}.{option['name']}" not in used]
    return errors


# -- answer ----------------------------------------------------------------

_ENTRY = re.compile(r"^- (\d+(?:\.\d+)*) (.+)$")
_PICK = re.compile(r"^pick (\d+)$")
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
            out.append((line_number, part_id, "pick", int(pick_match.group(1))))
            continue
        verb, separator, argument = rest.partition(":")
        if verb not in _TEXT_VERBS or not separator or not argument.strip():
            raise AnswerError(line_number, "cannot parse this line; expected 'pick N' or '<verb>: <text>'")
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


def _subtree(part):
    """Every Decision name under a Part, its own included."""
    found = {part["name"]} if "name" in part else set()
    for child in part.get("parts", []):
        found |= _subtree(child)
    return found


def _strike_blocker(plan, part_id):
    """The Decision outside a Part whose relation names a Decision inside it, or None."""
    ids = index(plan)
    inside = _subtree(ids[part_id])
    for other_id, decision in decisions(plan):
        if other_id == part_id or other_id.startswith(part_id + "."):
            continue
        refs = list(decision.get("requires", []))
        for option in options(decision):
            refs += option.get("requires", []) + option.get("excludes", [])
        if any(ref.partition(".")[0] in inside for ref in refs):
            return other_id
    return None


def _answers_of(plan, entries):
    """{Decision id: position} of the Answer, each line checked against the plan and the other lines."""
    ids = index(plan)
    answers = {}
    for line_number, part_id, verb, argument in entries:
        part = ids.get(part_id)
        if part is None:
            raise AnswerError(line_number, f"unknown part id {part_id}")
        if verb == "struck" and _strike_blocker(plan, part_id):
            raise AnswerError(line_number, f"part {_strike_blocker(plan, part_id)} depends on part {part_id}, so it cannot be struck")
        if verb in ("pick", "other"):
            if not is_decision(part):
                raise AnswerError(line_number, f"part {part_id} has no options")
            if part_id in answers:
                raise AnswerError(line_number, f"part {part_id} is answered twice")
            answers[part_id] = OTHER if verb == "other" else argument
        if verb == "pick" and not 1 <= argument <= len(options(part)):
            raise AnswerError(line_number, f"pick {argument} is out of range 1-{len(options(part))} for part {part_id}")
    state = evaluate(plan, answers)
    for line_number, part_id, verb, argument in entries:
        if verb == "pick" and state[part_id]["cause"]:
            raise AnswerError(line_number, f"part {part_id} is not needed: it requires {state[part_id]['cause']}")
        if verb == "pick" and state[part_id]["blockers"][argument - 1]:
            raise AnswerError(line_number, f"pick {argument} of part {part_id} is blocked by {state[part_id]['blockers'][argument - 1]}")
    return answers, state


def _drop_unused_names(plan):
    """A strike can remove the last relation that names something, and the checker refuses a name no relation uses."""
    graph = decisions(plan)
    used = _references(graph)
    for _, decision in graph:
        for option in options(decision):
            if f"{decision.get('name')}.{option.get('name')}" not in used:
                option.pop("name", None)
        if not any(ref.startswith(f"{decision.get('name')}.") for ref in used):
            decision.pop("name", None)


def apply_answer(plan, entries):
    """Return the next plan. Ids refer to the plan as given; struck parts go last."""
    answers, state = _answers_of(plan, entries)
    new = json.loads(json.dumps(plan))
    ids = index(new)
    parent = {part_id: part_id.rpartition(".")[0] for part_id in ids}
    struck = set()
    for _, part_id, verb, argument in entries:
        part = ids[part_id]
        if verb == "other":
            old = options(part)
            part["pick"] = {"text": argument}
            part["else"] = old
        elif verb == "comment":
            part.setdefault("parts", []).append({"kind": "comment", "text": argument})
        elif verb == "edited":
            part["text"] = argument
        elif verb == "struck":
            struck.add(part_id)
    # A pick or a settled Decision holds its option as the pick, so the next plan's default path stands.
    for part_id, entry in state.items():
        if entry["choice"]:
            _promote(ids[part_id], entry["choice"])
    for part_id in sorted(struck, key=lambda struck_id: -len(struck_id)):
        parent_id = parent[part_id]
        siblings = new["parts"] if not parent_id else ids[parent_id]["parts"]
        for i, sibling in enumerate(siblings):
            if sibling is ids[part_id]:
                del siblings[i]
                break
    _drop_unused_names(new)
    return new


def unanswered(plan, entries):
    """The (id, text) of each Decision the Answer left open, since a silence is not a yes."""
    answers, state = _answers_of(plan, entries)
    ids = index(plan)
    gone = [part_id for _, part_id, verb, _ in entries if verb == "struck"]
    return [(part_id, ids[part_id]["text"]) for part_id in waiting(state) if not _inside(part_id, gone)]


_HEAD = re.compile(r"^# Answer: (.+) · plan ([0-9a-f]{8})$")


def stamp(plan):
    """Eight hex digits naming this exact plan version."""
    raw = json.dumps(plan, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


def answer_head(plan):
    """The whole of an Answer that touched nothing."""
    return f"# Answer: {plan['title']} · plan {stamp(plan)}\n"


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
