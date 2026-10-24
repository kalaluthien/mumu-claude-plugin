"""Past task durations: one row per closed non-backlog issue, read from the board or from a fixture file."""
from concurrent.futures import ThreadPoolExecutor

import board
import landing
from session_gaps import stamp

CRITERION = ("[check]", "[score]")


def first_commit(repo, number):
    """When the pull request's first commit was authored, by the one commit its list starts with."""
    try:
        return landing.first_commit(number, repo)
    except LookupError as e:
        raise RuntimeError(f"task_history: {e}") from None


def fetch(repo):
    """Issues in the fixture shape: number, labels (names), body, createdAt, closedAt, prStart or None."""
    found = board.issues("all", repo=repo, pulls=True, comments=False)
    if found is None:
        raise RuntimeError("task_history: the issues could not be read")
    closed = {i["number"] for i in found if not i["isPullRequest"] and i["state"] == "CLOSED"}
    # a pull request's closing keywords stand for GitHub's closing references; its first commit is one read each, so only for those that close a task
    closing = {i["number"]: [n for n in map(int, landing.CLOSES.findall(i["body"])) if n in closed] for i in found if i["mergedAt"]}
    with ThreadPoolExecutor(8) as pool:
        starts = dict(zip(closing, pool.map(lambda n: first_commit(repo, n) if closing[n] else None, closing)))
    first = {}  # issue number -> earliest first-commit time of a merged pull request that closes it
    for number, start in starts.items():
        for ref in closing[number] if start else []:
            first[ref] = min(start, first.get(ref, start))
    return [{"number": i["number"], "labels": [x["name"] for x in i["labels"]], "body": i["body"], "createdAt": i["createdAt"],
             "closedAt": i["closedAt"], "prStart": first.get(i["number"])} for i in found if i["number"] in closed]


def rows(issues):
    """A task starts at its pull request's first commit, else at its creation; each row names which."""
    out = []
    for i in issues:
        if "backlog" in i["labels"] or not i.get("closedAt"):
            continue
        source, start = ("pr", i["prStart"]) if i.get("prStart") else ("created", i["createdAt"])
        hours = (stamp(i["closedAt"]) - stamp(start)).total_seconds() / 3600
        out.append({"number": i["number"], "labels": i["labels"], "criteria": sum(i["body"].count(c) for c in CRITERION),
                    "start": start, "end": i["closedAt"], "hours": hours, "source": source})
    return sorted(out, key=lambda r: r["end"])
