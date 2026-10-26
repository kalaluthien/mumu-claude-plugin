"""The board port: where a team keeps its issues and records, done by the adapter `board_<TEAMWORK_BOARD>`, read from the environment, else from the project's Claude settings `env` (default `github`).

Every adapter has these functions, by the same names:
- reads: `issues(state, project, pulls, comments, since, repo)`, `fresh(number, repo, comments)`, `comments_since(since)` as (issue number, comment),
  `changed_since(stamp)`, `blockers(number)` the open issues' numbers it waits on, `scoped(project)` the label that scopes a project or None,
  `tree(project, nodes)` the open issues' nodes the issue pane draws; each None when a read failed
- writes: `comment(number, text)`, `file(title, body, labels) -> int`, `body(number)` and `edit(number, body)`, `resolve(number, summary, completed)`, `reopen(number)`, `retitle(number, title)`,
  `order(later, earlier)`, `nest(backlog, task)`, `label(number, name, remove)`
- `trusted(record)`, whether a record's author may write records; `command(text)` and `posted(output)`, the board write a shell command runs and what it posted
A record has `number`, `title`, `body`, `labels` (names), `state` (`OPEN` or `CLOSED`), `parent` (a number or None), `trusted` and `comments`,
each comment with `body` and `trusted`."""
import importlib
import port_setting


def kind():
    """The adapter's name, read at each call, so a long-running process follows a setting written after it started."""
    return port_setting.value("TEAMWORK_BOARD", "github")


def __getattr__(name):
    return getattr(importlib.import_module(f"board_{kind()}"), name)
