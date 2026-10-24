"""The board port: where a team keeps its issues and records, done by the adapter `board_<TEAMWORK_BOARD>` (default `github`).

Every adapter has these functions, by the same names:
- reads: `issues(state, project, pulls, comments, since, repo)`, `fresh(number, repo, comments)`, `comments_since(since)` as (issue number, comment),
  `changed_since(stamp)`, `blockers(number)` the open issues' numbers it waits on, `scoped(project)` the label that scopes a project or None,
  `tree(project, nodes)` the open issues' nodes the issue pane draws; each None when a read failed
- writes: `comment(number, text)`, `file(title, body, labels) -> int`, `body(number)` and `edit(number, body)`, `resolve(number, summary, completed)`,
  `order(later, earlier)`, `nest(backlog, task)`, `label(number, name, remove)`
- `trusted(record)`, whether a record's author may write records; `command(text)` and `posted(output)`, the board write a shell command runs and what it posted
A record has `number`, `title`, `body`, `labels` (names), `state` (`OPEN` or `CLOSED`), `parent` (a number or None), `trusted` and `comments`,
each comment with `body` and `trusted`."""
import importlib
import os

adapter = importlib.import_module(f"board_{os.environ.get('TEAMWORK_BOARD', 'github')}")


def __getattr__(name):
    return getattr(adapter, name)
