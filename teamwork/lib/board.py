"""The board: where a team keeps its issues and records, the git board `board_git`, whose functions this module re-exports by the same names:
- reads: `issues(state, project, pulls, comments, since, repo)`, `fresh(number, repo, comments)`, `comments_since(since)` as (issue number, comment),
  `changed_since(stamp)`, `blockers(number)` the numbers of the tasks it waits on that are not closed as completed, `scoped(project)` the folder that scopes a project ('' the repository root),
  `tree(project, nodes)` the open issues' nodes the issue pane draws; each None when a read failed
- writes: `atomic(change)` runs CHANGE's writes as one, `comment(number, text, fields)`, `file(title, body, labels, scope, depends) -> int` (`scope` the folder), `depend(number, targets)`, `body(number)` and `edit(number, body)`, `resolve(number, summary, completed)`, `reopen(number)`, `retitle(number, title)`,
  `label(number, name, remove)`; this module's `edit`, `resolve` and `reopen` move the tree as issue-grammar.md's States table says
- links: `parent_of(number)` the task whose body names it as a part, `check_links(number, body, depends)` raises LookupError naming why NUMBER cannot have BODY and wait on DEPENDS
- `trusted(record)`, whether a record's author may write records; `command(text)`, the board write a shell command runs
A record has `number`, `title`, `body`, `labels` (names), `state` (`OPEN` or `CLOSED`), `parent` (a number or None), `trusted`,
`depends` (the numbers of the tasks it waits on) and `comments`, each comment with `body`, `trusted` and, unless it was written as text alone, `fields`."""
import hashlib

import board_git
import issue_state
import task_links


def body_sha(text):
    """The first 12 hex digits of TEXT's sha-256 with CRLF read as LF, which names the body a diff was made from, so an edit refuses a diff of a body that changed since."""
    return hashlib.sha256(text.replace("\r\n", "\n").encode()).hexdigest()[:12]


def __getattr__(name):
    return getattr(board_git, name)


def parts_completed(body):
    """Whether every part BODY names was closed as completed."""
    return all((found := board_git.fresh(part, comments=False)) and task_links.completed(found) for part in task_links.parts(body))


def edit(number, text):
    return board_git.atomic(lambda: edit_whole(number, text))


def edit_whole(number, text):
    """Writes TEXT as NUMBER's body, then moves the tree as issue-grammar.md's States table says for an `edit`."""
    old = board_git.fresh(number, comments=False)
    board_git.edit(number, text)
    gained = set(task_links.parts(text)) - set(task_links.parts(old["body"])) if old else set()
    if old and old["state"] == "CLOSED" and gained:
        reopen_up(number)
    dropped = old and (set(task_links.parts(old["body"])) - set(task_links.parts(text)) or set(task_links.criteria(old["body"])) - set(task_links.criteria(text)))
    if dropped and old["state"] == "OPEN" and task_links.parts(text) and not task_links.criteria(text) and parts_completed(text):
        resolve(number, "REPORTED: every part left closed as completed, once the edit dropped the rest.")


def resolve(number, summary, completed=True):
    return board_git.atomic(lambda: resolve_whole(number, summary, completed))


def resolve_whole(number, summary, completed=True):
    """Closes NUMBER as issue-grammar.md's States table says, its open parts stopped with it named in one `DECIDED:` on it."""
    record = board_git.fresh(number, comments=False)
    if record and record["state"] == "CLOSED":
        raise LookupError(f"#{number} is closed; reopen it first")
    if record and completed and not parts_completed(record["body"]):
        raise LookupError(f"#{number} has a part not closed as completed; resolve each open part first, `edit` a stopped part out of #{number}'s body, or `resolve` #{number} --not-planned")
    stopping = [part for part in task_links.parts(record["body"]) if (found := board_git.fresh(part, comments=False)) and found["state"] == "OPEN"] if record and not completed else []
    if stopping:
        board_git.comment(number, f"{issue_state.ANSWER}: stopping #{number} stops its open parts {' '.join(f'#{part}' for part in stopping)}.")
    board_git.resolve(number, summary, completed)
    for part in stopping:
        resolve(part, f"REPORTED: stopped with its parent #{number}.", False)
    parent = completed and board_git.parent_of(number)
    found = parent and board_git.fresh(parent, comments=False)
    if found and found["state"] == "OPEN" and int(number) in task_links.parts(found["body"]) and not task_links.criteria(found["body"]) and parts_completed(found["body"]):
        resolve(parent, f"REPORTED: every part closed as completed, the last #{number}.")


def reopen_up(number):
    """Opens NUMBER, which must exist, and each closed task above it."""
    board_git.reopen(number)
    while number := board_git.parent_of(number):
        found = board_git.fresh(number, comments=False)
        if found and found["state"] == "CLOSED":
            board_git.reopen(number)


def reopen(number):
    return board_git.atomic(lambda: reopen_up(number))
