"""A local board's records, whatever store keeps them: each issue is `<n>/issue.json` (title, labels, state, reason, parent, blockers, times),
`<n>/body.md` and `<n>/comments/<k>.md`, oldest first. Every record is trusted, since only local users write the store.

A store (a `Store` subclass) knows how to keep files, never what they hold: `names(folder)` lists the names right under a folder ('' the top),
`load(path)` reads one, raising OSError when it is missing, `written(path)` says when it was written, `url(path)` names it, `refresh()` lets a
long-lived reader see later writes, and `keep(change)` runs `change()` once or more and keeps every file it staged, all at once.
`bind(store)` gives the board port's functions over that store, which a board adapter puts in its own namespace."""
import functools
import json
import os
import re
import shlex
from datetime import datetime, timezone

import team_settings
import team_signal

USE = re.compile(r"use-board\.py\s+(file|comment|decide|edit|title|resolve|reopen|order|nest|label)\b([^;&|\n]*)")
POSTED = re.compile(r"(?:git\+)?file://\S*?/(\d+)(?:#comment-(\d+))?(?=[\s\"\\]|$)")
trusted = lambda record: True


class Store:
    """The writes staged by the change a store is keeping, which reads see first, so a change reads what it already wrote."""
    pending = None

    def read(self, path):
        if self.pending is not None and path in self.pending:
            return self.pending[path]
        return self.load(path)

    def children(self, folder=""):
        prefix = f"{folder}/" if folder else ""
        staged = {path[len(prefix):].split("/")[0] for path in self.pending or {} if path.startswith(prefix)}
        return sorted(set(self.names(folder)) | staged)

    def stage(self, path, text):
        self.pending[path] = text

    def write(self, change):
        """CHANGE's result, its staged files kept at once; a change made inside another, as resolve's comment, joins it."""
        if self.pending is not None:
            return change()
        result = self.keep(change)
        team_signal.SIGNAL.parent.mkdir(parents=True, exist_ok=True)
        team_signal.SIGNAL.touch()  # the issue pane rereads on it, as a GitHub write gets it from the pane
        return result

    def view(self):
        """Refreshes before a read, except inside a change, which reads the state it started from."""
        if self.pending is None:
            self.refresh()


def stamp(seconds=None):
    return datetime.fromtimestamp(seconds or datetime.now().timestamp(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def numbers(store):
    return sorted(int(name) for name in store.children() if name.isdigit())


def meta(store, number):
    return json.loads(store.read(f"{number}/issue.json"))


def save(store, number, **change):
    """Stages NUMBER's changed fields; a change to a missing issue raises, never makes it."""
    old = meta(store, number) if change.get("createdAt") is None else {}
    store.stage(f"{number}/issue.json", json.dumps({**old, **change, "updatedAt": stamp()}))


def comment_paths(store, number):
    return [f"{number}/comments/{name}" for name in store.children(f"{number}/comments") if name.endswith(".md")]


def record(store, number, comments=True):
    issue = meta(store, number)
    notes = [{"body": store.read(path), "url": f"{store.url(str(number))}#comment-{int(path.rsplit('/', 1)[1][:-3])}", "createdAt": stamp(store.written(path)), "trusted": True}
             for path in comment_paths(store, number)] if comments else []
    return {"number": number, "title": issue["title"], "body": store.read(f"{number}/body.md"), "url": store.url(str(number)), "state": issue["state"], "stateReason": issue["reason"],
            "createdAt": issue["createdAt"], "closedAt": issue["closedAt"], "trusted": True, "labels": issue["labels"], "parent": issue["parent"], "isPullRequest": False,
            "mergedAt": None, "comments": notes}


def scoped(store, project):
    store.view()
    label = team_settings.load(os.getcwd())["scope_prefix"] + project
    return label if any(label in meta(store, number)["labels"] for number in numbers(store)) else None


def issues(store, state="open", project=None, pulls=False, comments=True, since=None, repo=None):
    """The issues newest first, those labelled `scope:<project>` when that label exists, updated since SINCE (an ISO time) when given."""
    store.view()
    label = project and scoped(store, project)
    keep = lambda issue: state in ("all", issue["state"].lower()) and (not label or label in issue["labels"]) and (not since or issue["updatedAt"] >= since)
    return [record(store, number, comments) for number in reversed(numbers(store)) if keep(meta(store, number))]


def fresh(store, number, repo=None, comments=True):
    store.view()
    try:
        return record(store, int(number), comments)
    except (OSError, ValueError, KeyError):
        return None


def comments_since(store, since):
    store.view()
    return [(number, note) for number in numbers(store) for note in record(store, number)["comments"] if note["createdAt"] >= since]


def changed_since(store, stamp):
    store.view()
    return any(meta(store, number)["updatedAt"] >= stamp for number in numbers(store))


def blockers(store, number):
    store.view()
    return [blocker for blocker in meta(store, number)["blockers"] if meta(store, blocker)["state"] == "OPEN"]


def tree(store, project, nodes=None):
    """The open issues' nodes in the shape the issue pane draws, as GitHub's read gives them."""
    store.view()
    every = {number: meta(store, number) for number in numbers(store)}
    waits = lambda number: {"nodes": [{"number": blocker, "state": every[blocker]["state"]} for blocker in every[number]["blockers"]]}
    children = lambda number: [child for child, issue in every.items() if issue["parent"] == number]
    nodes = nodes if nodes is not None else [
        {**{k: issue[k] for k in ("number", "title", "url", "body")}, "parent": issue["parent"] and {"number": issue["parent"]}, "blockedBy": waits(issue["number"]),
         "labels": {"nodes": [{"name": name} for name in issue["labels"]]}, "comments": {"nodes": [{"body": note["body"], "url": note["url"]} for note in issue["comments"]]},
         "subIssuesSummary": {"total": len(children(issue["number"])), "completed": sum(every[child]["state"] == "CLOSED" for child in children(issue["number"]))},
         "subIssues": {"nodes": [{"number": child, "title": every[child]["title"], "url": store.url(str(child)), "state": every[child]["state"], "stateReason": every[child]["reason"] or None, "blockedBy": waits(child)}
                                 for child in children(issue["number"])][-50:]}} for issue in reversed(issues(store, "open", project))]
    for node in nodes:
        node["trusted"] = True
        for item in node["comments"]["nodes"] + (node.get("subIssues") or {}).get("nodes", []):
            item["trusted"] = True
    return nodes


def comment(store, number, text):
    """Adds TEXT as NUMBER's next comment; its url."""
    def change():
        meta(store, number)  # raises when NUMBER does not exist
        position = len(comment_paths(store, number)) + 1
        store.stage(f"{number}/comments/{position:04d}.md", text)
        save(store, number)
        return f"{store.url(str(number))}#comment-{position}"
    return store.write(change)


def file(store, title, body, labels) -> int:
    def change():
        number = max(numbers(store), default=0) + 1
        store.stage(f"{number}/body.md", body)  # before issue.json, so a reader that lists the issue finds its body
        save(store, number, title=title, labels=list(labels), state="OPEN", reason="", parent=None, blockers=[], createdAt=stamp(), closedAt=None)
        return number
    return store.write(change)


def body(store, number):
    store.view()
    try:
        return store.read(f"{number}/body.md")
    except OSError as e:
        raise LookupError(f"cannot read #{number} ({e.strerror or e}); check the board setting") from e


def edit(store, number, text):
    def change():
        body(store, number)
        store.stage(f"{number}/body.md", text)
        save(store, number)
    store.write(change)


def resolve(store, number, summary, completed=True):
    def change():
        comment(store, number, summary)
        save(store, number, state="CLOSED", reason="COMPLETED" if completed else "NOT_PLANNED", closedAt=stamp())
    store.write(change)


def reopen(store, number):
    """Opens NUMBER again; an open one stays as it is, as GitHub leaves it."""
    def change():
        if meta(store, number)["state"] == "CLOSED":
            save(store, number, state="OPEN", reason="REOPENED", closedAt=None)
    store.write(change)


def retitle(store, number, title):
    store.write(lambda: save(store, number, title=title))


# each refusal below is one GitHub answers with 422 or 404, so a local board accepts only what GitHub accepts
def order(store, later, earlier):
    def change():
        meta(store, earlier)  # raises when it does not exist, before anything is written
        if int(later) == int(earlier) or int(earlier) in meta(store, later)["blockers"]:
            raise LookupError(f"#{later} already waits on #{earlier}, or is #{earlier}")
        save(store, later, blockers=sorted([*meta(store, later)["blockers"], int(earlier)]))
    store.write(change)


def nest(store, backlog, task):
    def change():
        meta(store, backlog)
        if int(backlog) == int(task) or meta(store, task)["parent"]:
            raise LookupError(f"#{task} already has a parent, or is #{backlog}")
        save(store, task, parent=int(backlog))
    store.write(change)


def label(store, number, name, remove=False):
    def change():
        labels = [existing for existing in meta(store, number)["labels"] if existing != name]
        if remove and len(labels) == len(meta(store, number)["labels"]):
            raise LookupError(f"#{number} has no label {name}")
        save(store, number, labels=labels if remove else [*labels, name])
    store.write(change)


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


def posted(store, output):
    """(url, body) of the first issue or comment url OUTPUT names, read back now; None when it names none."""
    found = POSTED.search(output)
    if not found:
        return None
    store.view()
    number, position = found.groups()
    try:
        return found.group(0), store.read(f"{number}/comments/{int(position):04d}.md" if position else f"{number}/body.md")
    except OSError:
        return found.group(0), ""


PORT = ("issues", "fresh", "comments_since", "changed_since", "blockers", "scoped", "tree", "comment", "file", "body", "edit", "resolve", "reopen",
        "retitle", "order", "nest", "label", "posted")


def bind(store):
    """The board port's functions over STORE, with the store-free ones (`trusted`, `command`)."""
    here = globals()
    return {**{name: functools.partial(here[name], store) for name in PORT}, "trusted": trusted, "command": command}
