"""The issue board: the board's open tasks as a tree in the owner's reading order, laid out as guide-prefixed rows for a width."""
import re
import unicodedata

import decisions
import issue_state

# the latest closed parts a parent lists, newest first, an ellipsis below them when more landed before
SHOWN_CLOSED = 4
# close reasons of work stopped, not done; GitHub's duplicate close counts with them
STOPPED = ("NOT_PLANNED", "DUPLICATE")
# waits that need someone, which the status shows; a blocked task shows its `blocked by` line instead
SHOWN_WAITS = ("waits on the owner", "waits on the manager")
WIDTHS = (24, 30, 40, 60, 80)
PANE_WIDTH = 40  # a narrow docked pane, for a listing given no width, as before the pane is first drawn
MIN_TEXT = 16  # cells a row keeps for its text before its depth stops growing
NOTE_LINES = 3  # lines a question or decision takes at most, so one long text leaves room for the next task


def next_step_of(comments):
    """A parent's next step: the latest `REPORTED:` that names one, so a parent with nothing open says why it stays open; empty when none does."""
    firsts = [(comment["body"] or "").replace("\r\n", "\n").split("\n\n")[0] for comment in comments]
    return next((" ".join(first.rsplit("next step:", 1)[1].split()) for first in reversed(firsts) if first.startswith("REPORTED:") and "next step:" in first),
                "")


def progress_of(summary, blockers, next_step):
    """The parts' count; once every part is done and the task is still open, it says what holds the task open: its open blockers, a report's
    next step, else nothing named."""
    total = summary.get("total")
    if not total:
        return ""
    count = f"{summary['completed']}/{total} parts done"
    if summary["completed"] != total:
        return count
    return count + (f", task waits on {' '.join(f'#{number}' for number in blockers)}" if blockers
                    else ", task waits on its next step" if next_step else ", task still open")


def blockers_of(node):
    """Every task this one depends on; one closed as completed is marked closed, since only that releases it."""
    return [{"number": blocker["number"], "closed": blocker.get("state") == "CLOSED" and blocker.get("stateReason") not in STOPPED}
            for blocker in (node.get("blockedBy") or {}).get("nodes", [])]


def entry(node, superseded=frozenset()):
    """One task as the board shows it: its status, its open questions and decisions, its criteria, its parts' progress."""
    every = blockers_of(node)
    blockers = [blocker["number"] for blocker in every if not blocker["closed"]]
    state = issue_state.compose({"body": node["body"], "trusted": node["trusted"], "comments": node["comments"]["nodes"]}, blockers)
    summary = node.get("subIssuesSummary") or {}
    closed = [{"number": task["number"], "title": issue_state.title(task), "url": task["url"], "blockers": blockers_of(task),
               "stopped": task.get("stateReason") in STOPPED} for task in (node.get("subIssues") or {}).get("nodes", []) if task["state"] == "CLOSED"]
    wait = state["waits"].split(" by ")[0]
    next_step = next_step_of(node["comments"]["nodes"]) if summary.get("total") and summary.get("total") == summary.get("completed") else ""
    return {"number": node["number"], "title": issue_state.title(node), "url": node["url"],
            "holder": " ".join(state["holders"] or []), "wait": wait if wait in SHOWN_WAITS else "",
            "progress": progress_of(summary, blockers, next_step),
            "done": [item for item in state["done"] if item["kind"] != "task"],
            "next": next_step, "latest": max((comment.get("createdAt") or "" for comment in node["comments"]["nodes"]), default=""),
            **decisions.shown(node, superseded), "tasks": [], "blockers": every, "closed": closed[::-1][:SHOWN_CLOSED], "earlier": summary.get("completed", 0) > min(len(closed), SHOWN_CLOSED)}


def need_of(issue):
    """How soon a task needs someone, with its parts: 0 when it or a part waits on the owner, 1 when it or a part is held, else 2; and the latest comment time among them."""
    parts = [need_of(task) for task in issue["tasks"]]
    own = 0 if issue["wait"] == "waits on the owner" else 1 if issue["holder"] else 2
    return min([own] + [part[0] for part in parts]), max([issue["latest"]] + [part[1] for part in parts])


def board(nodes):
    """The open tasks as a tree: parts under their parent by number, roots by what they need: the owner's answer first, then held, then blocked or unheld,
    the latest comment first in each."""
    superseded = decisions.superseded_in(nodes)
    items = {node["number"]: entry(node, superseded) for node in nodes}
    top = []
    for node in nodes:
        parent = (node["parent"] or {}).get("number")
        (items[parent]["tasks"] if parent in items else top).append(items[node["number"]])

    def order(issues):
        for issue in issues:
            issue["tasks"].sort(key=lambda task: task["number"])
            order(issue["tasks"])
    order(top)
    needs = {issue["number"]: need_of(issue) for issue in top}
    top.sort(key=lambda issue: issue["number"])
    top.sort(key=lambda issue: needs[issue["number"]][1], reverse=True)  # stable, so a tie keeps the lower number first
    top.sort(key=lambda issue: needs[issue["number"]][0])
    return top


def cells(text):
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def wrap(text, width, first=None):
    """Greedy word wrap by display cells, the first line FIRST cells wide when given, every other WIDTH; a word wider than a whole
    line breaks after its last hyphen that fits, else is cut."""
    if width is None:
        return [text.replace("\u00a0", " ")]
    lines, line = [], ""

    def room():
        return width if first is None or lines else first

    for word in [word for word in re.split(r"[ \t\n]+", text) if word]:  # a no-break space glues the words it joins
        if line and cells(line) + 1 + cells(word) > room():
            lines.append(line)
            line = ""
        while cells(word) > room():
            cut = 0
            while cells(word[:cut + 1]) <= room():
                cut += 1
            hyphen = word.rfind("-", 0, cut)
            cut = hyphen + 1 if hyphen > 0 else max(cut, 1)
            lines.append(word[:cut])
            word = word[cut:]
        line = f"{line} {word}" if line else word
    lines = lines + [line] if line or not lines else lines
    return [line.replace("\u00a0", " ") for line in lines]


def blocked_by(blockers):
    """What a task waits on: the tasks it depends on that are still open, since a closed one no longer holds it; nothing once every one is closed."""
    return "blocked by " + " ".join(f"#{blocker['number']}" for blocker in blockers if not blocker["closed"]) if not all(blocker["closed"] for blocker in blockers) else ""


def status(issue):
    return " ".join(part for part in (issue["progress"], issue["holder"], issue["wait"]) if part)


def rows(issues, width=PANE_WIDTH):
    """Each task in reading order as a row: `guide`, drawn before its first line, `pad`, before every later line, `home`, the parent
    a row too deep for WIDTH names as `(in #n)` at its parent's depth, and `ancestors`; a level adds 4 cells, a root's parts start at 2."""
    placed = []

    def place(issue, depth, ancestors):
        home = None
        if depth and width is not None and width - (2 + 4 * depth) < MIN_TEXT:
            depth, home = depth - 1, ancestors[-1]
        placed.append((issue, depth, home, ancestors))
        for task in issue["tasks"]:
            place(task, depth + 1, ancestors + [issue["number"]])

    for issue in issues:
        place(issue, 0, [])

    def more_at(index, depth):
        for _, later, _, _ in placed[index + 1:]:
            if later <= depth:
                return later == depth
        return False

    out = []
    for index, (issue, depth, home, ancestors) in enumerate(placed):
        if depth == 0:
            guide, pad = "", "  "
        else:
            lead = "  " + "".join("│   " if more_at(index, level) else "    " for level in range(1, depth))
            last = not more_at(index, depth)
            guide, pad = lead + ("└ " if last else "├ "), lead + ("    " if last else "│   ")
        out.append({**issue, "done": [{**item, "line": criterion(item)} for item in issue["done"]], "tasks": [], "guide": guide, "pad": pad, "home": home, "ancestors": ancestors})
    return out


def label(row):
    """A row's title line: its number, its title, `(in #n)` when it sits too deep for its parent's depth, and `(blocked by #a #b)` while a blocker
    is open. No-break spaces glue `(blocked by` to its first number, and the `)` ends the last number, so a wrap never leaves `(blocked` or a lone `)` on a line."""
    held = " (" + blocked_by(row["blockers"]).replace(" ", "\u00a0", 2) + ")" if blocked_by(row["blockers"]) else ""
    return f"#{row['number']} {row['title']}" + (f" (in #{row['home']})" if row["home"] else "") + held


def criterion(item):
    """A criterion's line: a circle, then its name; the box and the kind stay in the body, since the pane shows what remains to prove, not a pass."""
    return f"\u25cb {item['name']}"


def held_offsets(title, blockers):
    """Per title line, the offset where its `(blocked by …)` text begins, else the line's length: the text the pane draws dim."""
    held = len(label({"number": 0, "title": "", "home": None, "blockers": blockers})) - len("#0 ") if blocked_by(blockers) else 0
    start = len(" ".join(title)) - held if held else None
    offsets, at = [], 0
    for line in title:
        offsets.append(len(line) if start is None else min(max(start - at, 0), len(line)))
        at += len(line) + 1
    return offsets


def decision_notes(decided, room):
    """The decision lines of a task, newest first, and the indexes of the lines of a manager's or a worker's decision, the quiet ones."""
    lines, quiet = [], []
    for decision in decided:
        start = len(lines)
        lines += note(decision["mark"], (f"[{decision['time']}] " if decision["time"] else "") + decision["decision"], room)
        if decision["mark"] == "\u25c7":
            quiet += range(start, len(lines))
    return lines, quiet


def heading(row, width):
    """A row's lines, wrapped to WIDTH less its guide: `title` and `status`, which the pane always shows, `notes`, the open questions, which it shows too, then, once the row is open, the decisions newest first and, once every part is done, what keeps it open, `questions`, how many of the first notes are the open questions, `quiet`, the indexes of the notes drawn dim, and `held`, where each title line's `(blocked by …)` text begins."""
    room = None if width is None else width - max(cells(row["guide"]), cells(row["pad"]))
    said = status(row)
    # parts share a line when they fit; else each takes its own
    shown = [said] if said and (room is None or cells(said) <= room) else [line for part in (row["progress"], row["holder"], row["wait"]) if part for line in wrap(part, room)]
    notes = [line for question in row.get("questions", []) for line in note("?", question, room)]
    shift = len(notes)
    deciding, quiet = decision_notes(row.get("decided", []), room)
    notes += deciding
    notes += note("next step:", row["next"], room, limit=None) if row.get("next") else []  # the next step has no other place to be read in full
    # the first line sits after the guide, the later ones after the wider pad, so a title that fits beside its guide takes one line
    title = wrap(label(row), room, None if width is None else width - cells(row["guide"]))
    return {"title": title, "status": shown, "notes": notes, "questions": shift, "quiet": [shift + k for k in quiet],
            "held": held_offsets(title, row["blockers"])}


def note(mark, text, room, limit=NOTE_LINES):
    """A note's lines: MARK and its text, later lines 2 cells in, at most LIMIT when one is given, the last ending `…` when cut."""
    indent = cells(mark) + 1
    inner = None if room is None else room - indent
    lines = wrap(text, inner)
    if limit and len(lines) > limit:
        last = lines[limit - 1]
        while inner is not None and last and cells(last) + 1 > inner:
            last = last[:-1].rstrip()
        lines = lines[:limit - 1] + [last + "…"]
    return [f"{mark} {lines[0]}"] + [f"{' ' * indent}{line}" for line in lines[1:]]


def lines(issues, width=None):
    """The board as text, every row unfolded: a row's title, status and link lines, then what the pane folds under it, each wrapped to WIDTH."""
    for row in rows(issues, width):
        room = None if width is None else width - max(cells(row["guide"]), cells(row["pad"]))
        head = heading(row, width)
        yield row["guide"] + head["title"][0]
        yield from (row["pad"] + line for line in head["title"][1:] + head["status"] + head["notes"])
        details = [item["line"] for item in row["done"]]
        details += [f"#{task['number']} {task['title']} closed{' stopped' * task['stopped']}" + (f" {blocked_by(task['blockers'])}" if blocked_by(task["blockers"]) else "") for task in row["closed"]]
        details += ["…"] if row["earlier"] else []
        yield from (row["pad"] + line for detail in details for line in wrap(detail, room))


def check(issues):
    """Per width, whether the rows fit: no line wider than the width, and each child not capped starting at least 2 cells right of every line of its parent."""
    for width in WIDTHS:
        laid = rows(issues, width)
        text = list(lines(issues, width))
        widest = max(map(cells, text), default=0)
        start = {row["number"]: cells(row["guide"]) for row in laid}
        deepest = {row["number"]: max(cells(row["guide"]), cells(row["pad"])) for row in laid}
        crowded = [row["number"] for row in laid if row["ancestors"] and not row["home"] and start[row["number"]] < deepest[row["ancestors"][-1]] + 2]
        capped = sum(bool(row["home"]) for row in laid)
        verdict = f"breaks: a line is {widest} cells wide" if widest > width else f"breaks: #{crowded[0]} starts within its parent" if crowded else "fits"
        yield f"width {width}: {len(text)} lines, widest {widest}, capped {capped}, {verdict}"
