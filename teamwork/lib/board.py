"""The board: where a team keeps its tasks and records, the git board `board_git`, whose functions this module re-exports by the same names:
- reads: `tasks(state, project, comments, since)`, `fresh(number, comments)`, `comments_since(since)` as (task number, comment),
  `changed_since(stamp)`, `blockers(number)` the numbers of the tasks it waits on that are not closed as completed, `scoped(project)` the folder that scopes a project ('' the repository root),
  `tree(project, nodes)` the open tasks' nodes the task pane draws; each None when a read failed
- writes, each refused by `task_state.Refused`, nothing written, unless `board_writers` lets the session running this process write it, and signed with its name as each comment's `author`:
  `atomic(change)` runs CHANGE's writes as one, `comment(number, text, fields)`, `file(title, body, labels, scope, depends) -> int` (`scope` the folder), `depend(number, targets)`, `body(number)` and `edit(number, body)`, `resolve(number, summary, completed)`, `reopen(number)`, `retitle(number, title)`,
  `label(number, name, remove)`; this module's `edit`, `resolve` and `reopen` move the tree as task-grammar.md's States table says
- links: `parent_of(number)` the task whose body names it as a part, `check_links(number, body, depends)` raises LookupError naming why NUMBER cannot have BODY and wait on DEPENDS
- `command(text)`, the board write a shell command runs
A record has `number`, `title`, `body`, `labels` (names), `state` (`open`, `completed` or `stopped`), `parent` (a number or None),
`depends` (the numbers of the tasks it waits on) and `comments`, each as `record_types.Comment.view` gives it; a read of a record in the old form
exits 2 by `record_types.OldRecord`, naming the record and the migration."""
import functools
import hashlib

import board_git
import board_writers
import task_state
import task_links

READS = ("tasks", "fresh", "comments_since", "changed_since", "blockers", "scoped", "tree", "body", "parent_of", "check_links", "command", "atomic")


def body_sha(text):
    """The first 12 hex digits of TEXT's sha-256 with CRLF read as LF, which names the body a new one was made from, so an edit refuses a new body made from one that changed since."""
    return hashlib.sha256(text.replace("\r\n", "\n").encode()).hexdigest()[:12]


def __getattr__(name):
    if name not in READS:
        raise AttributeError(f"board has no {name}")
    return getattr(board_git, name)


@functools.cache
def writer():
    return board_writers.writer()


def gate(verb, number, fields=None):
    """Raises task_state.Refused naming each rule VERB on NUMBER breaks, else signs the board's commits with the writer's name."""
    me = writer()
    if refusals := board_writers.check(verb, number, fields or {}, me):
        raise task_state.Refused("nothing posted: " + "; ".join(refusals))
    board_git.author(me.name)


def comment(number, text, fields=None):
    gate("comment", number, {"text": text, **(fields or {})})
    return board_git.comment(number, text, fields)


def file(title, body, labels, scope=None, depends=()):
    gate("file", None)
    return board_git.file(title, body, labels, scope=scope, depends=depends)


def depend(number, targets):
    gate("depend", number)
    return board_git.depend(number, targets)


def retitle(number, title):
    gate("title", number)
    return board_git.retitle(number, title)


def label(number, name, remove=False):
    gate("label", number)
    return board_git.label(number, name, remove)


def parts_completed(body):
    """Whether every part BODY names was closed as completed."""
    return all((found := board_git.fresh(part, comments=False)) and task_links.completed(found) for part in task_links.parts(body))


def edit(number, text):
    gate("edit", number)
    return board_git.atomic(lambda: edit_whole(number, text))


def edit_whole(number, text):
    """Writes TEXT as NUMBER's body, then moves the tree as task-grammar.md's States table says for an `edit`."""
    old = board_git.fresh(number, comments=False)
    board_git.edit(number, text)
    gained = set(task_links.parts(text)) - set(task_links.parts(old["body"])) if old else set()
    if old and old["state"] != "open" and gained:
        reopen_up(number)
    dropped = old and (set(task_links.parts(old["body"])) - set(task_links.parts(text)) or set(task_links.criteria(old["body"])) - set(task_links.criteria(text)))
    if dropped and old["state"] == "open" and task_links.parts(text) and not task_links.criteria(text) and parts_completed(text):
        resolve_whole(number, "REPORTED: every part left closed as completed, once the edit dropped the rest.")


def resolve(number, summary, completed=True):
    gate("resolve", number)
    return board_git.atomic(lambda: resolve_whole(number, summary, completed))


def resolve_whole(number, summary, completed=True):
    """Closes NUMBER as task-grammar.md's States table says, its open parts stopped with it named in one `DECIDED:` on it."""
    record = board_git.fresh(number, comments=False)
    if record and record["state"] != "open":
        raise LookupError(f"#{number} is closed; reopen it first")
    if record and completed and not parts_completed(record["body"]):
        raise LookupError(f"#{number} has a part not closed as completed; resolve each open part first, `edit` a stopped part out of #{number}'s body, or `resolve` #{number} --not-planned")
    stopping = [part for part in task_links.parts(record["body"]) if (found := board_git.fresh(part, comments=False)) and found["state"] == "open"] if record and not completed else []
    if stopping:
        board_git.comment(number, f"{task_state.ANSWER}: stopping #{number} stops its open parts {' '.join(f'#{part}' for part in stopping)}.")
    board_git.resolve(number, summary, completed)
    for part in stopping:
        resolve_whole(part, f"REPORTED: stopped with its parent #{number}.", False)
    parent = completed and board_git.parent_of(number)
    found = parent and board_git.fresh(parent, comments=False)
    if found and found["state"] == "open" and int(number) in task_links.parts(found["body"]) and not task_links.criteria(found["body"]) and parts_completed(found["body"]):
        resolve_whole(parent, f"REPORTED: every part closed as completed, the last #{number}.")


def reopen_up(number):
    """Opens NUMBER, which must exist, and each closed task above it."""
    board_git.reopen(number)
    while number := board_git.parent_of(number):
        found = board_git.fresh(number, comments=False)
        if found and found["state"] != "open":
            board_git.reopen(number)


def reopen(number):
    gate("reopen", number)
    return board_git.atomic(lambda: reopen_up(number))
