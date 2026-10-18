#!/usr/bin/env python3
"""usage: list-issue-board.py <project> [--json] | --nodes <file> [--json]

Print the project's open issues as the issue pane draws them: backlogs grouped with related ones, each task under its
backlog by number, an entry's link line then its holder and wait, a task's goal and criteria, a backlog's progress and its closed tasks.
`--json` prints the same tree for the pane; `--nodes` reads GitHub's issue nodes from a file instead of GitHub."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import issue_board  # noqa: E402
from github_issues import scope_label  # noqa: E402
from json_command import run  # noqa: E402

# one point or two per read: GitHub charges each connection a node is asked for, so the sub-issues' blockers, the costliest part,
# are read only for the closed ones the board shows, by the second query
ISSUES = """query($owner: String!, $name: String!, $labels: [String!], $after: String) {
  repository(owner: $owner, name: $name) {
    issues(states: OPEN, first: 30, after: $after, labels: $labels, orderBy: {field: CREATED_AT, direction: ASC}) {
      nodes { number title url body authorAssociation parent { number } labels(first: 20) { nodes { name } } subIssuesSummary { total completed }
              subIssues(last: 50) { nodes { number title url state } }
              blockedBy(first: 20) { nodes { number state } } comments(last: 100) { nodes { body url authorAssociation } } }
      pageInfo { hasNextPage endCursor } } } }"""
BLOCKERS = """query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    %s } }"""


def graphql(query, owner, name, *fields):
    found = run("gh", "api", "graphql", "-f", f"query={query}", "-f", f"owner={owner}", "-f", f"name={name}", *fields)
    return found and found["data"]["repository"]


def nodes(project):
    """The open issues' nodes, those labelled `scope:<project>` when that label exists, else all; None when a read failed."""
    repo = run("gh", "api", "repos/{owner}/{repo}", "--jq", "{owner: .owner.login, name: .name}")
    if repo is None:
        return None
    label = scope_label(project)
    scope = ["-f", f"labels[]={label}"] if label else []
    issues, after = [], []
    while True:  # a page is one point, so a project of more than 30 open issues pays one more per 30
        found = graphql(ISSUES, repo["owner"], repo["name"], *scope, *after)
        if found is None:
            return None
        issues += found["issues"]["nodes"]
        if not found["issues"]["pageInfo"]["hasNextPage"]:
            break
        after = ["-f", f"after={found['issues']['pageInfo']['endCursor']}"]
    shown = [t for n in issues for t in [t for t in n["subIssues"]["nodes"] if t["state"] == "CLOSED"][-issue_board.SHOWN_CLOSED:]]
    if shown:
        asked = graphql(BLOCKERS % " ".join(f"i{k}: issue(number: {k}) {{ blockedBy(first: 20) {{ nodes {{ number state }} }} }}" for k in {t["number"] for t in shown}),
                        repo["owner"], repo["name"])
        if asked is None:
            return None
        for t in shown:
            t["blockedBy"] = asked[f"i{t['number']}"]["blockedBy"]
    return issues


read = json.loads(pathlib.Path(sys.argv[sys.argv.index("--nodes") + 1]).read_text()) if "--nodes" in sys.argv else nodes(sys.argv[1])
if read is None:
    sys.exit("list-issue-board: a GitHub read failed, so no board is shown")
tree = issue_board.board(read)
print(json.dumps(tree) if "--json" in sys.argv else "\n".join(issue_board.lines(tree)))
