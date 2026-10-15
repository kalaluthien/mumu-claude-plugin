"""The issue board: GitHub issue nodes as a tree in the owner's reading order, and its text lines."""
import re

import issue_state

# a task under its backlog: what needs someone first, what is held last
URGENCY = ["waits on the owner", "waits on the manager", "no holder", "blocked", "held", "deferred"]


def summary_of(body):
    """A backlog's summary: its body's first paragraph, its lines joined, unless it is a heading."""
    first = (body or "").replace("\r\n", "\n").strip().split("\n\n")[0]
    return "" if first.startswith("#") else " ".join(line.strip() for line in first.splitlines() if line.strip())


def next_step_of(comments):
    """A backlog's next step: the latest `REPORTED:` that names one, so a backlog with nothing open says why it stays open."""
    for c in reversed(comments):
        first = (c["body"] or "").replace("\r\n", "\n").split("\n\n")[0]
        if first.startswith("REPORTED:") and "next step:" in first:
            return " ".join(first.rsplit("next step:", 1)[1].split())
    return ""


def entry(node):
    """One issue as the board shows it; a backlog shows its progress and summary, a task its goal and criteria."""
    blockers = [b["number"] for b in node["blockedBy"]["nodes"] if b["state"] == "OPEN"]
    state = issue_state.compose({"body": node["body"], "comments": node["comments"]["nodes"]}, blockers)
    backlog = "backlog" in [x["name"] for x in node["labels"]["nodes"]]
    holders = state["holders"] or []
    summary = node.get("subIssuesSummary") or {}
    progress = (f"{summary['total'] - summary['completed']} open, {summary['completed']} landed" if summary.get("total")
                else "" if holders or state["waits"] == "deferred" else "not started") if backlog else ""
    idle = backlog and summary.get("total", 0) == summary.get("completed", 0)
    return {"number": node["number"], "title": node["title"], "url": node["url"], "kind": "backlog" if backlog else "task",
            "holder": " ".join(holders), "wait": "←" + ",".join(f"#{n}" for n in blockers) if blockers else "" if state["waits"] == "held" or backlog and state["waits"] == "no holder" else state["waits"],
            "progress": progress, "goal": summary_of(node["body"]) if backlog else state["goal"], "done": [] if backlog else state["done"],
            "next": next_step_of(node["comments"]["nodes"]) if idle else "",
            "urgency": URGENCY.index(state["waits"].split(" by ")[0]), "tasks": [], "blockers": blockers, "layer": 0,
            "closed": [{"number": t["number"], "title": t["title"], "url": t["url"]}
                       for t in (node.get("subIssues") or {}).get("nodes", []) if t["state"] == "CLOSED"]}


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


def plan(tasks):
    """The tasks in layers: a task's layer is one below its deepest open sibling blocker, so one layer can run at once;
    within a layer the given order. A cycle is cut where it is met."""
    left, layer = list(tasks), {}
    while left:
        waiting = {t["number"] for t in left}
        ready = next((t for t in left if not waiting & set(t["blockers"])), left[0])
        left.remove(ready)
        ready["layer"] = layer[ready["number"]] = 1 + max([layer[b] for b in ready["blockers"] if b in layer], default=-1)
    return sorted(tasks, key=lambda t: t["layer"])


def board(nodes):
    """The open issues as a tree, backlogs grouped with related ones by lowest number, tasks by urgency, then number, each after its open blockers."""
    items = {i["number"]: entry(i) for i in nodes}
    top = []
    for i in nodes:
        parent = (i["parent"] or {}).get("number")
        (items[parent]["tasks"] if parent in items else top).append(items[i["number"]])
    groups = related(nodes, items)

    def order(issues):
        for i in issues:
            i["tasks"] = plan(sorted(i["tasks"], key=lambda t: (t["urgency"], t["number"])))
            order(i["tasks"])
            del i["urgency"]
    top.sort(key=lambda i: (groups[i["number"]], i["number"]) if i["number"] in groups else (float("inf"), i["urgency"], i["number"]))
    order(top)
    return top


def lines(issues, depth=0):
    """The board as text: each entry's link line, then indented what the pane shows under it."""
    for i in issues:
        depth_here = depth + i["layer"]
        pad = "  " * (depth_here + 1)
        yield f"{'  ' * depth_here}#{i['number']} {i['title']}"
        status = " ".join(x for x in (i["progress"], i["holder"], i["wait"]) if x)
        yield from ([f"{pad}{status}"] if status else [])
        yield from ([f"{pad}{i['goal']}"] if i["goal"] else [])
        yield from (f"{pad}- {d}" for d in i["done"])
        yield from ([f"{pad}next step: {i['next']}"] if i["next"] else [])
        yield from lines(i["tasks"], depth_here + 1)
        yield from (f"{pad}#{t['number']} {t['title']} closed" for t in i["closed"])
