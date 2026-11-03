"""The board port: where a team keeps its issues and records, done by the adapter `board_<TEAMWORK_BOARD>`, read from the environment, else from the project's Claude settings `env` (default `github`).

Every adapter has these functions, by the same names:
- reads: `issues(state, project, pulls, comments, since, repo)`, `fresh(number, repo, comments)`, `comments_since(since)` as (issue number, comment),
  `changed_since(stamp)`, `blockers(number)` the numbers its `depends on` names that are not closed as completed, `scoped(project)` the label that scopes a project or None,
  `tree(project, nodes)` the open issues' nodes the issue pane draws; each None when a read failed
- writes: `comment(number, text)`, `file(title, body, labels) -> int`, `body(number)` and `edit(number, body)`, `resolve(number, summary, completed)`, `reopen(number)`, `retitle(number, title)`,
  `label(number, name, remove)`; this port's `edit` and `resolve` add the state links derive: a follow-up part reopens, a stop stops the parts, the last part closes its parent
- links: `parent_of(number)` the task whose body names it as a part, `check_links(number, body)` raises LookupError naming why BODY cannot be NUMBER's
- `trusted(record)`, whether a record's author may write records; `command(text)` and `posted(output)`, the board write a shell command runs and what it posted
A record has `number`, `title`, `body`, `labels` (names), `state` (`OPEN` or `CLOSED`), `parent` (a number or None), `trusted` and `comments`,
each comment with `body` and `trusted`."""
import importlib

import port_setting
import task_links


def kind():
    """The adapter's name, read at each call, so a long-running process follows a setting written after it started."""
    return port_setting.value("TEAMWORK_BOARD", "github")


def adapter():
    return importlib.import_module(f"board_{kind()}")


def __getattr__(name):
    return getattr(adapter(), name)


def edit(number, text):
    """Writes TEXT as NUMBER's body; a closed task whose new body gains a part opens again, since that part is follow-up work."""
    old = adapter().fresh(number, comments=False)
    adapter().edit(number, text)
    if old and old["state"] == "CLOSED" and set(task_links.parts(text)) - set(task_links.parts(old["body"])):
        adapter().reopen(number)


def resolve(number, summary, completed=True):
    """Closes NUMBER. Stopped, it first stops its open parts, named in one `DECIDED:` on it; completed, it closes its parent
    once every part of the parent is closed as completed and the parent holds no other criterion."""
    record = adapter().fresh(number, comments=False)
    stopping = [part for part in task_links.parts(record["body"]) if (found := adapter().fresh(part, comments=False)) and found["state"] == "OPEN"] if record and not completed else []
    if stopping:
        adapter().comment(number, f"DECIDED: stopping #{number} stops its open parts {' '.join(f'#{part}' for part in stopping)}.")
    adapter().resolve(number, summary, completed)
    for part in stopping:
        resolve(part, f"REPORTED: stopped with its parent #{number}.", False)
    parent = completed and adapter().parent_of(number)
    found = parent and adapter().fresh(parent, comments=False)
    if found and found["state"] == "OPEN" and not task_links.criteria(found["body"]):
        named = [adapter().fresh(part, comments=False) for part in task_links.parts(found["body"])]
        if all(part and task_links.completed(part) for part in named):
            resolve(parent, f"REPORTED: every part closed as completed, the last #{number}.")
