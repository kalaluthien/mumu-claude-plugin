"""Read a memory file's frontmatter: its confirmation count, the date it was last confirmed, and the header Claude Code reads."""
import os
import re
from datetime import date

# MEMORY.md is left out: it indexes lessons, so editing it is no new lesson; a repository's folder under the memory
# home is kept in the match, so one name in two folders counts twice
PATH = re.compile(r"/memory/((?:[\w.-]+/)?(?!MEMORY\.md)[\w.-]+\.md)")
# the indent is kept, so a field nested under `metadata:` is rewritten in place
FIELD = re.compile(r"^([ \t]*)(confirmed|last-confirmed):[ \t]*(.*)$", re.M)


def split(text):
    """(frontmatter, body), frontmatter None when the file has none."""
    found = re.match(r"---\n(.*?\n)?---\n", text, re.S)
    return (found.group(1) or "", text[found.end():]) if found else (None, text)


def fields(path, text):
    """(confirmed, last-confirmed) of a file's text: a missing count, or one below 1, reads 1, a missing date the file's modification date."""
    front, _ = split(text)
    values = {name: value for _, name, value in FIELD.findall(front or "")}
    try:
        count = max(1, int(values.get("confirmed", "1")))
    except ValueError:
        count = 1
    try:
        last = date.fromisoformat(values["last-confirmed"].strip())
    except (KeyError, ValueError):
        last = date.fromtimestamp(os.path.getmtime(path))
    return count, last


TYPES = ("user", "feedback", "project", "reference")
# a block of indented lines under a top-level `metadata:`, where Claude Code reads `type`
METADATA = re.compile(r"^metadata:[ \t]*\n((?:[ \t]+.*\n?)*)", re.M)
TYPE = re.compile(r"^[ \t]+type:[ \t]*(.*)$", re.M)


def value(text):
    """A YAML scalar of a header line: its trailing ` # comment` and its quotes cut."""
    return re.split(r"\s#", text, maxsplit=1)[0].strip().strip("\"'")


def header_problems(path, text):
    """What is wrong with the header Claude Code reads, one phrase each; empty when the header is whole."""
    front, _ = split(text)
    if front is None:
        return ["no frontmatter"]
    found = []
    name = re.search(r"^name:[ \t]*(.*)$", front, re.M)
    stem = os.path.basename(path)[:-len(".md")]
    if not name or value(name.group(1)) != stem:
        found.append(f"name is not {stem}")
    description = re.search(r"^description:[ \t]*(.*)$", front, re.M)
    if not description or not value(description.group(1)):
        found.append("no description")
    block = METADATA.search(front)
    kind = TYPE.search(block.group(1)) if block else None
    if not kind or value(kind.group(1)) not in TYPES:
        found.append(f"metadata.type is not {', '.join(TYPES[:-1])} or {TYPES[-1]}")
    return found
