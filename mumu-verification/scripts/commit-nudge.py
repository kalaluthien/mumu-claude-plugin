#!/usr/bin/env python3
"""PostToolUse on Bash: after a `git commit` whose change fits a mumu-verification skill the session has not loaded, ask for it.

The change is the commit at HEAD, read after the call, since a worker often writes the files and commits in one
Bash call; each changed file is matched by `lib/fit.py` against its path and its added lines. A skill is loaded when
the transcript holds a Skill call naming `mumu-verification:<skill>`. Each skill is asked for once per session,
recorded under the plugin's data dir. Exit 0 always: the ask is the JSON `decision: block`, whose reason reaches the
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
from fit import CALL, COMMIT, SKILLS, added, fits  # noqa: E402


def committed(cwd):
    """{"/" + repo-relative path: added text} of the commit at HEAD."""
    show = ["git", "-C", cwd, "show", "--no-renames", "--no-color", "--src-prefix=a/", "--dst-prefix=b/", "--format=", "-p", "HEAD"]
    return added(subprocess.run(show, capture_output=True, text=True, check=True).stdout)


def loaded(transcript):
    """The mumu-verification skills the transcript shows a Skill call or a typed command for."""
    got = set()
    try:
        lines = open(transcript, errors="replace")
    except (OSError, TypeError):
        return got
    with lines:
        for line in lines:
            if '"Skill"' in line or "<command-name>" in line:
                got |= set(CALL.findall(line))
    return got


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
        for skill in fits(path, text):
            fit.setdefault(skill, path)
    data = pathlib.Path(os.environ.get("CLAUDE_PLUGIN_DATA") or tempfile.gettempdir()) / "commit-nudge"
    mark = data / re.sub(r"[^\w-]", "_", str(call.get("session_id", "none")))
    asked = set(mark.read_text().split()) if mark.exists() else set()
    missing = [s for s in SKILLS if s in fit and s not in asked]
    missing = [s for s in missing if s not in loaded(call.get("transcript_path"))] if missing else []
    if not missing:
        return
    data.mkdir(parents=True, exist_ok=True)
    mark.write_text(" ".join(sorted(asked | set(missing))))
    why = "; ".join(f"mumu-verification:{s} ({fit[s][1:]})" for s in missing)
    print(json.dumps({"decision": "block", "reason": (
        f"This commit's change fits {why}, not loaded in this session. Load each now with the Skill tool, even when "
        "your steps end at this commit, and do what it asks where it applies in a new commit; asked once per skill.")}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a crash asks nothing
        print(f"commit-nudge.py: {type(e).__name__}: {e}; commit not judged", file=sys.stderr)
    sys.exit(0)
