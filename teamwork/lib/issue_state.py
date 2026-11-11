"""An issue's latest state, composed from its body and comments by the grammar file, which alone names the keywords and keys."""
import difflib
import pathlib
import re

GRAMMAR = pathlib.Path(__file__).resolve().parents[1] / "skills" / "kick-off" / "references" / "issue-grammar.md"
DATA = re.compile(r"^```teamwork\n(.*?)^```", re.M | re.S)


def rows(text, heading):
    """{word: role} of the table under `## <heading>`, the word its first column's code span, the role its last cell."""
    section = re.search(rf"^## {heading}\n(.*?)(?=^## |\Z)", text, re.M | re.S).group(1)
    return {word: role.strip() for word, role in re.findall(r"^\| `([^`]+)` \|.*\|([^|\n]*)\|$", section, re.M)}


def load(path=GRAMMAR):
    text = path.read_text()
    since = re.search(r"posted before `(\d{4}-\d\d-\d\d)`", text).group(1)
    return rows(text, "Keywords"), rows(text, "Data"), rows(text, "Sections"), rows(text, "Decisions"), since


KEYWORDS, KEYS, SECTIONS, DECISION_KEYS, TYPED_SINCE = load()
WORD = {role: word for table in (KEYWORDS, KEYS) for word, role in table.items() if role}
FIELD = {role: word for word, role in DECISION_KEYS.items()}
SECTION_NAMES = {name.lower(): name for name in SECTIONS}
INFORM = next(word for word, role in KEYWORDS.items() if not role)  # the keyword that only informs, which the owner reads as what happened
DECISION = re.compile(r"^```decision\n(.*?)^```", re.M | re.S)
DIFF = re.compile(r"^(`{3,})diff\n(.*?)^\1$", re.M | re.S)
# the note `resolve` posts on a parent it stops, naming the parts it stops with it
STOPPING = "DECIDED: stopping #"
ITEM = re.compile(r"^(?:\d+\.|[-*])\s+(.*)$", re.M)
# a criterion `[check] **<name>**: <details>`, after a task-list box when one marks it met; one filed before names were asked for is its own name
CRITERION = re.compile(r"^(?:\[([ xX])\]\s+)?(?:\[(\w+)\]\s+)?(?:\*\*(.+?)\*\*:?\s*)?(.*)$")
# a run of n backticks closes only on a run of exactly n, so a ``…`` span may hold single backticks
SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")


def keyword(text):
    """The keyword a comment opens with, or None when its first line opens with none the grammar names."""
    found = re.match(r"\s*([A-Z]+):", text or "")
    return found and found.group(1) in KEYWORDS and found.group(1) or None


def data(text):
    """The `key: value` lines of its reserved blocks, keys the grammar names only."""
    pairs = (line.partition(":") for block in DATA.findall(text or "") for line in block.splitlines())
    return {k.strip(): value.strip() for k, separator, value in pairs if separator and k.strip() in KEYS}


FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def fence_step(fence, line):
    """(fence, marks) after LINE: the open fence as (run, info) or None, and whether LINE opened or closed one, as CommonMark reads it: a run of three or
    more backticks or tildes, indented up to three spaces, opens, a backtick run's info holding no backtick, and a bare run of the same mark at least
    as long, followed by nothing but spaces or tabs, closes."""
    found = FENCE.match(line)
    if not found:
        return fence, False
    run, info = found.groups()
    if fence is None:
        return (None, False) if run[0] == "`" and "`" in info else ((run, info.strip(" \t")), True)
    if run[0] == fence[0][0] and len(run) >= len(fence[0]) and not info.strip(" \t"):
        return None, True
    return fence, False


def language(fence):
    """The language of an open FENCE, its info string's first word in lowercase, as CommonMark reads it; empty outside a fence."""
    return (fence[1].split() or [""])[0].lower() if fence else ""


# a fence a writer may take for the teamwork one: its info string spelt otherwise, or a data language
LOOKALIKES = ("teamwork", "yaml", "yml")
# a fence that quotes lines as changed text, never as a record's data
QUOTING = ("diff",)
# a line opening a list item or an HTML block, inside which CommonMark reads fences that `fence_step` does not follow; a block quote's fences
# sit on its `>` lines, which `fence_step` never reads as fences, and a quote never takes in a line without `>` that opens a fence
UNTRACKED = re.compile(r"^ {0,3}(?:[-+*](?:\s|$)|\d{1,9}[.)](?:\s|$)|<)")
HOLDERS_LINE = re.compile(rf"^\s*{WORD['holders']}\s*:")
NAMES = re.compile(r"([a-z0-9][a-z0-9-]*)?( [a-z0-9][a-z0-9-]*)*")
TASKS = re.compile(r"(#\d+)?( #\d+)*")
# the opening of a line that reads as a key or a keyword, spelt right or not
KEY_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z ]*?)\s*[:=]")
KEYWORD_LINE = re.compile(r"^\s*[*_#>-]*\s*(?:" + "|".join(KEYWORDS) + r")\b", re.I)
EXACT_KEYWORD = re.compile(r"^\s*(" + "|".join(KEYWORDS) + r"):")
# the keyword each posting verb opens its text with: `decide` answers, `resolve` informs
VERB_KEYWORD = {"decide": WORD["answer"], "resolve": INFORM}
# the Plain words caps on a title, a summary line and a decision: the live board's plain summary lines and decisions ran to 20 words, its dense
# ones from 23, and a second `,` `;` or `:` joined a further idea in every dense line a fresh reader marked
TITLE_CHARS = 40
SENTENCE_WORDS = 20
SENTENCE_MIN_WORDS = 5  # a subject, a verb and what it acts on, with an article or a modifier
SENTENCE_BREAKS = 1
TASK_NUMBER = re.compile(r"#\d+\b")
BREAK = re.compile(r"[,;:](?=\s)")


def stem(words):
    """A key's words without case, sign or plural, so `Holder` and `holders` meet."""
    return " ".join(word.rstrip("s") for word in re.findall(r"[a-z]+", words.lower()))


def defects(kind, text, old=""):
    """The defects of TEXT written by KIND (comment, decide, resolve, file, edit-body, edit-line), each a plain sentence ending in its fix; none
    when it reads as meant. A defect OLD already held does not count, so an edit that fixes a body is never blocked."""
    found = _defects(kind, text)
    held = [signature for signature, _ in _defects(kind, old)] if old else []
    return [sentence for signature, sentence in found if signature not in held]


def _defects(kind, text):
    """[(signature, sentence)] of TEXT, the signature free of the line number so an edit that moves a line keeps it."""
    if kind == "title":
        return plain("title", text)
    if kind == "edit-line":
        one = re.fullmatch(WORD["answer"] + r":[^\n]*\S[^\n]*", (text or "").rstrip("\n"))
        return [] if one else [("edit-line", f"the keyword line is not one line that opens `{WORD['answer']}:` and says what changed; write `{WORD['answer']}: <what changed and why>` on one line")]
    found, fence, headings, opening, offset = [], None, {}, "", 0
    keys, stems = " ".join(KEYS), {stem(key): key for key in KEYS}
    # the reader skips blank lines before a keyword, so the first line is the first that holds something
    lines = (text or "").lstrip().split("\n") if kind in ("comment", "decide", "resolve") else (text or "").split("\n")
    # the lines `data` reads, by offset, so the key checks cover what code acts on, a teamwork block nested in another fence included
    read = [(block.start(1), block.end(1)) for block in DATA.finditer("\n".join(lines))]
    for number, line in enumerate(lines, 1):
        start, offset = offset, offset + len(line) + 1
        fence, marks = fence_step(fence, line)
        if any(low <= start < high for low, high in read):
            if line.strip():
                key, colon, value = (part.strip() for part in line.partition(":"))
                if not colon or key not in KEYS:
                    spelt = KEY_LINE.match(line)
                    near = stems.get(stem(spelt.group(1))) if spelt else None
                    found.append((f"fence {line.strip()}", f"line {number}, `{line.strip()}`, is no key the teamwork fence takes; "
                                  + (f"spell it `{near}: <value>`" if near else f"use one of: {keys}, as `key: value`")))
                elif key == WORD["holders"] and not NAMES.fullmatch(value):
                    found.append((f"names {line.strip()}", f"line {number}, `{line.strip()}`, holds more than session names; write the names lowercase, separated by spaces only, as `{key}: a-worker b-worker`"))
                elif key == WORD["audience"] and value != "owner":
                    found.append((f"asks {line.strip()}", f"line {number}, `{line.strip()}`, is no value `{key}` takes; write exactly `{key}: owner`"))
                elif key == WORD["live"] and not value.isdigit():
                    found.append((f"count {line.strip()}", f"line {number}, `{line.strip()}`, is no count; write `{key}: 12`"))
                elif key == WORD["depends"] and not TASKS.fullmatch(value):
                    found.append((f"tasks {line.strip()}", f"line {number}, `{line.strip()}`, is no task list; write `{key}: #12 #13`"))
            continue
        if marks:
            opening = line
            continue
        if fence:
            if language(fence) in LOOKALIKES and KEY_LINE.match(line) and stem(KEY_LINE.match(line).group(1)) in stems:
                found.append((f"lookalike {line.strip()}", f"line {number}, `{line.strip()}`, sits in a fence opened by {opening!r}, which no code reads as data; open the fence with exactly ```teamwork: three backticks at the line's start and nothing after `teamwork`"))
            continue
        near = KEY_LINE.match(line)
        if near and stem(near.group(1)) in stems:
            found.append((f"plain {line.strip()}", f"line {number}, `{line.strip()}`, opens with a key word outside a teamwork fence, so no code reads it; to write it as prose put it in a code span, else put `{stems[stem(near.group(1))]}: <value>` inside a ```teamwork fence"))
        heading = re.match(r"^#{1,6}\s*([A-Za-z].*?)\s*$", line)
        if heading and kind in ("file", "edit-body"):
            words = re.sub(r"\s*(\(.*\)|:)$", "", heading.group(1)).lower()
            close = difflib.get_close_matches(words, list(SECTION_NAMES), 1, 0.85)
            section = SECTION_NAMES[close[0]] if close else None
            if section:
                headings[section] = headings.get(section, 0) + (line == f"## {section}")
                if line != f"## {section}":
                    found.append((f"heading {line}", f"line {number}, `{line}`, misspells a section heading; write exactly `## {section}`"))
    found += [(f"repeated {section}", f"`## {section}` appears {count} times; keep one and merge the rest into it") for section, count in headings.items() if count > 1]
    found += unread_holders(text, {line for signature, _ in found for line in [signature.partition(" ")[2]]})
    if kind in ("comment", "decide", "resolve") and lines:
        found += keyword_defects(kind, lines)
    if kind in ("file", "edit-body"):
        found += body_defects(text)
    if kind == "decide":
        found += plain("decision", (decision(text) or {}).get(FIELD["decision"], ""))
    return found


def unread_holders(text, flagged):
    """[(signature, sentence)] for each holders line that `data` does not read and no other defect named, but one a diff fence quotes, since
    a holders line `data` skips sets no holder however its fence is spelt; after a line outside every fence opens a list item or an HTML
    block, no diff fence exempts a line, since CommonMark may read that fence otherwise."""
    text = text or ""
    # the lines `data` reads, by offset; fences are tracked on every line, read ones included, as CommonMark reads them
    read = [(block.start(1), block.end(1)) for block in DATA.finditer(text)]
    found, fence, offset, tracked = [], None, 0, True
    for line in text.split("\n"):
        start, offset = offset, offset + len(line) + 1
        tracked = tracked and not (fence is None and UNTRACKED.match(line))
        fence, marks = fence_step(fence, line)
        if any(low <= start < high for low, high in read):
            continue
        quoted = tracked and language(fence) in QUOTING
        if not marks and HOLDERS_LINE.match(line) and not quoted and line.strip() not in flagged:
            found.append((f"unread {line.strip()}", f"`{line.strip()}` sits where no code reads it as data, so it sets no holder; put it alone in a fence opened by exactly ```teamwork and closed by ```"))
    return found


def keyword_defects(kind, lines):
    """[(signature, sentence)] of the keyword a comment, decision or summary opens with, read from its LINES."""
    found, first = [], EXACT_KEYWORD.match(lines[0])
    if not first and KEYWORD_LINE.match(lines[0]):
        found.append(("near-keyword", f"the first line, `{lines[0]}`, nearly opens with a keyword; open it with exactly one of {' '.join(KEYWORDS)} and a colon, as `{WORD['answer']}: <words>`"))
    if not first and any(EXACT_KEYWORD.match(line) for line in lines[1:]):
        found.append(("later-keyword", "a keyword opens a later line, which no code reads; move it to the first line"))
    own = VERB_KEYWORD.get(kind)
    if first and own and first.group(1) != own:
        found.append(("other-verb", f"{kind} opens with `{own}:`, not `{first.group(1)}:`; change the first word, or post the text with the verb that matches it"))
    return found


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


def records(issue):
    """The body, then each comment, as (keyword, data, comment), oldest first; the body has no keyword, and an untrusted author's text records nothing."""
    return [(None, data(issue.get("body")) if trusted(issue) else {}, None)] + [(keyword(comment["body"]), data(comment["body"]), comment) for comment in issue.get("comments", []) if trusted(comment)]


def decision(text):
    """The `key: value` lines of its `decision` block, keys the grammar names only, and its `answers` from the line right after the keyword when
    the block lacks one, since `decide` puts the keyword before a body that opens with that line; None when it holds no such block."""
    found = DECISION.search(text or "")
    if not found:
        return None
    pairs = (line.partition(":") for line in found.group(1).splitlines())
    fields = {k.strip(): value.strip() for k, separator, value in pairs if separator and k.strip() in DECISION_KEYS}
    lead = re.match(rf"\s*[A-Z]+:\s*{FIELD['answers']}:[ \t]*(\S+)", text)
    if lead:
        fields.setdefault(FIELD["answers"], lead.group(1))
    return fields


def event(comment):
    """Whether a `DECIDED:` comment is an event, which binds and answers nothing: no `decision` block, and a teamwork block, a body
    edit's diff, or a stop's note."""
    text = comment["body"] or ""
    return decision(text) is None and bool(DATA.search(text) or DIFF.search(text) or text.startswith(STOPPING))


def legacy(comment):
    """Whether it was posted before decisions were typed, so it keeps its earlier reading; one with no date counts as legacy."""
    return (comment.get("createdAt") or "") < TYPED_SINCE


def role(decider):
    """`owner`; `manager` for a session named `<project>-manager`, or `<project>-manager-next`, the name Succession gives; else `worker`."""
    return "owner" if decider == "owner" else "manager" if decider == "manager" or decider.removesuffix("-next").endswith("-manager") else "worker"


def first_line(comment):
    """A comment's first line of text without its keyword, the line after a keyword that stands alone."""
    return next((line.strip() for line in re.sub(r"^\s*[A-Z]+:", "", (comment["body"] or "").strip()).splitlines() if line.strip()), "")


def questions(issue):
    """Its questions, oldest first, each {'ask': the `BLOCKED:` comment, 'fields': its data, 'answer': the comment that settles it or None}:
    a later decision that is no event settles the question whose url it names and each earlier open ask with the same first line, since an ask
    posted again is one question; with no `answers` it settles each open question its decider may answer: the owner any, a manager any
    not asked of the owner, a worker none, and a decision from before decisions were typed any."""
    found = []
    for word, fields, comment in records(issue)[1:]:
        kind = KEYWORDS.get(word)
        if kind == "ask":
            found.append({"ask": comment, "fields": fields, "answer": None})
        elif kind == "answer" and not event(comment):
            block = decision(comment["body"]) or {}
            named, decider = block.get(FIELD["answers"], ""), role(block.get(FIELD["decider"], ""))
            said = {first_line(question["ask"]) for question in found if question["ask"]["url"] == named}
            for question in found:
                to_owner = question["fields"].get(WORD["audience"]) == "owner"
                general = legacy(comment) or decider == "owner" or decider == "manager" and not to_owner
                if question["answer"] is None and (general if not named else question["ask"]["url"] == named or first_line(question["ask"]) in said):
                    question["answer"] = comment
    return found


def open_questions(issue):
    return [question for question in questions(issue) if question["answer"] is None]


def holder_values(issue):
    """Each holders value set, oldest first, as a list of names."""
    return [fields[WORD["holders"]].split() for _, fields, _ in records(issue) if WORD["holders"] in fields]


def live_runs(issue):
    """The latest `live runs` count a trusted record set, or None when none did."""
    return next((int(fields[WORD["live"]]) for _, fields, _ in reversed(records(issue)) if fields.get(WORD["live"], "").isdigit()), None)


def compose(issue, blockers=(), parts_wait=False):
    """{'holders': the latest names, or None when no record ever set them; 'waits': its wait line, in the grammar's order, PARTS_WAIT telling whether
    each open part waits on a task;
    'done': the body's criteria, each {'met': True, False or None when it has no box, 'kind', 'name', 'detail'}}."""
    holders = (holder_values(issue) or [None])[-1]
    asked = open_questions(issue)[-1:]
    if blockers:
        waits = " ".join(f"blocked by #{number}" for number in blockers)
    elif parts_wait:
        waits = "waits on its parts"
    elif asked:
        waits = "waits on the owner" if asked[0]["fields"].get(WORD["audience"]) == "owner" else "waits on the manager"
    else:
        waits = "held" if holders else "no holder"
    # the body alone, since a section is edited there with its diff posted as a comment
    current = sections(issue.get("body"))
    done = [dict(zip(("box", "kind", "name", "detail"), CRITERION.match(item).groups())) for item in ITEM.findall(current.get("done", ""))]
    done = [{"met": criterion["box"] and criterion["box"] != " ", "kind": criterion["kind"] or "", "name": criterion["name"] or criterion["detail"], "detail": criterion["detail"] if criterion["name"] else ""}
            for criterion in done]
    return {"holders": holders, "waits": waits, "done": done}
