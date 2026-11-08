"""How a `[check]` criterion reads: the command it runs, the output it expects, the one value it quotes for the base.
run-criteria.py runs a check by it and check-criteria.py refuses a check it cannot read, so both share this one parse."""
import re

import issue_state

# the number of the task that added the Goal path check, so every Goal written before it keeps its old rules
GOAL_CUT_OFF = 1305
PATH_LINE = re.compile(r"^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?Path(?:\*\*)?:(?:\*\*)?[ \t]*(.*)$", re.M | re.I)
# the blanks of the form FIX prints, which a writer who copies it unfilled has not answered
BLANK = re.compile(r"<(?:caller|step before|step after|who sees the result)>")
# the relations Scope the path names between a changed part and its flow, each written `label: who or what`
RELATION = re.compile(r"^\s*(?:caller|before|after|meets)\s*:\s*(\S.*?)\s*$", re.I)
# a value that opens by saying there is no such party, not a party, unless a party follows `but` or `except`
NOBODY = re.compile(r"^(?:none|no one|nobody|nothing|no\s|n/a|unknown|tbd|-)(?!.*\b(?:but|except)\b)", re.I)

GOAL_FIX = {
    "no path in the Goal": "add to the Goal one line, `Path: caller: <caller>; before: <step before>; after: <step after>; meets: <who sees the result>`, "
                           "naming the flow of the changed part, as protocol.md's **Scope the path** says: its callers, the steps before and after it, "
                           "and whoever meets its result, all on that one line; a Goal that names only the changed part misses what breaks when it changes",
    "path names no flow": "as protocol.md's **Scope the path** says, write the `Path:` line as `label: name` items split by `;`, the only form that counts: at least one of "
                          "`caller:`, `before:`, `after:` or `meets:` followed by the party it names, never `none`, empty, or a `<...>` blank of the form left in the line; "
                          "a line that names only the changed part, or says nothing is affected, gives no flow",
}


def goal_defects(goal):
    """The defects of a Goal's `Path:` line: absent, or present and naming no flow of the changed part."""
    lines = [text.strip() for text in PATH_LINE.findall(goal)]
    if not any(lines):
        return ["no path in the Goal"]
    items = [RELATION.match(item) for text in lines for item in text.split(";")]
    named = [item.group(1) for item in items if item]
    return [] if named and not any(BLANK.search(text) for text in lines) and any(not NOBODY.match(value) for value in named) else ["path names no flow"]


def goal_refusals(body, number=None, old=""):
    """The sentences, each ending in its fix, that refuse BODY's `## Goal` for naming no flow; none for a body with no Goal, a task numbered below the cut-off,
    or a defect OLD already held, so an edit to some other part of a body is never blocked."""
    goal = issue_state.sections(body).get("goal")
    if goal is None or number is not None and number < GOAL_CUT_OFF:
        return []
    before = issue_state.sections(old).get("goal")
    held = goal_defects(before) if before is not None else []
    return [f"the `## Goal` {name}: {GOAL_FIX[name]}" for name in goal_defects(goal) if name not in held]


PLACEHOLDER = re.compile(r"<[A-Za-z][\w .-]*>")
# a code span, or an empty one, which SPAN skips
# an empty one only where the clause goes on to its end, so a padded `` echo `x` `` stays one span
SPANS = re.compile(r"(?<!`)``(?=\s*(?:$|[;.,)]|\bon\b|\bwhen\b))|" + issue_state.SPAN.pattern)
# a remark in parentheses is hidden too, since it may hold a `,` or `;`
HIDDEN = re.compile(SPANS.pattern + r"|\([^()]*\)")
NOTE = re.compile(r"\s*\0(\d+)\0$")


def hide(text):
    """(text with each code span a token no clause split matches inside, the spans), so a `when` or `;` in a quoted value never splits."""
    kept = []

    def stash(match):
        kept.append(match.group())
        return f"\0{len(kept) - 1}\0"
    return HIDDEN.sub(stash, text), kept


def show(text, kept):
    return re.sub(r"\0(\d+)\0", lambda match: kept[int(match.group(1))], text)


def is_remark(text):
    """A parenthesis that only explains; one with a code span or an `or` may add a second accepted value, so it stays."""
    return text.lstrip().startswith("(") and "`" not in text and not re.search(r"\bor\b", text)


def clause_of(rest):
    """(first clause of text after `prints` or `on base` with a remark in parentheses cut, the hidden text after it, the hidden spans)."""
    hidden, kept = hide(rest)
    clause, *parts = re.split(r"([;.](?:\s|$)|,\s+(?!\0)|\bwhen\b|\bon (?:base|main)\b)", hidden)
    clause = clause.strip()
    while (note := NOTE.search(clause)) and is_remark(kept[int(note.group(1))]):
        clause = clause[:note.start()]
    return show(clause, kept).strip(), "".join(parts), kept


def expectation(detail):
    """(command, test) of a `[check]`'s details, test ('prints', text), ('more', n), ('exits', n) or (None, why) when undecidable."""
    spans = list(SPANS.finditer(detail))
    if not spans or spans[0].group(2) is None:
        return None, (None, "no command")
    command, after = spans[0].group(2), detail[spans[0].end():]
    if detail[:spans[0].start()].strip():
        return command, (None, "words before the command")
    verb = re.search(r"\b(prints|exits)\b", after)
    if not verb or any(other.start() < spans[0].end() + verb.start() for other in spans[1:]):
        return command, (None, "two commands" if verb else "no prints or exits")
    if PLACEHOLDER.search(command) or "..." in command or "…" in command:
        return command, (None, "placeholder in the command")
    rest = after[verb.end():]
    # the expected text runs to the clause's end, so a second value such as `a` then `b` or `a`, `b` reads as undecidable
    clause, after_clause, kept = clause_of(rest)
    # a further command before the base's output is a second condition, which this value alone would pass; a `when` explains
    tail = re.split(r"\bon (?:base|main)\b", after_clause)[0]
    tail = show(re.sub(r"\bwhen\b.*?(?:[;.](?:\s|$)|$)", "", tail, flags=re.S), kept)
    if re.match(r"[,;]\s*and\b", tail) or any(re.search(r"\s", match.group(2)) for match in issue_state.SPAN.finditer(tail)):
        return command, (None, "more than one condition")
    if verb.group(1) == "exits":
        code = re.fullmatch(r"`?(\d+)`?", clause)
        return command, ("exits", int(code.group(1))) if code else (None, "expected status not one value")
    found = list(issue_state.SPAN.finditer(clause))
    span = found[0] if len(found) == 1 and found[0].span() == (0, len(clause)) else None
    more = re.fullmatch(r"`?(\d+)`? or more", clause)
    if clause == "nothing":
        return command, ("prints", "")
    if more:
        return command, ("more", int(more.group(1)))
    if clause == "``":
        return command, ("prints", "")
    if span and not PLACEHOLDER.search(span.group(2)):
        return command, ("prints", span.group(2))
    if re.fullmatch(r"[\w-]+", clause):
        return command, ("prints", clause)
    return command, (None, "expected output not one value")


def base_quote(detail):
    """The one value quoted after `on base` in a `[check]`'s details, or None when it is not one value."""
    # tasks filed before the base was named quote `on main`
    hidden, kept = hide(detail)
    _, found, rest = (re.split(r"\b(on (?:base|main))\b", hidden, maxsplit=1) + ["", ""])[:3]
    clause = clause_of(show(rest, kept))[0]
    clause = re.sub(r"^(?:it\s+)?prints\s+", "", clause)
    spans = list(issue_state.SPAN.finditer(clause))
    if len(spans) == 1 and spans[0].span() == (0, len(clause)):
        return spans[0].group(2)
    if clause in ("nothing", "``"):
        return ""
    return clause if found and re.fullmatch(r"[\w-]+", clause) else None


def unreadable(detail):
    """Why run-criteria.py cannot decide a `[check]`'s details at the head or on the base, or None when it can."""
    _, test = expectation(detail)
    if test[0] is None:
        return test[1]
    if test[0] == "prints" and base_quote(detail) is None:
        return "no one value after `on base`"
    return None


def verdict(test, status, out):
    """`pass`, `fail`, or `unclear` for a `prints` text found only among other lines, which a judge reads, of a run's STATUS and OUT against TEST."""
    kind, want = test
    if status is None:
        return "fail"
    if kind == "exits":
        return "pass" if status == want else "fail"
    if kind == "more":
        first = out.split(maxsplit=1)[:1]
        return "pass" if first and first[0].isdigit() and int(first[0]) >= want else "fail"
    if out == want:
        return "pass"
    return "unclear" if want and re.search(rf"(?<!\w){re.escape(want)}(?!\w)", out) else "fail"


# outside quotes only these may precede the first pipe; anything else (`;`, `&`, `{`, `(`, `#`, a backslash, ...) might hide a pipe or a stage
SAFE = re.compile(r"[\w \t./=:,+@%~<-]|\$\w|\$(?=[\"'])")
# a compound command owns the pipe that follows its first word, so the pipe is not a stage boundary
COMPOUND = {"if", "while", "until", "for", "case", "select", "time", "function", "coproc"}


def after_first_pipe(command):
    """The command without its first pipe stage, split at the first `|` outside quotes, or None when the split is not certain:
    no pipe, or before it a character outside SAFE, or in double quotes a `$(`, `${`, backtick or backslash, which
    could hide a pipe or drop part of the first stage."""
    if command.split(None, 1)[:1] and command.split(None, 1)[0] in COMPOUND:
        return None
    quote, i = None, 0
    while i < len(command):
        char = command[i]
        if char == "\\":
            return None
        if quote:
            # a substitution inside double quotes can hold quotes of its own, which end this quote early
            if quote == '"' and (char == "`" or command[i:i + 2] in ("$(", "${")):
                return None
            quote = None if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char == "|" and command[i:i + 2] != "||":
            return command[i + 1:]
        elif not (match := SAFE.match(command, i)):
            return None
        else:
            i = match.end() - 1
        i += 1
    return None


# a program `claude` run with `-p` or `--print` starts a live session
SESSION = re.compile(r"(?<![\w\"'.-])claude(?![\w-])[^|;&\n]*?\s(?:-p|--print)\b")
WATCHES = re.compile(r"\bwatches:\s*([^;`]*?)(?=\s+on (?:base|main)\b|;|\.(?:\s|$)|$)")


def starts_session(command):
    return bool(SESSION.search(command))


def watched(detail):
    """The paths a `[check]` says its live run depends on, after `watches:`, as the files and folders that decide whether a saved transcript still holds."""
    found = WATCHES.search(re.sub(SPANS, "", detail))
    return found.group(1).split() if found else []


def live_stage(detail):
    """(first stage, the stages after it) of a `[check]` whose first pipe stage starts a live session and which names what it `watches:`, else None;
    the first stage's output is the transcript the later stages judge, so a fix to them replays it."""
    command, _ = expectation(detail)
    rest = after_first_pipe(command) if command else None
    if rest is None or not watched(detail):
        return None
    first = command[:len(command) - len(rest) - 1]
    return (first.strip(), rest) if starts_session(first) else None
