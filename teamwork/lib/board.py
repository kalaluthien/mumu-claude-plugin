"""The board: where a team keeps its issues and records, the git board `board_git`, whose functions this module re-exports by the same names:
- reads: `issues(state, project, pulls, comments, since, repo)`, `fresh(number, repo, comments)`, `comments_since(since)` as (issue number, comment),
  `changed_since(stamp)`, `blockers(number)` the numbers its `depends on` names that are not closed as completed, `scoped(project)` the folder that scopes a project ('' the repository root),
  `tree(project, nodes)` the open issues' nodes the issue pane draws; each None when a read failed
- writes: `atomic(change)` runs CHANGE's writes as one, `comment(number, text)`, `file(title, body, labels, scope) -> int` (`scope` the folder, git board only), `body(number)` and `edit(number, body)`, `resolve(number, summary, completed)`, `reopen(number)`, `retitle(number, title)`,
  `label(number, name, remove)`; this module's `edit` and `resolve` add the state links derive: a follow-up part reopens, a stop stops the parts, the last part closes its parent
- links: `parent_of(number)` the task whose body names it as a part, `check_links(number, body)` raises LookupError naming why BODY cannot be NUMBER's
- `trusted(record)`, whether a record's author may write records; `command(text)` and `posted(output)`, the board write a shell command runs and what it posted
A record has `number`, `title`, `body`, `labels` (names), `state` (`OPEN` or `CLOSED`), `parent` (a number or None), `trusted` and `comments`,
each comment with `body` and `trusted`."""
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
    """Writes TEXT as NUMBER's body; a closed task whose new body gains a part opens again, since that part is follow-up work, and an
    open one whose new body drops a part or a criterion closes once no criterion is left and every part left was closed as completed."""
    old = board_git.fresh(number, comments=False)
    board_git.edit(number, text)
    if old and old["state"] == "CLOSED" and set(task_links.parts(text)) - set(task_links.parts(old["body"])):
        board_git.reopen(number)
    dropped = old and (set(task_links.parts(old["body"])) - set(task_links.parts(text)) or set(task_links.criteria(old["body"])) - set(task_links.criteria(text)))
    if dropped and old["state"] == "OPEN" and task_links.parts(text) and not task_links.criteria(text) and parts_completed(text):
        resolve(number, "REPORTED: every part left closed as completed, once the edit dropped the rest.")


def resolve(number, summary, completed=True):
    return board_git.atomic(lambda: resolve_whole(number, summary, completed))


def resolve_whole(number, summary, completed=True):
    """Closes NUMBER. Stopped, it first stops its open parts, named in one `DECIDED:` on it; completed, it closes its parent
    once every part of the parent is closed as completed and the parent holds no other criterion."""
    record = board_git.fresh(number, comments=False)
    stopping = [part for part in task_links.parts(record["body"]) if (found := board_git.fresh(part, comments=False)) and found["state"] == "OPEN"] if record and not completed else []
    if stopping:
        board_git.comment(number, f"{issue_state.STOPPING}{number} stops its open parts {' '.join(f'#{part}' for part in stopping)}.")
    board_git.resolve(number, summary, completed)
    for part in stopping:
        resolve(part, f"REPORTED: stopped with its parent #{number}.", False)
    parent = completed and board_git.parent_of(number)
    found = parent and board_git.fresh(parent, comments=False)
    if found and found["state"] == "OPEN" and int(number) in task_links.parts(found["body"]) and not task_links.criteria(found["body"]) and parts_completed(found["body"]):
        resolve(parent, f"REPORTED: every part closed as completed, the last #{number}.")
