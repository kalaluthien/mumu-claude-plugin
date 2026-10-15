"""Past task durations: one row per closed non-backlog issue, read from GitHub or from a fixture file."""
import json
import subprocess
from datetime import datetime

CRITERION = ("[check]", "[score]")


def gh_json(*args):
    return json.loads(subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout)


def fetch(repo):
    """Issues in the fixture shape: number, labels (names), body, createdAt, closedAt, prStart or None."""
    issues = gh_json("issue", "list", "-R", repo, "--state", "closed", "--limit", "1000",
                     "--json", "number,labels,body,createdAt,closedAt")
    owner, name = repo.split("/")
    query = """query($owner: String!, $name: String!, $endCursor: String) {
      repository(owner: $owner, name: $name) { pullRequests(states: MERGED, first: 100, after: $endCursor) {
        pageInfo { hasNextPage endCursor }
        nodes { commits(first: 1) { nodes { commit { authoredDate } } } closingIssuesReferences(first: 20) { nodes { number } } }
      } } }"""
    out = subprocess.run(["gh", "api", "graphql", "--paginate", "-F", f"owner={owner}", "-F", f"name={name}", "-f", f"query={query}",
                          "--jq", ".data.repository.pullRequests.nodes[]"], capture_output=True, text=True, check=True).stdout
    first = {}  # issue number -> earliest first-commit time of a merged pull request that closes it
    for line in out.splitlines():
        pr = json.loads(line)
        if not pr["commits"]["nodes"]:
            continue
        start = pr["commits"]["nodes"][0]["commit"]["authoredDate"]
        for ref in pr["closingIssuesReferences"]["nodes"]:
            first[ref["number"]] = min(start, first.get(ref["number"], start))
    return [{**i, "labels": [x["name"] for x in i["labels"]], "prStart": first.get(i["number"])} for i in issues]


def rows(issues):
    """A task starts at its pull request's first commit, else at its creation; each row names which."""
    out = []
    for i in issues:
        if "backlog" in i["labels"] or not i.get("closedAt"):
            continue
        source, start = ("pr", i["prStart"]) if i.get("prStart") else ("created", i["createdAt"])
        hours = (datetime.fromisoformat(i["closedAt"]) - datetime.fromisoformat(start)).total_seconds() / 3600
        out.append({"number": i["number"], "labels": i["labels"], "criteria": sum(i["body"].count(c) for c in CRITERION),
                    "start": start, "end": i["closedAt"], "hours": hours, "source": source})
    return sorted(out, key=lambda r: r["end"])
