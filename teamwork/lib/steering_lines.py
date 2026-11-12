"""The worker prompt's steering lines, loaded by key from the table in assets/handoff-worker-prompt.md."""
import pathlib
import re

TABLE = pathlib.Path(__file__).resolve().parents[1] / "skills" / "kick-off" / "assets" / "handoff-worker-prompt.md"
WORD_CAP = 100  # the cap on a worker prompt that manager-handoff-task.md states; urls do not count
URL = re.compile(r"\S+://\S+")


def rows():
    """Each row of the table as a dict of its columns, in file order."""
    found = []
    for line in TABLE.read_text().splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split(" | ")]
        if line.startswith("|") and len(cells) == 4 and cells[0] not in ("key", "---"):
            found.append(dict(zip(("key", "with", "case", "line"), cells)))
    return found


def words(text):
    return len(URL.sub("", text).split())


def lines(keys):
    """The lines of KEYS joined by a space, or a ValueError naming the fix."""
    by_key = {row["key"]: row for row in rows()}
    unknown = [key for key in keys if key not in by_key]
    if unknown:
        raise ValueError(f"no steering key {', '.join(unknown)}: the keys are {', '.join(by_key)}")
    keys = list(dict.fromkeys(keys))
    alone = [key for key in keys if by_key[key]["with"] == "alone"]
    if alone and len(keys) > 1:
        raise ValueError(f"{alone[0]} takes its line alone: drop the other keys")
    text = " ".join(by_key[key]["line"] for key in keys)
    if words(text) > WORD_CAP:
        raise ValueError(f"these lines hold {words(text)} words, over the cap of {WORD_CAP}: drop a key")
    return text
