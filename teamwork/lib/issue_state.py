"""An issue's latest state, composed from its body and the fields of its comments, which board-record-schema.json names."""
import difflib
import json
import pathlib
import re

import legacy_records

SKILL = pathlib.Path(__file__).resolve().parents[1] / "skills" / "kick-off"
GRAMMAR = SKILL / "references" / "issue-grammar.md"
SCHEMA = json.loads((SKILL / "assets" / "board-record-schema.json").read_text())
# the word a comment's first line opens with: a question, a decision or an event, anything else
ASK, ANSWER, INFORM = "BLOCKED", "DECIDED", "REPORTED"
KEYWORDS = (ASK, ANSWER, INFORM)
SECTIONS = {"Goal": "goal", "Definition of done": "done"}
ITEM = re.compile(r"^(?:\d+\.|[-*])\s+(.*)$", re.M)
# a criterion `[check] **<name>**: <details>`, after a task-list box when one marks it met; one filed before names were asked for is its own name
CRITERION = re.compile(r"^(?:\[([ xX])\]\s+)?(?:\[(\w+)\]\s+)?(?:\*\*(.+?)\*\*:?\s*)?(.*)$")
# a run of n backticks closes only on a run of exactly n, so a ``…`` span may hold single backticks
SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
EXACT_KEYWORD = re.compile(r"^\s*(" + "|".join(KEYWORDS) + r"):")
# the one wait the pane highlights, since only the owner's answer is the owner's to give
OWNER_WAIT = "waits on the owner"
DIFF = re.compile(r"^(`{3,})diff\n(.*?)^\1$", re.M | re.S)
# a data fence at a line's start, which a text may not hold, since every datum is an option
FENCE = re.compile(r"^```(teamwork|decision)[ \t]*$", re.M)
FENCE_OPTIONS = {"teamwork": "`hold <issue> <name>...`, `depend <issue> <n>...`, `comment --asks owner` or `decide --live-runs <n>`",
                 "decision": "`decide [--by <who>] [--one-way] [--supersedes <url>] [--answers <url>]`, whose sentence is the text's first line"}
# the keyword each posting verb opens its text with; a comment asks or informs
VERB_KEYWORDS = {"comment": (ASK, INFORM), "decide": (ANSWER,), "resolve": (INFORM,)}
# the Plain words caps on a title, a summary line and a decision: the live board's plain summary lines and decisions ran to 20 words, its dense
# ones from 23, and a second `,` `;` or `:` joined a further idea in every dense line a fresh reader marked
TITLE_CHARS = 40
SENTENCE_WORDS = 20
SENTENCE_MIN_WORDS = 5  # a subject, a verb and what it acts on, with an article or a modifier
SENTENCE_BREAKS = 1
TASK_NUMBER = re.compile(r"#\d+\b")
BREAK = re.compile(r"[,;:](?=\s)")
TYPES = {"object": dict, "array": list, "string": str, "integer": int}


def keyword(text):
    """The keyword a comment opens with, or None when its first line opens with none."""
    found = EXACT_KEYWORD.match(text or "")
    return found and found.group(1)


def first_line(text):
    """A comment's first line of text without its keyword, the line after a keyword that stands alone."""
    return next((line.strip() for line in re.sub(r"^\s*[A-Z]+:", "", (text or "").strip()).splitlines() if line.strip()), "")


class Refused(LookupError):
    """A record the schema refuses, so nothing was written."""


def invalid(value, schema=SCHEMA, name="the record"):
    """Why VALUE breaks SCHEMA, read for its type, enum, pattern, minimum, items, properties, required and additionalProperties; None when it keeps it."""
    kind = schema.get("type")
    wrong = "enum" in schema and value not in schema["enum"] or kind and (not isinstance(value, TYPES[kind]) or isinstance(value, bool)) \
        or "pattern" in schema and not re.search(schema["pattern"], value) or "minimum" in schema and value < schema["minimum"]
    if wrong:
        return f"{name} is {value!r}, which does not fit: {schema.get('description') or schema.get('title')}"
    if kind == "array":
        return next(filter(None, (invalid(item, {"description": schema.get("description"), **schema["items"]}, name) for item in value)), None)
    if kind == "object":
        known = schema["properties"]
        if stray := [key for key in value if key not in known] if schema.get("additionalProperties") is False else []:
            return f"{name} holds `{stray[0]}`, which is none of: {' '.join(known)}"
        if missing := [key for key in schema.get("required", ()) if key not in value]:
            return f"{name} lacks `{missing[0]}`"
        return next(filter(None, (invalid(value[key], known[key], f"`{key}`") for key in value)), None)
    return None


def defects(kind, text, old=""):
    """The defects of TEXT written by KIND (title, comment, decide, resolve, file, edit-body, edit-line), each a plain sentence ending in its fix; none
    when it reads as meant. A defect OLD already held does not count, so an edit that fixes a body is never blocked."""
    found = _defects(kind, text or "")
    held = [signature for signature, _ in _defects(kind, old)] if old else []
    return [sentence for signature, sentence in found if signature not in held]


def _defects(kind, text):
    """[(signature, sentence)] of TEXT, the signature free of the line number so an edit that moves a line keeps it."""
    if kind == "title":
        return plain("title", text) if text.strip() else [("empty", "the title is empty; write what the task does in a few words")]
    if kind == "edit-line":
        one = re.fullmatch(ANSWER + r":[^\n]*\S[^\n]*", text.rstrip("\n"))
        return [] if one else [("edit-line", f"the keyword line is not one line that opens `{ANSWER}:` and says what changed; write `{ANSWER}: <what changed and why>` on one line")]
    found = [(f"fence {name}", f"a line opens a `{name}` fence, and a text carries no data; drop the fence and pass its values as options: {FENCE_OPTIONS[name]}")
             for name in dict.fromkeys(FENCE.findall(text))]
    if kind in VERB_KEYWORDS:
        first, own = EXACT_KEYWORD.match(text), VERB_KEYWORDS[kind]
        # `decide` and `resolve` put their keyword first themselves, so only a text that opens with another verb's is refused
        if first.group(1) not in own if first else kind == "comment":
            found.append(("keyword", f"the first line does not open with {' or '.join(f'`{word}:`' for word in own)}; a comment opens `{ASK}:` to ask a question "
                          f"with its options or `{INFORM}:` to say anything else, and `decide` posts a `{ANSWER}:`"))
    if kind in ("file", "edit-body"):
        found += heading_defects(text) + body_defects(text)
    if kind in (*VERB_KEYWORDS, "file", "edit-body") and not re.sub(r"\A(\s*[A-Z]+:)*", "", text).strip():
        # a shell write that failed leaves an empty file, which would post as a bare keyword
        found.append(("empty", "the text is empty or holds its keyword alone; write what it asks, decides or reports, and check the file was written"))
    elif kind == "decide":
        found += plain("decision", first_line(text))
    return found


def heading_defects(text):
    """[(signature, sentence)] of a body's section headings: one misspelt, or one that appears twice."""
    found, headings, names = [], {}, {name.lower(): name for name in SECTIONS}
    for number, line in enumerate(text.split("\n"), 1):
        heading = re.match(r"^#{1,6}\s*([A-Za-z].*?)\s*$", line)
        close = heading and difflib.get_close_matches(re.sub(r"\s*(\(.*\)|:)$", "", heading.group(1)).lower(), list(names), 1, 0.85)
        if close:
            section = names[close[0]]
            headings[section] = headings.get(section, 0) + (line == f"## {section}")
            if line != f"## {section}":
                found.append((f"heading {line}", f"line {number}, `{line}`, misspells a section heading; write exactly `## {section}`"))
    return found + [(f"repeated {section}", f"`## {section}` appears {count} times; keep one and merge the rest into it") for section, count in headings.items() if count > 1]


def body_defects(text):
    """[(signature, sentence)] of a body's summary line and the names of its criteria."""
    found = plain("summary line", summary_line(text))
    for item in ITEM.findall(sections(text).get("done", "")):
        name = CRITERION.match(item).group(3)
        found += plain("criterion name", name) + sentence("criterion name", name) if name else []
    return found


def summary_line(body):
    """A body's summary line, its first paragraph's lines joined; none when the body opens with a heading."""
    first = (body or "").replace("\r\n", "\n").strip().split("\n\n")[0]
    return "" if first.startswith("#") else " ".join(first.split())


def plain(what, text):
    """[(signature, sentence)] of the Plain words caps TEXT, a title, summary line or decision, breaks; the signature holds the text, so
    an edit that leaves an older line as it was is never blocked by it."""
    raw = text or ""
    text, found = " ".join(raw.split()), []
    named = TASK_NUMBER.findall(text)
    if named:
        found.append(f"the {what} names {' '.join(named)}; say what that task is in words and put its number in the body")
    # a title is stored as written, so its cap counts every character written
    if what == "title" and len(raw) > TITLE_CHARS:
        found.append(f"the title has {len(raw)} characters; cut it to {TITLE_CHARS}")
    if what != "title" and len(text.split()) > SENTENCE_WORDS:
        found.append(f"the {what} has {len(text.split())} words; cut it to {SENTENCE_WORDS} words with one idea, and move the detail to the body")
    if what != "title" and len(BREAK.findall(text)) > SENTENCE_BREAKS:
        found.append(f"the {what} joins ideas by {len(BREAK.findall(text))} of `,` `;` `:`; keep one idea, with at most {SENTENCE_BREAKS}")
    return [(f"plain {what} {text}", f"{sentence}, as Plain words says") for sentence in found]


def sentence(what, text):
    """[(signature, sentence)] when TEXT is too short to be a complete sentence, which holds a subject, a verb and what it acts on; the signature holds the text, as in plain."""
    words = len(text.split())
    if words >= SENTENCE_MIN_WORDS:
        return []
    return [(f"sentence {what} {text}", f"the {what} `{text}` has {words} word{'' if words == 1 else 's'}, a label and no complete sentence; write what holds, with a subject, a verb and what it acts on, in at least {SENTENCE_MIN_WORDS} words, as Complete sentence says")]


def sections(text):
    """{role: text} of the sections it carries, by the heading the grammar names."""
    found = re.findall(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", text or "", re.M | re.S)
    return {SECTIONS[heading.strip()]: body for heading, body in found if heading.strip() in SECTIONS}


def trusted(item):
    """Whether an issue's or comment's author may write records, as the board adapter marked it, since each board says who may."""
    return item.get("trusted") is True


# C0 and DEL, which a terminal or a prompt reads as a command or a line break
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
TITLE_CUT = 60


def title(item):
    """Its title as a prompt or the pane may show it: a trusted author's as written, else quoted, its control characters
    removed and cut to TITLE_CUT characters then an ellipsis, so it reads as data, never as an instruction."""
    if trusted(item):
        return item["title"]
    text = CONTROL.sub("", item["title"] or "")
    return '"' + (text[:TITLE_CUT] + "…" if len(text) > TITLE_CUT else text) + '"'


def fields(comment):
    """A comment's fields, as board-record-schema.json names them: those `use-board.py` stored, else the ones an older text holds."""
    stored = comment.get("fields")
    return stored if stored is not None else legacy_records.fields(comment.get("body"))


def records(issue):
    """The body, then each comment, as (keyword, fields, comment), oldest first; the body has no keyword and only an older one holds fields, and an
    untrusted author's text records nothing."""
    return [(None, legacy_records.fields(issue.get("body")) if trusted(issue) else {}, None)] + [(keyword(comment["body"]), fields(comment), comment) for comment in issue.get("comments", []) if trusted(comment)]


def event(found):
    """Whether a `DECIDED:` with the fields FOUND is an event, which binds and answers nothing: it holds no decision."""
    return "decision" not in found and not found.get("untyped")


def role(decider):
    """`owner`; `manager` for a session named `<project>-manager`, or `<project>-manager-next`, the name Succession gives; else `worker`."""
    return "owner" if decider == "owner" else "manager" if decider == "manager" or decider.removesuffix("-next").endswith("-manager") else "worker"


def place(url):
    """URL's path after the board ref, since the same comment is named by another git dir when the board is read from another checkout path; any other url whole."""
    return url.partition("refs/teamwork-blackboard/")[2] or url


def questions(issue):
    """Its questions, oldest first, each {'ask': the `BLOCKED:` comment, 'fields': its fields, 'answer': the comment that settles it or None}:
    a later decision settles the question whose url it names and each earlier open ask with the same first line, since an ask
    posted again is one question; one that names none settles each open question its decider may answer: the owner any, a manager any
    not asked of the owner, a worker none, and a `DECIDED:` from before decisions were typed any."""
    found = []
    for word, held, comment in records(issue)[1:]:
        if word == ASK:
            found.append({"ask": comment, "fields": held, "answer": None})
        elif word == ANSWER and not event(held):
            named, decider = held.get("answers", ""), role(held.get("by", ""))
            said = {first_line(question["ask"]["body"]) for question in found if place(question["ask"]["url"]) == place(named)}
            older = (comment.get("createdAt") or "") < legacy_records.TYPED_SINCE
            for question in found:
                general = older or decider == "owner" or decider == "manager" and question["fields"].get("asks") != "owner"
                if question["answer"] is None and (general if not named else place(question["ask"]["url"]) == place(named) or first_line(question["ask"]["body"]) in said):
                    question["answer"] = comment
    return found


def open_questions(issue):
    return [question for question in questions(issue) if question["answer"] is None]


def holder_values(issue):
    """Each holders value set, oldest first, as a list of names."""
    return [held["holders"] for _, held, _ in records(issue) if "holders" in held]


def live_runs(issue):
    """The latest `live_runs` count a trusted record set, or None when none did."""
    return next((held["live_runs"] for _, held, _ in reversed(records(issue)) if "live_runs" in held), None)


def compose(issue, blockers=()):
    """{'holders': the latest names, or None when no record ever set them; 'waits': its wait line, in the grammar's order;
    'done': the body's criteria, each {'met': True, False or None when it has no box, 'kind', 'name', 'detail'}}."""
    holders = (holder_values(issue) or [None])[-1]
    if any(question["fields"].get("asks") == "owner" for question in open_questions(issue)):
        waits = OWNER_WAIT
    elif blockers:
        waits = " ".join(f"blocked by #{number}" for number in blockers)
    else:
        waits = "held" if holders else "no holder"
    # the body alone, since a section is edited there with its diff posted as a comment
    current = sections(issue.get("body"))
    done = [dict(zip(("box", "kind", "name", "detail"), CRITERION.match(item).groups())) for item in ITEM.findall(current.get("done", ""))]
    done = [{"met": criterion["box"] and criterion["box"] != " ", "kind": criterion["kind"] or "", "name": criterion["name"] or criterion["detail"], "detail": criterion["detail"] if criterion["name"] else ""}
            for criterion in done]
    return {"holders": holders, "waits": waits, "done": done}
