"""An issue's latest state, composed from its body and comments by the grammar file, which alone names the keywords and keys."""
import pathlib
import re

GRAMMAR = pathlib.Path(__file__).resolve().parents[1] / "skills" / "kick-off" / "references" / "issue-grammar.md"
DATA = re.compile(r"^```teamwork\n(.*?)^```", re.M | re.S)


def rows(text, heading):
    """{word: role} of the table under `## <heading>`, the word its first column's code span, the role its last cell."""
    section = re.search(rf"^## {heading}\n(.*?)(?=^## |\Z)", text, re.M | re.S).group(1)
    return {w: r.strip() for w, r in re.findall(r"^\| `([^`]+)` \|.*\|([^|\n]*)\|$", section, re.M)}


def load(path=GRAMMAR):
    text = path.read_text()
    return rows(text, "Keywords"), rows(text, "Data"), rows(text, "Sections")


KEYWORDS, KEYS, SECTIONS = load()
WORD = {role: word for table in (KEYWORDS, KEYS) for word, role in table.items() if role}
ITEM = re.compile(r"^(?:\d+\.|[-*])\s+(.*)$", re.M)


def keyword(text):
    """The keyword a comment opens with, or None when its first line opens with none the grammar names."""
    found = re.match(r"\s*([A-Z]+):", text or "")
    return found and found.group(1) in KEYWORDS and found.group(1) or None


def data(text):
    """The `key: value` lines of its reserved blocks, keys the grammar names only."""
    pairs = (line.partition(":") for block in DATA.findall(text or "") for line in block.splitlines())
    return {k.strip(): v.strip() for k, sep, v in pairs if sep and k.strip() in KEYS}


def sections(text):
    """{role: text} of the sections it carries, by the heading the grammar names."""
    found = re.findall(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", text or "", re.M | re.S)
    return {SECTIONS[h.strip()]: body for h, body in found if h.strip() in SECTIONS}


def records(issue):
    """The body, then each comment, as (keyword, data, comment), oldest first; the body has no keyword."""
    return [(None, data(issue.get("body")), None)] + [(keyword(c["body"]), data(c["body"]), c) for c in issue.get("comments", [])]


def exchange(issue):
    """Its asks and answers, oldest first, each as (role, data, comment); the other keywords take no part in a wait."""
    return [(KEYWORDS[w], d, c) for w, d, c in records(issue) if KEYWORDS.get(w) in ("ask", "answer")]


def holder_values(issue):
    """Each holders value set, oldest first, as a list of names."""
    return [d[WORD["holders"]].split() for _, d, _ in records(issue) if WORD["holders"] in d]


def compose(issue, blockers=()):
    """{'holders': the latest names, or None when no record ever set them; 'waits': its wait line, in the grammar's order;
    'goal': the first paragraph of the body's goal, its lines joined, or ''; 'done': the body's criteria}."""
    holders = (holder_values(issue) or [None])[-1]
    asked = exchange(issue)[-1:]
    if blockers:
        waits = " ".join(f"blocked by #{n}" for n in blockers)
    elif asked and asked[0][0] == "ask":
        waits = "waits on the owner" if asked[0][1].get(WORD["audience"]) == "owner" else "waits on the manager"
    else:
        waits = "held" if holders else "deferred" if holders == [] else "no holder"
    # the body alone, since a section is edited there with its diff posted as a comment
    current = sections(issue.get("body"))
    goal = " ".join(line.strip() for line in current.get("goal", "").strip().split("\n\n")[0].splitlines() if line.strip())
    return {"holders": holders, "waits": waits, "goal": goal, "done": ITEM.findall(current.get("done", ""))}
