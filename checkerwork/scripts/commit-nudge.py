#!/usr/bin/env python3
"""PostToolUse on Bash: after a `git commit` whose change fits a playbook of `checkerwork:contract`, unloaded, ask for it.

The change is the commit at HEAD, read after the call, since a worker often writes the files and commits in one
Bash call; each changed file is matched by `lib/fit.py` against its path and its added lines. The skill is loaded when
the transcript holds a Skill call or typed command naming `checkerwork:contract`. It is asked for once per session,
recorded under the plugin's data dir, naming each fitting playbook. Exit 0 always: the ask is the JSON `decision: block`, whose reason reaches the
model; a crash asks nothing and names itself on stderr.
"""
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
from fit import CALL, COMMIT, PLAYBOOKS, added, fits  # noqa: E402


def committed(cwd):
    """{"/" + repo-relative path: added text} of the commit at HEAD."""
    show = ["git", "-C", cwd, "show", "--no-renames", "--no-color", "--src-prefix=a/", "--dst-prefix=b/", "--format=", "-p", "HEAD"]
    return added(subprocess.run(show, capture_output=True, text=True, check=True).stdout)


def loaded(transcript):
    """Whether the transcript shows a Skill call or a typed command for `checkerwork:contract`."""
    try:
        lines = open(transcript, errors="replace")
    except (OSError, TypeError):
        return False
    with lines:
        return any(('"Skill"' in line or "<command-name>" in line) and CALL.search(line) for line in lines)


def main():
    call = json.load(sys.stdin)
    m = COMMIT.search((call.get("tool_input") or {}).get("command", ""))
    if not m:
        return
    cwd = call.get("cwd") or os.getcwd()
    if m.group(3):
        cwd = os.path.join(cwd, os.path.expanduser(shlex.split(m.group(3))[0]))
    fit = {}
    for path, text in committed(cwd).items():
        for playbook in fits(path, text):
            fit.setdefault(playbook, path)
    data = pathlib.Path(os.environ.get("CLAUDE_PLUGIN_DATA") or tempfile.gettempdir()) / "commit-nudge"
    mark = data / re.sub(r"[^\w-]", "_", str(call.get("session_id", "none")))
    if not fit or mark.exists() or loaded(call.get("transcript_path")):
        return
    data.mkdir(parents=True, exist_ok=True)
    mark.write_text("contract")
    why = "; ".join(f"{p}.md ({fit[p][1:]})" for p in PLAYBOOKS if p in fit)
    print(json.dumps({"decision": "block", "reason": (
        f"This commit's change fits checkerwork:contract's playbooks {why}, and the skill is not loaded in this session. "
        "Load it now with the Skill tool, even when your steps end at this commit, read those playbooks, and do what "
        "they ask where it applies in a new commit; asked once per session.")}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a crash asks nothing
        print(f"commit-nudge.py: {type(e).__name__}: {e}; commit not judged", file=sys.stderr)
    sys.exit(0)
