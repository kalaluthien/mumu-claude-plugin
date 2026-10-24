"""The issue board: the board's issue nodes as a tree in the owner's reading order, and its text lines."""
import re

import issue_state

# an issue with no backlog group: what needs someone first, what is held last
# the latest closed tasks a backlog lists, newest first, an ellipsis below them when more landed before
SHOWN_CLOSED = 10
# close reasons of work stopped, not done; GitHub's duplicate close counts with them
STOPPED = ("NOT_PLANNED", "DUPLICATE")
URGENCY = ["waits on the owner", "waits on the manager", "no holder", "blocked", "held", "deferred"]


def summary_of(body):
    """A backlog's summary: its body's first paragraph, its lines joined, unless it is a heading."""
    first = (body or "").replace("\r\n", "\n").strip().split("\n\n")[0]
    return "" if first.startswith("#") else " ".join(line.strip() for line in first.splitlines() if line.strip())


def next_step_of(comments):
    """A backlog's next step: the latest `REPORTED:` that names one, so a backlog with nothing open says why it stays open."""
    firsts = [(c["body"] or "").replace("\r\n", "\n").split("\n\n")[0] for c in comments]
    return next((" ".join(f.rsplit("next step:", 1)[1].split()) for f in reversed(firsts) if f.startswith("REPORTED:") and "next step:" in f), "")


def blockers_of(node):
    """Every issue that blocks this one, a landed one marked closed."""
    return [{"number": b["number"], "closed": b["state"] != "OPEN"} for b in (node.get("blockedBy") or {}).get("nodes", [])]


def entry(node):
    """One issue as the board shows it; a backlog shows its progress and summary, a task its goal and criteria."""
    every = blockers_of(node)
    blockers = [b["number"] for b in every if not b["closed"]]
    state = issue_state.compose({"body": node["body"], "trusted": node["trusted"], "comments": node["comments"]["nodes"]}, blockers)
    backlog = "backlog" in [x["name"] for x in node["labels"]["nodes"]]
    holders = state["holders"] or []
    summary = node.get("subIssuesSummary") or {}
    closed = [{"number": t["number"], "title": t["title"], "url": t["url"], "blockers": blockers_of(t),
               "stopped": t.get("stateReason") in STOPPED} for t in (node.get("subIssues") or {}).get("nodes", []) if t["state"] == "CLOSED"]
    progress = (f"task {summary['completed']}/{summary['total']}" if summary.get("total")
                else "" if holders or state["waits"] == "deferred" else "not started") if backlog else ""
    return {"number": node["number"], "title": node["title"], "url": node["url"], "kind": "backlog" if backlog else "task",
            "holder": " ".join(holders), "wait": "" if blockers or state["waits"] == "held" or backlog and state["waits"] == "no holder" else state["waits"],
            "progress": progress, "goal": summary_of(node["body"]) if backlog else "", "detail": [] if backlog else state["goal"], "done": [] if backlog else state["done"],
            "next": next_step_of(node["comments"]["nodes"]) if backlog and summary.get("total", 0) == summary.get("completed", 0) else "",
            "urgency": URGENCY.index(state["waits"].split(" by ")[0]), "tasks": [],
            "blockers": every,
            "closed": closed[::-1][:SHOWN_CLOSED], "earlier": summary.get("completed", 0) > min(len(closed), SHOWN_CLOSED)}


def related(nodes, items):
    """{backlog: its group's lowest number}: backlogs whose issues name each other, or whose tasks block one another."""
    group = {n: n for n, i in items.items() if i["kind"] == "backlog"}

    def root(n):
        while group[n] != n:
            n = group[n]
        return n

    def join(a, b):
        if a in group and b in group:
            a, b = root(a), root(b)
            group[max(a, b)] = min(a, b)

    def backlog(n):
        node = by_number.get(n)
        while node and items[node["number"]]["kind"] != "backlog":
            node = by_number.get((node["parent"] or {}).get("number"))
        return node and node["number"]

    by_number = {i["number"]: i for i in nodes}
    for i in nodes:
        if i["number"] in group:
            for text in [i["body"]] + [c["body"] for c in i["comments"]["nodes"]]:
                for named in re.findall(r"#(\d+)\b", text or ""):
                    join(i["number"], int(named))
        for b in i["blockedBy"]["nodes"]:
            join(backlog(i["number"]), backlog(b["number"]))
    return {n: root(n) for n in group}


def board(nodes):
    """The open issues as a tree, backlogs grouped with related ones by lowest number, tasks by number."""
    items = {i["number"]: entry(i) for i in nodes}
    top = []
    for i in nodes:
        parent = (i["parent"] or {}).get("number")
        (items[parent]["tasks"] if parent in items else top).append(items[i["number"]])
    groups = related(nodes, items)

    def order(issues):
        for i in issues:
            i["tasks"].sort(key=lambda t: t["number"])
            order(i["tasks"])
            del i["urgency"]
    top.sort(key=lambda i: (groups[i["number"]], i["number"]) if i["number"] in groups else (float("inf"), i["urgency"], i["number"]))
    order(top)
    return top


def after(blockers):
    """What a task follows, every blocker, a landed one marked closed."""
    return "← " + ",".join(f"#{b['number']}{' closed' * b['closed']}" for b in blockers) if blockers else ""


def criterion(d):
    """A criterion's line: `[x]` or `[ ]` when a box marks it, its kind in parentheses, its name."""
    return " ".join(x for x in ("" if d["met"] is None else "[x]" if d["met"] else "[ ]", d["kind"] and f"({d['kind']})", d["name"]) if x)


def lines(issues, depth=0):
    """The board as text: each entry's link line, then indented what the pane shows under it."""
    for i in issues:
        pad = "  " * (depth + 1)
        yield f"{'  ' * depth}#{i['number']} {i['title']}"
        status = " ".join(x for x in (i["progress"], i["holder"], i["wait"], after(i["blockers"])) if x)
        yield from ([f"{pad}{status}"] if status else [])
        yield from ([f"{pad}{i['goal']}"] if i["goal"] else [])
        yield from ([f"{pad}see detail"] if i["detail"] else [])
        yield from (f"{pad}  {line.strip()}" for line in i["detail"] if line.strip())
        for d in i["done"]:
            yield f"{pad}  {criterion(d)}"
            yield from ([f"{pad}    {d['detail']}"] if d["detail"] else [])
        yield from ([f"{pad}next step: {i['next']}"] if i["next"] else [])
        yield from lines(i["tasks"], depth + 1)
        yield from (f"{pad}#{t['number']} {t['title']} closed{' stopped' * t['stopped']}{' ' * bool(t['blockers'])}{after(t['blockers'])}" for t in i["closed"])
        yield from ([f"{pad}…"] if i["earlier"] else [])
