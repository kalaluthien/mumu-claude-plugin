"""The one way board text reaches an instruction line: `quote(text, cap=60)`, TEXT with its control characters (newlines too) removed, cut to CAP
characters then an ellipsis, and put in double quotes; `line(instruction, **data)`, INSTRUCTION then each datum as `name: <quoted>`, after it, so a title
or report written by anyone reads as data and never as the line's instruction."""
import re

# C0 and DEL, which a terminal or a prompt reads as a command or a line break
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def quote(text, cap=60):
    cleaned = CONTROL.sub("", str(text or "")).replace('"', "'")
    return '"' + (cleaned[:cap] + "…" if len(cleaned) > cap else cleaned) + '"'


def line(instruction, **data):
    return " ".join([instruction, *(f"{name}: {quote(value)}" for name, value in data.items())])
