"""The issue board: the board's issue nodes as a tree in the owner's reading order, and its text lines."""
import os
import re

import issue_state
import team_settings

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
    firsts = [(comment["body"] or "").replace("\r\n", "\n").split("\n\n")[0] for comment in comments]
    return next((" ".join(first.rsplit("next step:", 1)[1].split()) for first in reversed(firsts) if first.startswith("REPORTED:") and "next step:" in first), "")


def blockers_of(node):
    """Every issue that blocks this one, a landed one marked closed."""
    return [{"number": blocker["number"], "closed": blocker["state"] != "OPEN"} for blocker in (node.get("blockedBy") or {}).get("nodes", [])]


def entry(node):
    """One issue as the board shows it; a backlog shows its progress and summary, a task its goal and criteria."""
    every = blockers_of(node)
    blockers = [blocker["number"] for blocker in every if not blocker["closed"]]
    state = issue_state.compose({"body": node["body"], "trusted": node["trusted"], "comments": node["comments"]["nodes"]}, blockers)
    backlog = team_settings.load(os.getcwd())["backlog_label"] in [label["name"] for label in node["labels"]["nodes"]]
    holders = state["holders"] or []
    summary = node.get("subIssuesSummary") or {}
    closed = [{"number": task["number"], "title": issue_state.title(task), "url": task["url"], "blockers": blockers_of(task),
               "stopped": task.get("stateReason") in STOPPED} for task in (node.get("subIssues") or {}).get("nodes", []) if task["state"] == "CLOSED"]
    progress = (f"task {summary['completed']}/{summary['total']}" if summary.get("total")
                else "" if holders or state["waits"] == "deferred" else "not started") if backlog else ""
    return {"number": node["number"], "title": issue_state.title(node), "url": node["url"], "kind": "backlog" if backlog else "task",
            "holder": " ".join(holders), "wait": "" if blockers or state["waits"] == "held" or backlog and state["waits"] == "no holder" else state["waits"],
            "progress": progress, "goal": summary_of(node["body"]) if backlog else "", "detail": [] if backlog else state["goal"], "done": [] if backlog else state["done"],
            "next": next_step_of(node["comments"]["nodes"]) if backlog and summary.get("total", 0) == summary.get("completed", 0) else "",
            "urgency": URGENCY.index(state["waits"].split(" by ")[0]), "tasks": [],
            "blockers": every,
            "closed": closed[::-1][:SHOWN_CLOSED], "earlier": summary.get("completed", 0) > min(len(closed), SHOWN_CLOSED)}


def related(nodes, items):
    """{backlog: its group's lowest number}: backlogs whose issues name each other, or whose tasks block one another."""
    group = {number: number for number, issue in items.items() if issue["kind"] == "backlog"}

    def root(number):
        while group[number] != number:
            number = group[number]
        return number

    def join(first, second):
        if first in group and second in group:
            first, second = root(first), root(second)
            group[max(first, second)] = min(first, second)

    def backlog(number):
        node = by_number.get(number)
        while node and items[node["number"]]["kind"] != "backlog":
            node = by_number.get((node["parent"] or {}).get("number"))
        return node and node["number"]

    by_number = {node["number"]: node for node in nodes}
    for node in nodes:
        if node["number"] in group:
            for text in [node["body"]] + [comment["body"] for comment in node["comments"]["nodes"]]:
                for named in re.findall(r"#(\d+)\b", text or ""):
                    join(node["number"], int(named))
        for blocker in node["blockedBy"]["nodes"]:
            join(backlog(node["number"]), backlog(blocker["number"]))
    return {number: root(number) for number in group}


def board(nodes):
    """The open issues as a tree, backlogs grouped with related ones by lowest number, tasks by number."""
    items = {node["number"]: entry(node) for node in nodes}
    top = []
    for node in nodes:
        parent = (node["parent"] or {}).get("number")
        (items[parent]["tasks"] if parent in items else top).append(items[node["number"]])
    groups = related(nodes, items)

    def order(issues):
        for issue in issues:
            issue["tasks"].sort(key=lambda task: task["number"])
            order(issue["tasks"])
            del issue["urgency"]
    top.sort(key=lambda issue: (groups[issue["number"]], issue["number"]) if issue["number"] in groups else (float("inf"), issue["urgency"], issue["number"]))
    order(top)
    return top


def after(blockers):
    """What a task follows, every blocker, a landed one marked closed."""
    return "← " + ",".join(f"#{blocker['number']}{' closed' * blocker['closed']}" for blocker in blockers) if blockers else ""


def criterion(item):
    """A criterion's line: `[x]` or `[ ]` when a box marks it, its kind in parentheses, its name."""
    return " ".join(part for part in ("" if item["met"] is None else "[x]" if item["met"] else "[ ]", item["kind"] and f"({item['kind']})", item["name"]) if part)


def lines(issues, depth=0):
    """The board as text: each entry's link line, then indented what the pane shows under it."""
    for issue in issues:
        pad = "  " * (depth + 1)
        yield f"{'  ' * depth}#{issue['number']} {issue['title']}"
        status = " ".join(part for part in (issue["progress"], issue["holder"], issue["wait"], after(issue["blockers"])) if part)
        yield from ([f"{pad}{status}"] if status else [])
        yield from ([f"{pad}{issue['goal']}"] if issue["goal"] else [])
        yield from ([f"{pad}see detail"] if issue["detail"] else [])
        yield from (f"{pad}  {line.strip()}" for line in issue["detail"] if line.strip())
        for item in issue["done"]:
            yield f"{pad}  {criterion(item)}"
            yield from ([f"{pad}    {item['detail']}"] if item["detail"] else [])
        yield from ([f"{pad}next step: {issue['next']}"] if issue["next"] else [])
        yield from lines(issue["tasks"], depth + 1)
        yield from (f"{pad}#{task['number']} {task['title']} closed{' stopped' * task['stopped']}{' ' * bool(task['blockers'])}{after(task['blockers'])}" for task in issue["closed"])
        yield from ([f"{pad}…"] if issue["earlier"] else [])
