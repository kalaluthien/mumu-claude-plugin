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


def summary_of(body):
    """A task's summary when it has no Goal section: its body's first paragraph, its lines joined, unless it is a heading."""
    first = (body or "").replace("\r\n", "\n").strip().split("\n\n")[0]
    return "" if first.startswith("#") else " ".join(line.strip() for line in first.splitlines() if line.strip())


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
    """One task as the board shows it: its status, its open questions and owner decisions, its goal and criteria, its parts' progress."""
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
            "goal": "" if state["goal"] else summary_of(node["body"]), "detail": state["goal"], "done": [item for item in state["done"] if item["kind"] != "task"],
            "next": next_step,
            **decisions.shown(node, superseded), "tasks": [], "blockers": every, "closed": closed[::-1][:SHOWN_CLOSED], "earlier": summary.get("completed", 0) > min(len(closed), SHOWN_CLOSED)}


def related(nodes, roots):
    """{root: its group's lowest number}: roots whose tasks name each other, or wait on one another."""
    group = {number: number for number in roots}
    parent = {node["number"]: (node["parent"] or {}).get("number") for node in nodes}

    def find(number):
        while group[number] != number:
            number = group[number]
        return number

    def root_of(number):
        seen = set()
        while parent.get(number) in parent and number not in seen:
            seen.add(number)
            number = parent[number]
        return number

    def join(first, second):
        if first in group and second in group:
            first, second = find(first), find(second)
            group[max(first, second)] = min(first, second)

    for node in nodes:
        if node["number"] in group:
            for text in [node["body"]] + [comment["body"] for comment in node["comments"]["nodes"]]:
                for named in re.findall(r"#(\d+)\b", text or ""):
                    join(node["number"], root_of(int(named)))
        for blocker in node["blockedBy"]["nodes"]:
            join(root_of(node["number"]), root_of(blocker["number"]))
    return {number: find(number) for number in group}


def board(nodes):
    """The open tasks as a tree: parts under their parent by number, roots grouped with related ones by lowest number."""
    superseded = decisions.superseded_in(nodes)
    items = {node["number"]: entry(node, superseded) for node in nodes}
    top = []
    for node in nodes:
        parent = (node["parent"] or {}).get("number")
        (items[parent]["tasks"] if parent in items else top).append(items[node["number"]])
    groups = related(nodes, [issue["number"] for issue in top])

    def order(issues):
        for issue in issues:
            issue["tasks"].sort(key=lambda task: task["number"])
            order(issue["tasks"])
    top.sort(key=lambda issue: (groups[issue["number"]], issue["number"]))
    order(top)
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
        out.append({**issue, "tasks": [], "guide": guide, "pad": pad, "home": home, "ancestors": ancestors})
    return out


def label(row):
    """A row's title line: its number, its title, `(in #n)` when it sits too deep for its parent's depth, and `(blocked by #a #b)` while a blocker
    is open. No-break spaces glue `(blocked by` to its first number, and the `)` ends the last number, so a wrap never leaves `(blocked` or a lone `)` on a line."""
    held = " (" + blocked_by(row["blockers"]).replace(" ", "\u00a0", 2) + ")" if blocked_by(row["blockers"]) else ""
    return f"#{row['number']} {row['title']}" + (f" (in #{row['home']})" if row["home"] else "") + held


def criterion(item):
    """A criterion's line: `[x]` or `[ ]` when a box marks it, its kind in parentheses, its name."""
    return " ".join(part for part in ("" if item["met"] is None else "[x]" if item["met"] else "[ ]", item["kind"] and f"({item['kind']})", item["name"]) if part)


def heading(row, width):
    """A row's lines the pane always shows, wrapped to WIDTH less its guide: `title`, `status`, and `notes`, with `struck` the indexes of the notes of a replaced decision; its open questions, owner decisions and, once every part is done, what keeps it open."""
    room = None if width is None else width - max(cells(row["guide"]), cells(row["pad"]))
    said = status(row)
    # parts share a line when they fit; else each takes its own
    shown = [said] if said and (room is None or cells(said) <= room) else [line for part in (row["progress"], row["holder"], row["wait"]) if part for line in wrap(part, room)]
    notes = [line for question in row.get("questions", []) for line in note("?", question, room)]
    struck = []
    for decided in row.get("decided", []):
        lines_of = note("◆", (f"[{decided['time']}] " if decided["time"] else "") + decided["decision"], room)
        struck += range(len(notes), len(notes) + len(lines_of)) if decided["struck"] else []
        notes += lines_of
    notes += note("◆", f"{row['more']} more decided", room) if row.get("more") else []
    notes += note("next step:", row["next"], room, limit=None) if row.get("next") else []  # the next step has no other place to be read in full
    # the first line sits after the guide, the later ones after the wider pad, so a title that fits beside its guide takes one line
    title = wrap(label(row), room, None if width is None else width - cells(row["guide"]))
    return {"title": title, "status": shown, "notes": notes, "struck": list(struck)}


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
        details = [row["goal"]] if row["goal"] else []
        details += ["see detail"] if row["detail"] else []
        details += [criterion(item) for item in row["done"]]
        details += [f"#{task['number']} {task['title']} closed{' stopped' * task['stopped']}" + (f" {blocked_by(task['blockers'])}" if blocked_by(task["blockers"]) else "") for task in row["closed"]]
        details += ["…"] if row["earlier"] else []
        yield from (row["pad"] + "  " + line for detail in details for line in wrap(detail, None if room is None else room - 2))


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
