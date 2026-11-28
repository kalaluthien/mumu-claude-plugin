"""Past task durations: one row per closed task that holds no parts, read from the board or from a fixture file."""
import os

import board
import data_folder
import task_links
from session_gaps import parse_time

CRITERION = ("[check]", "[score]")


def own_repository():
    """The git directory of the repository this folder is in, the repository the board reads, as a board url names it."""
    found = data_folder.common_folder()
    if found is None:
        raise RuntimeError("task_history: the board needs a git repository: run this inside a project's checkout")
    return os.path.realpath(found)


def fetch():
    """The board's closed tasks in the fixture shape: number, labels (names), body, createdAt, closedAt."""
    found = board.tasks("closed", comments=False)
    if found is None:
        raise RuntimeError("task_history: the tasks could not be read")
    return [{key: task[key] for key in ("number", "labels", "body", "createdAt", "closedAt")} for task in found]


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
