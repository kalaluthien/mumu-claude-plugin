"""An issue's latest state, composed from its body and comments by the grammar file, which alone names the keywords and keys."""
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
    return rows(text, "Keywords"), rows(text, "Data"), rows(text, "Sections")


KEYWORDS, KEYS, SECTIONS = load()
WORD = {role: word for table in (KEYWORDS, KEYS) for word, role in table.items() if role}
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


def exchange(issue):
    """Its asks and answers, oldest first, each as (role, data, comment); the other keywords take no part in a wait."""
    return [(KEYWORDS[word], fields, comment) for word, fields, comment in records(issue) if KEYWORDS.get(word) in ("ask", "answer")]


def holder_values(issue):
    """Each holders value set, oldest first, as a list of names."""
    return [fields[WORD["holders"]].split() for _, fields, _ in records(issue) if WORD["holders"] in fields]


def cloud(issue):
    """The names its latest cloud value set, which run where no local listing shows them."""
    return ([fields[WORD["cloud"]].split() for _, fields, _ in records(issue) if WORD["cloud"] in fields] or [[]])[-1]


def deferral(issue):
    """Why it is left for later: the latest deferral's reason, or None when none was set or holders with names came after it."""
    reason = None
    for _, fields, _ in records(issue):
        if fields.get(WORD["holders"]):
            reason = None
        if WORD["deferral"] in fields:
            reason = fields[WORD["deferral"]] or None
    return reason


def compose(issue, blockers=()):
    """{'holders': the latest names, or None when no record ever set them; 'deferred': its deferral's reason or None; 'waits': its wait line, in the grammar's order;
    'goal': the lines of the body's goal, blank lines kept so a Markdown reader sees its paragraphs, its data blocks left out;
    'done': the body's criteria, each {'met': True, False or None when it has no box, 'kind', 'name', 'detail'}}."""
    holders = (holder_values(issue) or [None])[-1]
    deferred = deferral(issue)
    asked = exchange(issue)[-1:]
    if blockers:
        waits = " ".join(f"blocked by #{number}" for number in blockers)
    elif asked and asked[0][0] == "ask":
        waits = "waits on the owner" if asked[0][1].get(WORD["audience"]) == "owner" else "waits on the manager"
    else:
        waits = "held" if holders else "deferred" if deferred else "no holder"
    # the body alone, since a section is edited there with its diff posted as a comment
    current = sections(issue.get("body"))
    done = [dict(zip(("box", "kind", "name", "detail"), CRITERION.match(item).groups())) for item in ITEM.findall(current.get("done", ""))]
    done = [{"met": criterion["box"] and criterion["box"] != " ", "kind": criterion["kind"] or "", "name": criterion["name"] or criterion["detail"], "detail": criterion["detail"] if criterion["name"] else ""}
            for criterion in done]
    return {"holders": holders, "deferred": deferred, "waits": waits, "goal": DATA.sub("", current.get("goal", "")).strip().splitlines(), "done": done}
