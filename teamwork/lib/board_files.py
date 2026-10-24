"""The board in plain files: each issue is a folder `<n>/` under `TEAMWORK_BOARD_DIR` holding `issue.json` (title, labels, state, parent, blockers, times),
`body.md` and `comments/<k>.md`, oldest first. Every record is trusted, since only local users write the folder."""
import json
import os
import pathlib
import re
import shlex
from datetime import datetime, timezone

import claude_config
import team_signal

DIR = pathlib.Path(os.environ.get("TEAMWORK_BOARD_DIR") or claude_config.folder() / "teamwork" / "board")
USE = re.compile(r"use-board\.py\s+(file|comment|decide|edit|resolve|order|nest|label)\b([^;&|\n]*)")
POSTED = re.compile(r"file://\S*?/(\d+)(?:#comment-(\d+))?(?=[\s\"\\]|$)")
trusted = lambda record: True

def stamp(seconds=None):
    return datetime.fromtimestamp(seconds or datetime.now().timestamp(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def numbers():
    return sorted(int(p.name) for p in DIR.glob("[0-9]*"))

def meta(number):
    return json.loads((DIR / str(number) / "issue.json").read_text())

def save(number, **change):
    """Writes NUMBER's changed fields, then touches the signal file, which a GitHub write gets from the issue pane."""
    old = meta(number) if change.get("createdAt") is None else {}  # a change to a missing issue raises, never makes the folder
    (DIR / str(number) / "issue.json").write_text(json.dumps({**old, **change, "updatedAt": stamp()}))
    team_signal.SIGNAL.parent.mkdir(parents=True, exist_ok=True)
    team_signal.SIGNAL.touch()

def record(number, comments=True):
    m, d = meta(number), DIR / str(number)
    notes = [{"body": p.read_text(), "url": f"file://{d}#comment-{int(p.stem)}", "createdAt": stamp(p.stat().st_mtime), "trusted": True}
             for p in sorted((d / "comments").glob("*.md"))] if comments else []
    return {"number": number, "title": m["title"], "body": (d / "body.md").read_text(), "url": f"file://{d}", "state": m["state"], "stateReason": m["reason"],
            "createdAt": m["createdAt"], "closedAt": m["closedAt"], "trusted": True, "labels": m["labels"], "parent": m["parent"], "isPullRequest": False,
            "mergedAt": None, "comments": notes}

def scoped(project):
    label = f"scope:{project}"
    return label if any(label in meta(n)["labels"] for n in numbers()) else None

def issues(state="open", project=None, pulls=False, comments=True, since=None, repo=None):
    """The issues newest first, those labelled `scope:<project>` when that label exists, updated since SINCE (an ISO time) when given."""
    label = project and scoped(project)
    keep = lambda m: state in ("all", m["state"].lower()) and (not label or label in m["labels"]) and (not since or m["updatedAt"] >= since)
    return [record(n, comments) for n in reversed(numbers()) if keep(meta(n))]

def fresh(number, repo=None, comments=True):
    try:
        return record(int(number), comments)
    except (OSError, ValueError):
        return None

def comments_since(since):
    return [(n, c) for n in numbers() for c in record(n)["comments"] if c["createdAt"] >= since]

def changed_since(stamp):
    return any(meta(n)["updatedAt"] >= stamp for n in numbers())

def blockers(number):
    return [b for b in meta(number)["blockers"] if meta(b)["state"] == "OPEN"]

def tree(project, nodes=None):
    """The open issues' nodes in the shape the issue pane draws, as GitHub's read gives them."""
    every = {n: meta(n) for n in numbers()}
    waits = lambda n: {"nodes": [{"number": b, "state": every[b]["state"]} for b in every[n]["blockers"]]}
    kids = lambda n: [c for c, m in every.items() if m["parent"] == n]
    nodes = nodes if nodes is not None else [
        {**{k: r[k] for k in ("number", "title", "url", "body")}, "parent": r["parent"] and {"number": r["parent"]}, "blockedBy": waits(r["number"]),
         "labels": {"nodes": [{"name": x} for x in r["labels"]]}, "comments": {"nodes": [{"body": c["body"], "url": c["url"]} for c in r["comments"]]},
         "subIssuesSummary": {"total": len(kids(r["number"])), "completed": sum(every[c]["state"] == "CLOSED" for c in kids(r["number"]))},
         "subIssues": {"nodes": [{"number": c, "title": every[c]["title"], "url": f"file://{DIR}/{c}", "state": every[c]["state"], "blockedBy": waits(c)}
                                 for c in kids(r["number"])][-50:]}} for r in reversed(issues("open", project))]
    for n in nodes:
        n["trusted"] = True
        for c in n["comments"]["nodes"]:
            c["trusted"] = True
    return nodes

def comment(number, text):
    """Adds TEXT as NUMBER's next comment; its url."""
    meta(number)  # raises when NUMBER does not exist
    folder = DIR / str(number) / "comments"
    folder.mkdir(exist_ok=True)
    k = len(list(folder.glob("*.md"))) + 1
    (folder / f"{k:04d}.md").write_text(text)
    save(number)
    return f"file://{DIR}/{number}#comment-{k}"

def file(title, body, labels) -> int:
    number = max(numbers(), default=0) + 1
    (DIR / str(number)).mkdir(parents=True)
    save(number, title=title, labels=list(labels), state="OPEN", reason="", parent=None, blockers=[], createdAt=stamp(), closedAt=None)
    (DIR / str(number) / "body.md").write_text(body)
    return number

def body(number):
    try:
        return (DIR / str(number) / "body.md").read_text()
    except OSError as e:
        raise LookupError(f"cannot read #{number} ({e.strerror}); check TEAMWORK_BOARD_DIR") from e

def edit(number, text):
    body(number)
    (DIR / str(number) / "body.md").write_text(text)
    save(number)

def resolve(number, summary, completed=True):
    comment(number, summary)
    save(number, state="CLOSED", reason="COMPLETED" if completed else "NOT_PLANNED", closedAt=stamp())

def order(later, earlier):
    meta(earlier)  # raises when it does not exist, before anything is written
    save(later, blockers=sorted({*meta(later)["blockers"], int(earlier)}))

def nest(backlog, task):
    meta(backlog)
    save(task, parent=int(backlog))

def label(number, name, remove=False):
    labels = [x for x in meta(number)["labels"] if x != name]
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
    return {"called": f"use-board.py {verb}", "write": "comment" if verb == "decide" else verb if verb in ("file", "comment", "resolve", "edit") else None,
            "title": len(args[0]) if verb == "file" and args else None, "inline body": False, "body edit": False,
            "body file": args[1] if verb in ("file", "comment", "decide") and len(args) > 1 else None}

def posted(output):
    """(url, body) of the first issue or comment url OUTPUT names, read back now; None when it names none."""
    found = POSTED.search(output)
    if not found:
        return None
    number, k = found.groups()
    path = DIR / number / "comments" / f"{int(k):04d}.md" if k else DIR / number / "body.md"
    return found.group(0), path.read_text() if path.exists() else ""
