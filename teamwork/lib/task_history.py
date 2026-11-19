"""Past task durations: one row per closed task that holds no parts, read from the board or from a fixture file."""
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import board
import landing
import task_links
from session_gaps import parse_time

CRITERION = ("[check]", "[score]")


def own_repository():
    """The git directory of the repository this folder is in, the repository the board reads, as a board url names it."""
    found = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], capture_output=True, text=True)
    if found.returncode or not found.stdout.strip():
        raise RuntimeError("task_history: the board needs a git repository: run this inside a project's checkout")
    return os.path.realpath(found.stdout.strip())


def first_commit(repo, number):
    """When the pull request's first commit was authored, by the one commit its list starts with."""
    try:
        return landing.first_commit(number, repo)
    except LookupError as e:
        raise RuntimeError(f"task_history: {e}") from None


def fetch(repo):
    """Tasks in the fixture shape: number, labels (names), body, createdAt, closedAt, prStart or None."""
    found = board.tasks("all", repo=repo, pulls=True, comments=False)
    if found is None:
        raise RuntimeError("task_history: the tasks could not be read")
    closed = {task["number"] for task in found if not task["isPullRequest"] and task["state"] == "CLOSED"}
    # a pull request's closing keywords stand for GitHub's closing references; its first commit is one read each, so only for those that close a task
    closing = {pull["number"]: [number for number in map(int, landing.CLOSES.findall(pull["body"])) if number in closed] for pull in found if pull["mergedAt"]}
    with ThreadPoolExecutor(8) as pool:
        starts = dict(zip(closing, pool.map(lambda number: first_commit(repo, number) if closing[number] else None, closing)))
    first = {}  # task number -> earliest first-commit time of a merged pull request that closes it
    for number, start in starts.items():
        for ref in closing[number] if start else []:
            first[ref] = min(start, first.get(ref, start))
    return [{"number": task["number"], "labels": task["labels"], "body": task["body"], "createdAt": task["createdAt"],
             "closedAt": task["closedAt"], "prStart": first.get(task["number"])} for task in found if task["number"] in closed]


def rows(tasks):
    """A task starts at its pull request's first commit, else at its creation; each row names which."""
    out = []
    for task in tasks:
        if task_links.parts(task["body"]) or not task.get("closedAt"):
            continue
        source, start = ("pr", task["prStart"]) if task.get("prStart") else ("created", task["createdAt"])
        hours = (parse_time(task["closedAt"]) - parse_time(start)).total_seconds() / 3600
        out.append({"number": task["number"], "labels": task["labels"], "criteria": sum(task["body"].count(marker) for marker in CRITERION),
                    "start": start, "end": task["closedAt"], "hours": hours, "source": source})
    return sorted(out, key=lambda row: row["end"])
