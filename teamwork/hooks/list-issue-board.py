#!/usr/bin/env python3
"""usage: list-issue-board.py <project> [--json] | --nodes <file> [--json]

Print the project's open issues as the issue pane draws them: backlogs grouped with related ones, each task under its
backlog by urgency, an entry's link line then its holder and wait, a task's goal and criteria, a backlog's progress.
`--json` prints the same tree for the pane; `--nodes` reads GitHub's issue nodes from a file instead of GitHub."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import issue_board  # noqa: E402
from json_command import run  # noqa: E402

QUERY = """query($owner: String!, $name: String!, $labels: [String!]) {
  repository(owner: $owner, name: $name) {
    issues(states: OPEN, first: 100, labels: $labels, orderBy: {field: CREATED_AT, direction: ASC}) {
      nodes { number title url body parent { number } labels(first: 20) { nodes { name } } subIssuesSummary { total completed }
              blockedBy(first: 20) { nodes { number state } } comments(last: 100) { nodes { body url } } } } } }"""


def nodes(project):
    """The open issues' nodes, those labelled `scope:<project>` when that label exists, else all; None when a read failed."""
    repo = run("gh", "repo", "view", "--json", "owner,name")
    if repo is None:
        return None
    # gh prints nothing, not `[]`, when no label matches, so an empty read is a repository without that label
    scoped = f"scope:{project}" in [x["name"] for x in run("gh", "label", "list", "--search", f"scope:{project}", "--json", "name") or []]
    found = run("gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"owner={repo['owner']['login']}", "-f", f"name={repo['name']}",
                *(["-f", f"labels[]=scope:{project}"] if scoped else []))
    return found and found["data"]["repository"]["issues"]["nodes"]


read = json.loads(pathlib.Path(sys.argv[sys.argv.index("--nodes") + 1]).read_text()) if "--nodes" in sys.argv else nodes(sys.argv[1])
if read is None:
    sys.exit("list-issue-board: a GitHub read failed, so no board is shown")
tree = issue_board.board(read)
print(json.dumps(tree) if "--json" in sys.argv else "\n".join(issue_board.lines(tree)))
