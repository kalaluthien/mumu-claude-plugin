"""How a `[check]` criterion reads: the command it runs, the output it expects, the one value it quotes for the base.
run-criteria.py runs a check by it and lint-criteria.py refuses a check it cannot read, so both share this one parse."""
import re

import issue_state

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

    def stash(m):
        kept.append(m.group())
        return f"\0{len(kept) - 1}\0"
    return HIDDEN.sub(stash, text), kept


def show(text, kept):
    return re.sub(r"\0(\d+)\0", lambda m: kept[int(m.group(1))], text)


def is_remark(text):
    """A parenthesis that only explains; one with a code span or an `or` may add a second accepted value, so it stays."""
    return text.lstrip().startswith("(") and "`" not in text and not re.search(r"\bor\b", text)


def clause_of(rest):
    """(first clause of text after `prints` or `on base` with a remark in parentheses cut, the hidden text after it, the hidden spans)."""
    hidden, kept = hide(rest)
    clause, *parts = re.split(r"([;.](?:\s|$)|,\s+(?!\0)|\bwhen\b|\bon (?:base|main)\b)", hidden)
    clause = clause.strip()
    while (m := NOTE.search(clause)) and is_remark(kept[int(m.group(1))]):
        clause = clause[:m.start()]
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
    if not verb or any(s.start() < spans[0].end() + verb.start() for s in spans[1:]):
        return command, (None, "two commands" if verb else "no prints or exits")
    if PLACEHOLDER.search(command) or "..." in command or "…" in command:
        return command, (None, "placeholder in the command")
    rest = after[verb.end():]
    # the expected text runs to the clause's end, so a second value such as `a` then `b` or `a`, `b` reads as undecidable
    clause, after_clause, kept = clause_of(rest)
    # a further command before the base's output is a second condition, which this value alone would pass; a `when` explains
    tail = re.split(r"\bon (?:base|main)\b", after_clause)[0]
    tail = show(re.sub(r"\bwhen\b.*?(?:[;.](?:\s|$)|$)", "", tail, flags=re.S), kept)
    if re.match(r"[,;]\s*and\b", tail) or any(re.search(r"\s", m.group(2)) for m in issue_state.SPAN.finditer(tail)):
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
