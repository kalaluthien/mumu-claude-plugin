"""A local board's records, whatever store keeps them: each issue is a folder `<scope>/<n>/` (`<n>/` at the repository root) holding `issue.json`
(title, labels, state, reason, times, and `depends`, the numbers of the tasks it waits on), `body.md` and `comments/<k>.json`, oldest first, each as board-record-schema.json says, a comment written before that schema a `comments/<k>.md` of text alone, where `<scope>` is the folder of the repository the issue belongs to; `commentTimes` in `issue.json`, when a copy set it, holds the first comments' times. Every record is trusted, since only local users write the store.

A store (a `Store` subclass) knows how to keep files, never what they hold: `names(folder)` lists the names right under a folder ('' the top),
`homes()` says the folder of each issue number (a store may cache it),
`load(path)` reads one, raising OSError when it is missing, `written(path)` says when it was written, `url(path)` names it, `refresh()` lets a
long-lived reader see later writes, and `keep(change)` runs `change()` once or more and keeps every file it staged, all at once.
`bind(store)` gives the board port's functions over that store, which a board adapter puts in its own namespace.
A task's parts live in its body, as `task_links` reads them."""
import functools
import json
import re

import board_scope
import iso_time
import issue_state
import task_links
import team_signal

USE = re.compile(r"use-board\.py\s+(file|comment|decide|hold|depend|edit|title|resolve|reopen|label)\b")
FLOOR = "floor"  # a file at the board's top holding the number a copied board's newest issue or pull request had, so no new issue reuses one
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

    def homes(self):
        """{issue number: its scope folder}, found by walking `names`; a store that can keep it between reads overrides this."""
        found = {}

        def walk(folder):
            for name in self.names(folder):
                path = f"{folder}/{name}" if folder else name
                if name.isdigit():
                    if "issue.json" in self.names(path):
                        found.setdefault(int(name), folder)
                else:
                    walk(path)
        walk("")
        return found

    def staged(self):
        """{issue number: scope folder} of the issues the running change has written so far."""
        found = {}
        for path in self.pending or ():
            parts = path.split("/")
            if len(parts) >= 2 and parts[-2].isdigit() and parts[-1] in ("issue.json", "body.md"):
                found[int(parts[-2])] = "/".join(parts[:-2])
        return found

    def place(self, number):
        """NUMBER's scope folder, or None when no issue has that number."""
        return self.staged().get(number, self.homes().get(number))

    def write(self, change):
        """CHANGE's result, its staged files kept at once; a change made inside another, as resolve's comment, joins it."""
        if self.pending is not None:
            return change()
        result = self.keep(change)
        team_signal.touch()  # the issue pane rereads on it
        return result

    def view(self):
        """Refreshes before a read, except inside a change, which reads the state it started from."""
        if self.pending is None:
            self.refresh()


def numbers(store):
    return sorted({*store.homes(), *store.staged()})


def home(store, number):
    """NUMBER's record folder, `teamwork/1213`, or `1213` at the repository root; FileNotFoundError when no issue has that number."""
    folder = store.place(int(number))
    if folder is None:
        raise FileNotFoundError(f"no issue #{number}")
    return f"{folder}/{int(number)}" if folder else str(int(number))


def next_number(store):
    """The number a new issue takes: one above the highest issue, or above the floor a copy of another board left, if that is higher."""
    try:
        floor = int(store.read(FLOOR))
    except (OSError, ValueError):
        floor = 0
    return max(max(numbers(store), default=0), floor) + 1


def meta(store, number):
    return json.loads(store.read(f"{home(store, number)}/issue.json"))


def save(store, number, **change):
    """Stages NUMBER's changed fields; a change to a missing issue raises, never makes it."""
    old = meta(store, number) if change.get("createdAt") is None else {}
    store.stage(f"{home(store, number)}/issue.json", json.dumps({**old, **change, "updatedAt": iso_time.stamp()}))


def comment_paths(store, number):
    folder = f"{home(store, number)}/comments"
    return [f"{folder}/{name}" for name in store.children(folder) if name.endswith((".md", ".json"))]


def note(store, path):
    """{body, fields} of the comment at PATH; one written as text alone has no stored fields."""
    if path.endswith(".md"):
        return {"body": store.read(path)}
    stored = json.loads(store.read(path))
    return {"body": stored.pop("text"), "fields": stored}


def record(store, number, comments=True, owners=None):
    """NUMBER's record; OWNERS, the parents by part from `owners(store)`, spares a read of every body when many records are read."""
    issue = meta(store, number)
    given = issue.get("commentTimes", [])  # a copy of another board keeps the times its comments had there
    address = store.url(home(store, number))
    notes = [{**note(store, path), "url": f"{address}#comment-{int(path.rsplit('/', 1)[1].split('.')[0])}",
              "createdAt": given[at] if at < len(given) else iso_time.stamp(store.written(path)), "trusted": True}
             for at, path in enumerate(comment_paths(store, number))] if comments else []
    return {"number": number, "title": issue["title"], "body": store.read(f"{home(store, number)}/body.md"), "url": address, "scope": store.place(number), "state": issue["state"], "stateReason": issue["reason"],
            "depends": task_links.depends({"body": store.read(f"{home(store, number)}/body.md"), "depends": issue.get("depends")}),
            "createdAt": issue["createdAt"], "closedAt": issue["closedAt"], "trusted": True, "labels": issue["labels"], "parent": parent_of(store, number) if owners is None else owners.get(number), "isPullRequest": False,
            "mergedAt": None, "comments": notes}


def scoped(store, project):
    """The folder whose issues are PROJECT's: its own top-level folder, else '' the repository root."""
    return board_scope.folder_of(project)


def issues(store, state="open", project=None, pulls=False, comments=True, since=None, repo=None):
    """The issues newest first, those in PROJECT's folder and below when given (the root project holds only the root's own), updated since SINCE (an ISO time) when given."""
    store.view()
    scope = scoped(store, project) if project else None
    keep = lambda number: state in ("all", meta(store, number)["state"].lower()) and (scope is None or board_scope.within(store.place(number), scope)) \
        and (not since or meta(store, number)["updatedAt"] >= since)
    parents = owners(store)
    return [record(store, number, comments, parents) for number in reversed(numbers(store)) if keep(number)]


def fresh(store, number, repo=None, comments=True):
    store.view()
    return exists(store, number, comments)


def comments_since(store, since):
    store.view()
    parents = owners(store)
    return [(number, note) for number in numbers(store) for note in record(store, number, owners=parents)["comments"] if note["createdAt"] >= since]


def changed_since(store, stamp):
    store.view()
    return any(meta(store, number)["updatedAt"] >= stamp for number in numbers(store))


def owners(store):
    """{part: the issue whose body names it}, read in one pass over the bodies."""
    return {part: owner for owner in numbers(store) for part in task_links.parts(store.read(f"{home(store, owner)}/body.md"))}


def parent_of(store, number):
    """The issue whose body names NUMBER as a part, else None."""
    return next((owner for owner in numbers(store) if int(number) in task_links.parts(store.read(f"{home(store, owner)}/body.md"))), None)


def exists(store, number, comments=False):
    """NUMBER's record, None when no issue has that number or its files cannot be read."""
    try:
        return record(store, int(number), comments)
    except (OSError, ValueError, KeyError):
        return None


def blockers(store, number):
    store.view()
    return [target for target in record(store, int(number), False, {})["depends"] if not ((found := exists(store, target)) and task_links.completed(found))]


def check_links(store, number, text, depends=None):
    """Raises LookupError naming why TEXT cannot be NUMBER's body (None for an issue not yet filed) beside the tasks DEPENDS numbers, those it waits on now when None."""
    store.view()
    waits = depends if depends is not None else record(store, int(number), False, {})["depends"] if number else []
    found = task_links.refusals(number and int(number), text, waits, lambda n: exists(store, n), lambda n: parent_of(store, n))
    if found:
        raise LookupError(f"nothing written to #{number or 'a new issue'}: " + "; ".join(found))


def tree(store, project, nodes=None):
    """The open issues' nodes in the shape the issue pane draws."""
    store.view()
    nodes = nodes if nodes is not None else [
        {**{k: issue[k] for k in ("number", "title", "url", "body", "depends")}, "labels": {"nodes": [{"name": name} for name in issue["labels"]]},
         "comments": {"nodes": [{k: note[k] for k in ("body", "fields", "url", "createdAt") if k in note} for note in issue["comments"]]}} for issue in reversed(issues(store, "open", project))]
    for node in nodes:
        node["trusted"] = True
        for item in node["comments"]["nodes"]:
            item["trusted"] = True
    return task_links.derive(nodes, lambda n: exists(store, n))


def atomic(store, change):
    """CHANGE's result, every write it makes kept as one commit, or none when it raises."""
    return store.write(change)


def comment(store, number, text, fields=None):
    """Adds TEXT with its FIELDS as NUMBER's next comment; its url. issue_state.Refused, nothing written, for fields the schema refuses."""
    stored = {"text": text, **(fields or {})}
    if refused := issue_state.invalid(stored):
        raise issue_state.Refused(f"nothing written to #{number}: {refused}")

    def change():
        meta(store, number)  # raises when NUMBER does not exist
        position = len(comment_paths(store, number)) + 1
        store.stage(f"{home(store, number)}/comments/{position:04d}.json", json.dumps(stored, ensure_ascii=False, indent=1))
        save(store, number)
        return f"{store.url(home(store, number))}#comment-{position}"
    return store.write(change)


def file(store, title, body, labels, scope=None, depends=()) -> int:
    """Opens an issue in the folder SCOPE names (the caller's own project folder when None), waiting on the tasks DEPENDS numbers; LookupError for a folder the repository lacks."""
    folder = board_scope.default() if scope is None else board_scope.check(scope)

    def change():
        check_links(store, None, body, list(depends))
        number = next_number(store)
        store.stage(f"{folder}/{number}/body.md" if folder else f"{number}/body.md", body)  # before issue.json, so a reader that lists the issue finds its body
        save(store, number, title=title, labels=list(labels), state="OPEN", reason="", createdAt=iso_time.stamp(), closedAt=None, depends=list(depends))
        return number
    return store.write(change)


def body(store, number):
    store.view()
    try:
        return store.read(f"{home(store, number)}/body.md")
    except OSError as e:
        raise LookupError(f"cannot read #{number} ({e.strerror or e}); check the board setting") from e


def edit(store, number, text):
    def change():
        body(store, number)
        check_links(store, number, text)
        store.stage(f"{home(store, number)}/body.md", text)
        save(store, number)
    store.write(change)


def depend(store, number, targets):
    """Makes NUMBER wait on the tasks TARGETS numbers, replacing those it waited on, and says so in a comment; its url."""
    def change():
        check_links(store, number, body(store, number), list(targets))
        save(store, number, depends=list(targets))
        return comment(store, number, f"{issue_state.ANSWER}: waits on {' '.join(f'#{target}' for target in targets)}." if targets else f"{issue_state.ANSWER}: waits on no task.")
    return store.write(change)


def resolve(store, number, summary, completed=True):
    def change():
        comment(store, number, summary)
        save(store, number, state="CLOSED", reason="COMPLETED" if completed else "NOT_PLANNED", closedAt=iso_time.stamp())
    store.write(change)


def reopen(store, number):
    """Opens NUMBER again; an open one stays as it is."""
    def change():
        if meta(store, number)["state"] == "CLOSED":
            save(store, number, state="OPEN", reason="", closedAt=None)
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
    verb = found.group(1)
    return {"called": f"use-board.py {verb}", "write": {"decide": "comment", "title": "edit"}.get(verb, verb if verb in ("file", "comment", "resolve", "edit") else None)}


PORT = ("atomic", "issues", "fresh", "comments_since", "changed_since", "blockers", "scoped", "tree", "comment", "file", "body", "edit", "resolve", "reopen",
        "retitle", "label", "depend", "parent_of", "check_links")


def bind(store):
    """The board port's functions over STORE, with the store-free ones (`trusted`, `command`)."""
    here = globals()
    return {**{name: functools.partial(here[name], store) for name in PORT}, "trusted": trusted, "command": command}
