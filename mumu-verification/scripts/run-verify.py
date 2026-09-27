#!/usr/bin/env python3
"""PreToolUse on Bash and Stop: in a repo holding a `spec/` model, run the spec skill's gate before a `git commit`
and before a stop that leaves changes, refusing either while it fails, with its FAIL lines. A repo without one is
commit-nudge.py's.
A stop already held once goes on, so a gate the session cannot turn green never traps it. Exit 0 always.
"""
import json
import os
import pathlib
import shlex
import subprocess
import sys

PLUGIN = pathlib.Path(__file__).resolve().parent.parent
GATE = PLUGIN / "skills" / "spec" / "scripts" / "verify.sh"
sys.path.insert(0, str(PLUGIN / "lib"))
from fit import COMMIT  # noqa: E402


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True).stdout.strip()


def main():
    call = json.load(sys.stdin)
    stop = call.get("hook_event_name") == "Stop"
    cwd = call.get("cwd") or os.getcwd()
    m = None if stop else COMMIT.search((call.get("tool_input") or {}).get("command", ""))
    if m and m.group(3):
        cwd = os.path.join(cwd, os.path.expanduser(shlex.split(m.group(3))[0]))
    root = git(cwd, "rev-parse", "--show-toplevel")
    if not (root and any(pathlib.Path(root, "spec").rglob("*.als"))) or not (m or stop and not call.get("stop_hook_active") and git(root, "status", "--porcelain")):
        return
    p = subprocess.run([str(GATE)], cwd=root, capture_output=True, text=True)
    fails = [l for l in (p.stdout + p.stderr).splitlines() if l.startswith("FAIL")] or p.stderr.splitlines()[-5:]
    why = "verify.sh fails:\n" + "\n".join(fails) + "\nFix the change or the model until it passes; never loosen an expect."
    if p.returncode:
        print(json.dumps({"decision": "block", "reason": why} if stop else {"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": why}}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a crash refuses nothing
        print(f"run-verify.py: {type(e).__name__}: {e}; gate not run", file=sys.stderr)
    sys.exit(0)
