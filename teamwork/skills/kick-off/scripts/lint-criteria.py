#!/usr/bin/env python3
"""usage: lint-criteria.py <body-file | ->

Print each criterion of a task body's Definition of done whose form a judge would send back, one line per criterion,
`<position>: <defects>`, and exit 1; a body with none prints nothing and exits 0. It reads the form only, never running
a command, since whether a check passes on the default branch stays the judge's to find."""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import issue_state  # noqa: E402

# a run of n backticks closes only on a run of exactly n, so a ``…`` span may hold single backticks
SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
WORD = r"[\s`]+([A-Za-z0-9-]+)"


def defects(kind, name, detail):
    """The defects of one criterion, in the order the task lists them."""
    found = [] if kind in ("check", "score") else ["no kind"]
    found += [] if name else ["no name"]
    span = SPAN.search(detail)
    rest = detail[:span.start()] + detail[span.end():] if span else detail
    if kind == "check":
        passes, main = re.search(r"\bprints" + WORD, rest), re.search(r"\bon main" + WORD, rest)
        found += [] if span else ["no command"]
        found += ["no main output"] if not main else ["passes on main"] if passes and passes.group(1) == main.group(1) else []
    if span and ("..." in span.group(2) or "…" in span.group(2)):
        found.append("elided command")
    if kind == "score":
        found += [f"no {word}" for word in ("sample", "rubric") if f"{word}:" not in rest]
        found += [] if re.search(r"\bmain\b", rest) else ["no main measure"]
    return found


source = sys.argv[1]
body = sys.stdin.read() if source == "-" else pathlib.Path(source).read_text()
lines = issue_state.ITEM.findall(issue_state.sections(body).get("done", ""))
flagged = [(n, found) for n, line in enumerate(lines, 1)
           for found in [defects(*issue_state.CRITERION.match(line).groups()[1:])] if found]
for n, found in flagged:
    print(f"{n}: {', '.join(found)}")
sys.exit(1 if flagged else 0)
