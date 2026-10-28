"""Past task durations: one row per closed non-backlog issue, read from the board or from a fixture file."""
import os
from concurrent.futures import ThreadPoolExecutor

import board
import landing
import team_settings
from session_gaps import parse_time

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
    closed = {issue["number"] for issue in found if not issue["isPullRequest"] and issue["state"] == "CLOSED"}
    # a pull request's closing keywords stand for GitHub's closing references; its first commit is one read each, so only for those that close a task
    closing = {pull["number"]: [number for number in map(int, landing.CLOSES.findall(pull["body"])) if number in closed] for pull in found if pull["mergedAt"]}
    with ThreadPoolExecutor(8) as pool:
        starts = dict(zip(closing, pool.map(lambda number: first_commit(repo, number) if closing[number] else None, closing)))
    first = {}  # issue number -> earliest first-commit time of a merged pull request that closes it
    for number, start in starts.items():
        for ref in closing[number] if start else []:
            first[ref] = min(start, first.get(ref, start))
    return [{"number": issue["number"], "labels": issue["labels"], "body": issue["body"], "createdAt": issue["createdAt"],
             "closedAt": issue["closedAt"], "prStart": first.get(issue["number"])} for issue in found if issue["number"] in closed]


def rows(issues):
    """A task starts at its pull request's first commit, else at its creation; each row names which."""
    out, backlog = [], team_settings.load(os.getcwd())["backlog_label"]
    for issue in issues:
        if backlog in issue["labels"] or not issue.get("closedAt"):
            continue
        source, start = ("pr", issue["prStart"]) if issue.get("prStart") else ("created", issue["createdAt"])
        hours = (parse_time(issue["closedAt"]) - parse_time(start)).total_seconds() / 3600
        out.append({"number": issue["number"], "labels": issue["labels"], "criteria": sum(issue["body"].count(marker) for marker in CRITERION),
                    "start": start, "end": issue["closedAt"], "hours": hours, "source": source})
    return sorted(out, key=lambda row: row["end"])
