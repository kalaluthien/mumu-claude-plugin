"""The board's two record types, as board-record-schema.json defines them, and the one place a comment's keyword is read:
- `Task.load(stored, name)`, a `task.json`: `title`, `labels`, `state` (`open`, `completed` or `stopped`), `depends`, `created`, `updated`, `closed`
- `Comment.load(stored, name)`, a `comments/<k>.json`: `kind` (question, report, decision, event or note), `line`, the words of its keyword
  line, `text`, what follows that line from the newline that ends it, `fields`, its data, `author`, `created` and `ref`, its own `<n>#comment-<k>`
- `.dump()` the dict a record is stored as, `task_state.Refused` for one the schema refuses
- `Comment.parse(said, fields, author, created, ref)` the comment a writer's text `<KEYWORD>: <line>`, then the rest, makes; `shown(comment)` that text again
- `OldRecord`, raised by a load of a record in the form before this one, which exits 2 naming the record and convert-records.py
NAME is the record's path in the board; a comment a reader holds is `Comment.load(...).view(url)`, a dict with its url."""
import dataclasses
import pathlib
import re
import sys
import typing

import task_state

KEYWORDS = {"question": task_state.ASK, "report": task_state.INFORM, "decision": task_state.ANSWER, "event": task_state.ANSWER}
KEYED = re.compile(r"(" + "|".join(task_state.KEYWORDS) + r"):( ?)([^\n]*)")
CONVERT = pathlib.Path(__file__).resolve().parents[1] / "skills" / "kick-off" / "scripts" / "convert-records.py"
TASK_KEYS = {"created": "createdAt", "updated": "updatedAt", "closed": "closedAt"}


class OldRecord(SystemExit):
    """A record in the old form; a SystemExit, so no reader's handler of a failed read takes it for a missing record, and its message is
    printed here, since an exit status carries none."""

    def __init__(self, name):
        self.message = f"{name} is a board record in the form before records carry their kind, which no board call reads: run `python3 {CONVERT}` once, then call again"
        print(self.message, file=sys.stderr)
        super().__init__(2)


def checked(stored, definition, name):
    if refused := task_state.invalid(stored, task_state.SCHEMA["definitions"][definition], name):
        raise task_state.Refused(f"nothing written to {name}: {refused}")
    return stored


@dataclasses.dataclass
class Task:
    title: str
    labels: typing.List[str]
    state: str
    depends: typing.List[int]
    created: str
    updated: str
    closed: typing.Optional[str]

    @classmethod
    def load(cls, stored, name="task.json"):
        if stored.get("state") in ("OPEN", "CLOSED"):
            raise OldRecord(name)
        return cls(**{key: stored[TASK_KEYS.get(key, key)] for key in cls.__dataclass_fields__})

    def dump(self, name="task.json"):
        return checked({TASK_KEYS.get(key, key): value for key, value in dataclasses.asdict(self).items()}, "task", name)


@dataclasses.dataclass
class Comment:
    kind: str
    line: str
    text: str
    fields: dict
    author: str
    created: str
    ref: str

    @classmethod
    def load(cls, stored, name="comment"):
        if "kind" not in stored:
            raise OldRecord(name)
        own = {key: stored[key] for key in ("kind", "line", "text", "author", "created", "ref")}
        return cls(**own, fields={key: value for key, value in stored.items() if key not in own})

    @classmethod
    def parse(cls, said, fields, author, created, ref):
        """The comment SAID makes: a question, a report, a decision when FIELDS hold one else an event, by the keyword its first line opens with
        followed by a space or by the line's end, else a note; `shown` gives SAID back unchanged."""
        found = KEYED.match(said)
        if found and (found.group(2) or not found.group(3)):
            keyword = found.group(1)
            kind = {task_state.ASK: "question", task_state.INFORM: "report"}.get(keyword) or ("decision" if "decision" in fields else "event")
            # a keyword line with no words keeps what follows the colon as it was, a space or the newline
            line, text = (found.group(3), said[found.end():]) if found.group(3).strip() else ("", said[len(keyword) + 1:])
        else:
            kind, line = "note", said.split("\n", 1)[0]
            text = said[len(line):]
        return cls(kind, line, text, dict(fields), author, created, ref)

    def dump(self, name="comment"):
        own = {key: value for key, value in dataclasses.asdict(self).items() if key != "fields"}
        return checked({**own, **self.fields}, "comment", name)

    def view(self, url):
        return {**dataclasses.asdict(self), "url": url}


def shown(comment):
    """A comment's text as its writer said it: the keyword line, then what follows it."""
    keyword = KEYWORDS.get(comment["kind"])
    head = "" if keyword is None else f"{keyword}: " if comment["line"] else f"{keyword}:"
    return head + comment["line"] + comment["text"]
