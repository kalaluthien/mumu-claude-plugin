#!/usr/bin/env python3
"""Send a worker's `cd` into the live checkout through route-event.py from a worktree of a temporary repository, run the command its refusal offers, and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-cd-refusal.py --case <name>
- git: `cd <live>/teamwork && git ls-files` is denied with a command that has no cd and prints what the cd command printed
- path: `cd <live>/teamwork && cat note.txt | head -1 && ls .` is denied with a command that has no cd and prints what the cd command printed
- subshell: `(cd <live>/teamwork && cat note.txt)` is denied with a command that has no cd and prints what the cd command printed
Every case also sends the commands of UNSAFE, which write, cd again or hold a word the rewrite cannot keep, and each must be denied with no command offered."""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROUTE = pathlib.Path(__file__).resolve().parents[1] / "route-event.py"
COMMANDS = {"git": "cd {live}/teamwork && git ls-files",
            "path": "cd {live}/teamwork && cat note.txt | head -1 && ls .",
            "subshell": "(cd {live}/teamwork && cat note.txt)"}


UNSAFE = ("cp note.txt copy.txt", "git add . && git commit -m x", "git log && cd .. && git log", "cat note.txt; cd ..; git log", "grep '' note.txt",
          "sed -i '' s/a/b/ note.txt", "git log abc#1 -- note.txt", "cat ~/x note.txt", "rm -rf sub", "ls", "cat note.txt | tee new.txt", "sort -o out note.txt", "grep -f note.txt note.txt", "git log --output=out.txt")


def setup():
    work = pathlib.Path(tempfile.mkdtemp(prefix="cd-refusal-"))
    live = work.resolve() / "live"
    (live / "teamwork").mkdir(parents=True)
    (live / "teamwork" / "note.txt").write_text("the live note\n")
    for command in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "first"]):
        subprocess.run(["git", *command], cwd=live, check=True, capture_output=True)
    worktree = live / ".claude" / "worktrees" / "w"
    worktree.mkdir(parents=True)
    (work / "bin").mkdir()
    (work / "bin" / "herdr").write_text(f"#!/bin/sh\necho '{json.dumps({'result': {'agents': [{'pane_id': 'p1', 'name': 't-worker'}]}})}'\n")
    (work / "bin" / "herdr").chmod(0o755)
    return work, live, worktree


def hook_reason(work, worktree, command):
    event = {"hook_event_name": "PreToolUse", "cwd": str(worktree), "tool_input": {"command": command}}
    env = {**os.environ, "PATH": f"{work / 'bin'}:{os.environ['PATH']}", "HERDR_PANE_ID": "p1"}
    out = subprocess.run([str(ROUTE)], input=json.dumps(event), capture_output=True, text=True, env=env).stdout
    hook = (json.loads(out) if out.strip() else {}).get("hookSpecificOutput", {})
    return hook.get("permissionDecision") == "deny" and hook.get("permissionDecisionReason", "")


def main(args):
    if len(args) != 2 or args[0] != "--case" or args[1] not in COMMANDS:
        print(__doc__, file=sys.stderr)
        return 2
    work, live, worktree = setup()
    command = COMMANDS[args[1]].format(live=live)
    reason = hook_reason(work, worktree, command)
    if not reason:
        print("FAIL: the hook did not deny the cd")
        return 1
    offered = re.search(r"run this instead: `([^`]+)`", reason)
    if not offered:
        print(f"FAIL: the refusal names no full command: {reason!r}")
        return 1
    if re.search(r"(^|[;&|({]|\s)(cd|pushd)\s", offered[1]):
        print(f"FAIL: the offered command still has a cd: {offered[1]}")
        return 1
    for risky in UNSAFE:
        said = hook_reason(work, worktree, f"cd {live}/teamwork && {risky}")
        if not said or "run this instead" in said:
            print(f"FAIL: {risky!r} " + ("was not denied" if not said else "was offered a rewrite: " + said[said.index("run this instead"):][:200]))
            return 1
    want = subprocess.run(["bash", "-c", command], cwd=worktree, capture_output=True, text=True)
    got = subprocess.run(["bash", "-c", offered[1]], cwd=worktree, capture_output=True, text=True)
    if (got.returncode, got.stdout) != (want.returncode, want.stdout) or not want.stdout:
        print(f"FAIL: the offered command printed {got.stdout!r} (exit {got.returncode}), not {want.stdout!r} (exit {want.returncode}): {got.stderr.strip()[-200:]}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
