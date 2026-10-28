"""The board in plain files: each issue is a folder `<n>/` under `TEAMWORK_BOARD_DIR` holding `issue.json` (title, labels, state, parent, blockers, times),
`body.md` and `comments/<k>.md`, oldest first. Every record is trusted, since only local users write the folder."""
import json
import os
import pathlib
import re
import shlex
from datetime import datetime, timezone

import claude_config
import data_folder
import team_settings
import team_signal


def default_folder():
    """The main checkout's `.teamwork/board`, the same for every worktree of a project and never committed; outside a repository, or with no git, the Claude config folder's."""
    return data_folder.folder("board") or claude_config.folder() / "teamwork" / "board"

FOLDER = pathlib.Path(os.environ.get("TEAMWORK_BOARD_DIR") or default_folder())
USE = re.compile(r"use-board\.py\s+(file|comment|decide|edit|title|resolve|reopen|order|nest|label)\b([^;&|\n]*)")
POSTED = re.compile(r"file://\S*?/(\d+)(?:#comment-(\d+))?(?=[\s\"\\]|$)")
trusted = lambda record: True

def stamp(seconds=None):
    return datetime.fromtimestamp(seconds or datetime.now().timestamp(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def numbers():
    return sorted(int(path.name) for path in FOLDER.glob("[0-9]*"))

def meta(number):
    return json.loads((FOLDER / str(number) / "issue.json").read_text())

def save(number, **change):
    """Writes NUMBER's changed fields, then touches the signal file, which a GitHub write gets from the issue pane."""
    old = meta(number) if change.get("createdAt") is None else {}  # a change to a missing issue raises, never makes the folder
    (FOLDER / str(number) / "issue.json").write_text(json.dumps({**old, **change, "updatedAt": stamp()}))
    team_signal.SIGNAL.parent.mkdir(parents=True, exist_ok=True)
    team_signal.SIGNAL.touch()

def record(number, comments=True):
    issue, folder = meta(number), FOLDER / str(number)
    notes = [{"body": path.read_text(), "url": f"file://{folder}#comment-{int(path.stem)}", "createdAt": stamp(path.stat().st_mtime), "trusted": True}
             for path in sorted((folder / "comments").glob("*.md"))] if comments else []
    return {"number": number, "title": issue["title"], "body": (folder / "body.md").read_text(), "url": f"file://{folder}", "state": issue["state"], "stateReason": issue["reason"],
            "createdAt": issue["createdAt"], "closedAt": issue["closedAt"], "trusted": True, "labels": issue["labels"], "parent": issue["parent"], "isPullRequest": False,
            "mergedAt": None, "comments": notes}

def scoped(project):
    label = team_settings.load(os.getcwd())["scope_prefix"] + project
    return label if any(label in meta(number)["labels"] for number in numbers()) else None

def issues(state="open", project=None, pulls=False, comments=True, since=None, repo=None):
    """The issues newest first, those labelled `scope:<project>` when that label exists, updated since SINCE (an ISO time) when given."""
    label = project and scoped(project)
    keep = lambda issue: state in ("all", issue["state"].lower()) and (not label or label in issue["labels"]) and (not since or issue["updatedAt"] >= since)
    return [record(number, comments) for number in reversed(numbers()) if keep(meta(number))]

def fresh(number, repo=None, comments=True):
    try:
        return record(int(number), comments)
    except (OSError, ValueError):
        return None

def comments_since(since):
    return [(number, note) for number in numbers() for note in record(number)["comments"] if note["createdAt"] >= since]

def changed_since(stamp):
    return any(meta(number)["updatedAt"] >= stamp for number in numbers())

def blockers(number):
    return [blocker for blocker in meta(number)["blockers"] if meta(blocker)["state"] == "OPEN"]

def tree(project, nodes=None):
    """The open issues' nodes in the shape the issue pane draws, as GitHub's read gives them."""
    every = {number: meta(number) for number in numbers()}
    waits = lambda number: {"nodes": [{"number": blocker, "state": every[blocker]["state"]} for blocker in every[number]["blockers"]]}
    children = lambda number: [child for child, issue in every.items() if issue["parent"] == number]
    nodes = nodes if nodes is not None else [
        {**{k: issue[k] for k in ("number", "title", "url", "body")}, "parent": issue["parent"] and {"number": issue["parent"]}, "blockedBy": waits(issue["number"]),
         "labels": {"nodes": [{"name": name} for name in issue["labels"]]}, "comments": {"nodes": [{"body": note["body"], "url": note["url"]} for note in issue["comments"]]},
         "subIssuesSummary": {"total": len(children(issue["number"])), "completed": sum(every[child]["state"] == "CLOSED" for child in children(issue["number"]))},
         "subIssues": {"nodes": [{"number": child, "title": every[child]["title"], "url": f"file://{FOLDER}/{child}", "state": every[child]["state"], "stateReason": every[child]["reason"] or None, "blockedBy": waits(child)}
                                 for child in children(issue["number"])][-50:]}} for issue in reversed(issues("open", project))]
    for node in nodes:
        node["trusted"] = True
        for item in node["comments"]["nodes"] + (node.get("subIssues") or {}).get("nodes", []):
            item["trusted"] = True
    return nodes

def comment(number, text):
    """Adds TEXT as NUMBER's next comment; its url."""
    meta(number)  # raises when NUMBER does not exist
    folder = FOLDER / str(number) / "comments"
    folder.mkdir(exist_ok=True)
    position = len(list(folder.glob("*.md"))) + 1
    (folder / f"{position:04d}.md").write_text(text)
    save(number)
    return f"file://{FOLDER}/{number}#comment-{position}"

def file(title, body, labels) -> int:
    number = max(numbers(), default=0) + 1
    (FOLDER / str(number)).mkdir(parents=True)
    save(number, title=title, labels=list(labels), state="OPEN", reason="", parent=None, blockers=[], createdAt=stamp(), closedAt=None)
    (FOLDER / str(number) / "body.md").write_text(body)
    return number

def body(number):
    try:
        return (FOLDER / str(number) / "body.md").read_text()
    except OSError as e:
        raise LookupError(f"cannot read #{number} ({e.strerror}); check TEAMWORK_BOARD_DIR") from e

def edit(number, text):
    body(number)
    (FOLDER / str(number) / "body.md").write_text(text)
    save(number)

def resolve(number, summary, completed=True):
    comment(number, summary)
    save(number, state="CLOSED", reason="COMPLETED" if completed else "NOT_PLANNED", closedAt=stamp())

def reopen(number):
    """Opens NUMBER again; an open one stays as it is, as GitHub leaves it."""
    if meta(number)["state"] == "CLOSED":
        save(number, state="OPEN", reason="REOPENED", closedAt=None)

def retitle(number, title):
    save(number, title=title)

# each refusal below is one GitHub answers with 422 or 404, so a files board accepts only what GitHub accepts
def order(later, earlier):
    meta(earlier)  # raises when it does not exist, before anything is written
    if int(later) == int(earlier) or int(earlier) in meta(later)["blockers"]:
        raise LookupError(f"#{later} already waits on #{earlier}, or is #{earlier}")
    save(later, blockers=sorted([*meta(later)["blockers"], int(earlier)]))

def nest(backlog, task):
    meta(backlog)
    if int(backlog) == int(task) or meta(task)["parent"]:
        raise LookupError(f"#{task} already has a parent, or is #{backlog}")
    save(task, parent=int(backlog))

def label(number, name, remove=False):
    labels = [existing for existing in meta(number)["labels"] if existing != name]
    if remove and len(labels) == len(meta(number)["labels"]):
        raise LookupError(f"#{number} has no label {name}")
    save(number, labels=labels if remove else [*labels, name])

def command(text):
    """The `use-board.py` write TEXT runs, as the fields route-event reads; None when it runs none."""
    found = USE.search(text)
    if not found:
        return None
    verb, rest = found.groups()
    try:
        args = shlex.split(rest)
    except ValueError:
        args = []
    return {"called": f"use-board.py {verb}", "write": {"decide": "comment", "title": "edit"}.get(verb, verb if verb in ("file", "comment", "resolve", "edit") else None),
            "title": len(args[0]) if verb == "file" and args else len(args[1]) if verb == "title" and len(args) > 1 else None, "inline body": False, "body edit": False,
            "body file": args[1] if verb in ("file", "comment", "decide") and len(args) > 1 else None}

def posted(output):
    """(url, body) of the first issue or comment url OUTPUT names, read back now; None when it names none."""
    found = POSTED.search(output)
    if not found:
        return None
    number, position = found.groups()
    path = FOLDER / number / "comments" / f"{int(position):04d}.md" if position else FOLDER / number / "body.md"
    return found.group(0), path.read_text() if path.exists() else ""
