"""Read a memory file's frontmatter: its confirmation count and the date it was last confirmed."""
import os
import re
from datetime import date

# groups: indent, name, value
FIELD = re.compile(r"^([ \t]*)(confirmed|last-confirmed):[ \t]*(.*)$", re.M)


def split(text):
    """(frontmatter, body), frontmatter None when the file has none."""
    found = re.match(r"---\n(.*?\n)?---\n", text, re.S)
    return (found.group(1) or "", text[found.end():]) if found else (None, text)


def fields(path, text):
    """(confirmed, last-confirmed) of a file's text: a missing count reads 1, a missing date the file's modification date."""
    front, _ = split(text)
    values = {name: value for _, name, value in FIELD.findall(front or "")}
    try:
        count = int(values.get("confirmed", "1"))
    except ValueError:
        count = 1
    try:
        last = date.fromisoformat(values["last-confirmed"].strip())
    except (KeyError, ValueError):
        last = date.fromtimestamp(os.path.getmtime(path))
    return count, last
