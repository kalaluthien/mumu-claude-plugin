#!/usr/bin/env python3
"""Cap a Bash call's long program output before the model reads it, keeping the whole output in a file the note names.

usage: cap-program-output.py < <PostToolUse event JSON>

Each of stdout and stderr over 50 lines keeps its first 40 and last 10 lines, then over 8,000 characters its first 6,400
and last 1,600, with a note naming a file of all of it; a call that reads a file (`cat`, `sed`, `head`, `tail`) passes
whole, since a cut file read was fetched again by range in #1159's replay. Replacing the output after the call, never
the command before it, keeps the owner's allow rules, the shell's state and the exit status as they were."""
import json
import re
import sys
import tempfile

LINES, HEAD_LINES, TAIL_LINES = 50, 40, 10
CHARS, HEAD_CHARS, TAIL_CHARS = 8000, 6400, 1600
FILE_READ = re.compile(r"\b(?:cat|sed|head|tail)\b")


def cap(output, stream):
    # a final line break ends the last line, so it neither counts as a line nor takes a kept one's place
    text, end = (output[:-1], "\n") if output.endswith("\n") else (output, "")
    lines = text.split("\n")
    head, tail = (lines[:HEAD_LINES], lines[-TAIL_LINES:]) if len(lines) > LINES else (lines, [])
    head, tail = "\n".join(head), "\n".join(tail)
    if len(head) + len(tail) > CHARS:
        whole = head + ("\n" + tail if tail else "")
        head, tail = whole[:HEAD_CHARS], whole[-TAIL_CHARS:]
    if not tail and head == text:
        return output
    with tempfile.NamedTemporaryFile("w", prefix=f"bash-{stream}-", suffix=".txt", delete=False) as saved:
        saved.write(output)
    # the line break between head and tail is the one the note takes over, so it counts as kept
    lines_cut = max(text.count("\n") - head.count("\n") - tail.count("\n") - 1, 0)
    note = (f"[output cap: {lines_cut} of {len(lines)} lines and {len(text) - len(head) - len(tail)} of "
            f"{len(text)} characters cut here; all of them are in {saved.name}; read a range of that file, not all of it]")
    return f"{head}\n{note}\n{tail}{end}"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 0
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    response = event.get("tool_response")
    command = (event.get("tool_input") or {}).get("command", "")
    if event.get("tool_name") != "Bash" or not isinstance(response, dict) or FILE_READ.search(command):
        return 0
    updated = dict(response)
    for stream in ("stdout", "stderr"):
        if isinstance(response.get(stream), str):
            updated[stream] = cap(response[stream], stream)
    # an unchanged output gets no rewrite, since a rewrite of the same text can overwrite another hook's real one
    if updated != response:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedToolOutput": updated}}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
