"""A local board's records, whatever store keeps them: each issue is `<n>/issue.json` (title, labels, state, reason, times),
`<n>/body.md` and `<n>/comments/<k>.md`, oldest first. Every record is trusted, since only local users write the store.

A store (a `Store` subclass) knows how to keep files, never what they hold: `names(folder)` lists the names right under a folder ('' the top),
`load(path)` reads one, raising OSError when it is missing, `written(path)` says when it was written, `url(path)` names it, `refresh()` lets a
long-lived reader see later writes, and `keep(change)` runs `change()` once or more and keeps every file it staged, all at once.
`bind(store)` gives the board port's functions over that store, which a board adapter puts in its own namespace.
Links between issues live in their bodies only, as `task_links` reads them."""
import functools
import json
import os
import re
import shlex
from datetime import datetime, timezone

import task_links
import team_settings
import team_signal

USE = re.compile(r"use-board\.py\s+(file|comment|decide|edit|title|resolve|reopen|label)\b([^;&|\n]*)")
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


def record(store, number, comments=True, owners=None):
    """NUMBER's record; OWNERS, the parents by part from `owners(store)`, spares a read of every body when many records are read."""
    issue = meta(store, number)
    notes = [{"body": store.read(path), "url": f"{store.url(str(number))}#comment-{int(path.rsplit('/', 1)[1][:-3])}", "createdAt": stamp(store.written(path)), "trusted": True}
             for path in comment_paths(store, number)] if comments else []
    return {"number": number, "title": issue["title"], "body": store.read(f"{number}/body.md"), "url": store.url(str(number)), "state": issue["state"], "stateReason": issue["reason"],
            "createdAt": issue["createdAt"], "closedAt": issue["closedAt"], "trusted": True, "labels": issue["labels"], "parent": parent_of(store, number) if owners is None else owners.get(number), "isPullRequest": False,
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
    parents = owners(store)
    return [record(store, number, comments, parents) for number in reversed(numbers(store)) if keep(meta(store, number))]


def fresh(store, number, repo=None, comments=True):
    store.view()
    try:
        return record(store, int(number), comments)
    except (OSError, ValueError, KeyError):
        return None


def comments_since(store, since):
    store.view()
    parents = owners(store)
    return [(number, note) for number in numbers(store) for note in record(store, number, owners=parents)["comments"] if note["createdAt"] >= since]


def changed_since(store, stamp):
    store.view()
    return any(meta(store, number)["updatedAt"] >= stamp for number in numbers(store))


def owners(store):
    """{part: the issue whose body names it}, read in one pass over the bodies."""
    return {part: owner for owner in numbers(store) for part in task_links.parts(store.read(f"{owner}/body.md"))}


def parent_of(store, number):
    """The issue whose body names NUMBER as a part, else None."""
    return next((owner for owner in numbers(store) if int(number) in task_links.parts(store.read(f"{owner}/body.md"))), None)


def exists(store, number):
    try:
        return record(store, int(number), comments=False)
    except (OSError, ValueError, KeyError):
        return None


def blockers(store, number):
    store.view()
    return [target for target in task_links.depends(store.read(f"{number}/body.md")) if not ((found := exists(store, target)) and task_links.completed(found))]


def check_links(store, number, text):
    """Raises LookupError naming why TEXT cannot be NUMBER's body (None for an issue not yet filed)."""
    store.view()
    found = task_links.refusals(number and int(number), text, lambda n: exists(store, n), lambda n: parent_of(store, n))
    if found:
        raise LookupError(f"nothing written to #{number or 'a new issue'}: " + "; ".join(found))


def tree(store, project, nodes=None):
    """The open issues' nodes in the shape the issue pane draws, as GitHub's read gives them."""
    store.view()
    nodes = nodes if nodes is not None else [
        {**{k: issue[k] for k in ("number", "title", "url", "body")}, "labels": {"nodes": [{"name": name} for name in issue["labels"]]},
         "comments": {"nodes": [{"body": note["body"], "url": note["url"]} for note in issue["comments"]]}} for issue in reversed(issues(store, "open", project))]
    for node in nodes:
        node["trusted"] = True
        for item in node["comments"]["nodes"]:
            item["trusted"] = True
    return task_links.derive(nodes, lambda n: exists(store, n))


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
        check_links(store, None, body)
        number = max(numbers(store), default=0) + 1
        store.stage(f"{number}/body.md", body)  # before issue.json, so a reader that lists the issue finds its body
        save(store, number, title=title, labels=list(labels), state="OPEN", reason="", createdAt=stamp(), closedAt=None)
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
        check_links(store, number, text)
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
        "retitle", "label", "posted", "parent_of", "check_links")


def bind(store):
    """The board port's functions over STORE, with the store-free ones (`trusted`, `command`)."""
    here = globals()
    return {**{name: functools.partial(here[name], store) for name in PORT}, "trusted": trusted, "command": command}
