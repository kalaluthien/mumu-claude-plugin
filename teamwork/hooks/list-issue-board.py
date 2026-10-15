#!/usr/bin/env python3
"""usage: list-issue-board.py <project> [--json]

Print the project's open issues, each task under its backlog: `<kind>#<n> <title>`, then indented its goal, its definition
of done as a list and its holder with any wait not about holding, as issue-grammar.md composes them. `--json` prints the
same tree for the issue pane to draw."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import issue_state  # noqa: E402
from json_command import run  # noqa: E402

QUERY = """query($owner: String!, $name: String!, $labels: [String!]) {
  repository(owner: $owner, name: $name) {
    issues(states: OPEN, first: 100, labels: $labels, orderBy: {field: CREATED_AT, direction: ASC}) {
      nodes { number title url body parent { number } labels(first: 20) { nodes { name } }
              blockedBy(first: 20) { nodes { number state } } comments(last: 100) { nodes { body url } } } } } }"""


def board(project):
    """The open issues as a tree: each {'number', 'title', 'url', 'kind', 'goal', 'done', 'holder', 'tasks'}; None when a read failed."""
    repo = run("gh", "repo", "view", "--json", "owner,name")
    scoped = run("gh", "label", "list", "--search", f"scope:{project}", "--json", "name")
    if repo is None or scoped is None:
        return None
    labels = [f"scope:{project}"] if f"scope:{project}" in [x["name"] for x in scoped] else []
    found = run("gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"owner={repo['owner']['login']}", "-f", f"name={repo['name']}",
                *(["-f", f"labels[]={labels[0]}"] if labels else []))
    if found is None:
        return None
    nodes = found["data"]["repository"]["issues"]["nodes"]
    items = {}
    for i in nodes:
        state = issue_state.compose({"body": i["body"], "comments": i["comments"]["nodes"]},
                                    [b["number"] for b in i["blockedBy"]["nodes"] if b["state"] == "OPEN"])
        kind = "backlog" if "backlog" in [x["name"] for x in i["labels"]["nodes"]] else "task"
        items[i["number"]] = {"number": i["number"], "title": i["title"], "url": i["url"], "kind": kind,
                              "goal": state["goal"], "done": state["done"], "holder": state["holder"], "tasks": []}
    top = []
    for i in nodes:
        parent = (i["parent"] or {}).get("number")
        (items[parent]["tasks"] if parent in items else top).append(items[i["number"]])
    return top


def lines(issues, depth=0):
    for i in issues:
        pad = "  " * (depth + 1)
        yield f"{'  ' * depth}{i['kind']}#{i['number']} {i['title']}"
        yield f"{pad}goal: {i['goal']}"
        yield f"{pad}definition-of-done:" if i["done"] else f"{pad}definition-of-done: none"
        yield from (f"{pad}  - {d}" for d in i["done"])
        yield f"{pad}holder: {i['holder']}"
        yield from lines(i["tasks"], depth + 1)


tree = board(sys.argv[1])
if tree is None:
    sys.exit("list-issue-board: a GitHub read failed, so no board is shown")
print(json.dumps(tree) if "--json" in sys.argv else "\n".join(lines(tree)))
