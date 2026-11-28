"""Links to a task or a comment of the board, in the one form this board writes them: `git+file://<git common dir>/refs/teamwork-blackboard/<scope>/<n>`,
the path percent-encoded, then `#comment-<k>` for a comment. `TaskRef.parse` reads a link a person typed and refuses one of another board by naming it;
`stored` reads a link or a record's ref, `<n>#comment-<k>`, by task and comment index, so a moved checkout or a rescoped task keeps it; `relative` gives that ref; `url` builds a link."""
import dataclasses
import functools
import os
import re
import typing
import urllib.parse

import data_folder

REF = "refs/teamwork-blackboard"
SCHEME = "git+file"
NUMBER = re.compile(r"#?(\d+)")
TASK = re.compile(r"(?:(.*)/)?(\d+)")
STORED = re.compile(r"(?:^|" + re.escape(REF) + r"/(?:.*/)?)(\d+)(?:#comment-(\d+))?$")


class Refused(ValueError):
    """Why a text names no task of this board, a clause that follows the text: `it belongs to` the board that holds it."""


@functools.lru_cache  # keyed by the folder, since one process may act on several checkouts
def common_in(folder):
    found = data_folder.common_folder()
    return str(found) if found else None


def common():
    """The git common folder of the current folder's repository, which names this board; None outside one."""
    return common_in(os.getcwd())


def url(scope, number, comment=None):
    """The link to task NUMBER in the folder SCOPE ('' for the repository root), or to its comment COMMENT, with its path percent-encoded."""
    path = "/".join(part for part in (common(), REF, scope, str(number)) if part)
    return f"{SCHEME}://{urllib.parse.quote(path)}" + (f"#comment-{comment}" if comment is not None else "")


def stored(url):
    """(task number, comment index) a link or a ref names, 0 for a part it does not name, whichever checkout or scope wrote it; (0, the text) for text that is
    neither, so it matches only the same text."""
    found = STORED.search(url or "")
    return (int(found.group(1)), int(found.group(2) or 0)) if found else (0, url or "")


def relative(url):
    """The ref `<n>#comment-<k>` of the comment a link or a ref names, as a record stores it; None for text that names no comment."""
    number, comment = stored(url)
    return f"{number}#comment-{comment}" if number and comment else None


@dataclasses.dataclass(frozen=True)
class TaskRef:
    scope: typing.Optional[str]
    number: int
    comment: typing.Optional[int]

    @classmethod
    def parse(cls, text):
        """The task a `7`, a `#7` or this board's link names, its scope None when a number gives none; Refused for any other text, naming the board a link belongs to, in a clause that follows the text."""
        if found := NUMBER.fullmatch(text):
            return cls(None, int(found.group(1)), None)
        try:
            parts = urllib.parse.urlsplit(text)
        except ValueError:
            parts = None
        # urlsplit drops a tab, a line break and, on newer Pythons, a leading space or control character, so it would read a padded url as the bare one
        if not parts or not parts.scheme or text != text.strip() or not text.isprintable():
            raise Refused("names no task; give its number or its url")
        path = urllib.parse.unquote(parts.path)
        here, found_ref, tail = path.partition(f"/{REF}/")
        mine = common()
        if parts.scheme != SCHEME or not found_ref:
            raise Refused(f"belongs to {parts.netloc or parts.scheme}, not to this board, which is {mine}")
        if here != mine:
            raise Refused(f"belongs to the board of {here}, not to this board, which is {mine}")
        task, comment = TASK.fullmatch(tail), re.fullmatch(r"comment-(\d+)", parts.fragment) if parts.fragment else None
        if not task or parts.query or (parts.fragment and not comment):
            raise Refused("is no task link of this board: it ends `<scope>/<n>` or `<scope>/<n>#comment-<k>`")
        return cls(task.group(1) or "", int(task.group(2)), int(comment.group(1)) if comment else None)
