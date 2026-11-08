#!/usr/bin/env python3
"""Replay one Bash command's PreToolUse event through route-event.py as a worker in a fresh git repo, and print what the hook did: deny, other or silent.

usage: replay-event.py <command> [text]
`REPLAY_SESSION_ID` in the environment is the event's session id, so a repeat call can meet the hook's once-per-session reminders.
With `text` it prints the hook's message (the deny reason and the context) on the lines after the verdict.
A fake herdr names the session t-worker."""
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "lib"))
import replay_probe  # noqa: E402


def main(args):
    if not args or len(args) > 2 or args[1:] not in ([], ["text"]):
        print(__doc__, file=sys.stderr)
        return 2
    command = args[0]
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "repo").mkdir()
    stubs = replay_probe.fake_herdr(folder, [{"pane_id": "p1", "name": "t-worker"}])
    subprocess.run(["git", "init", "-q", str(folder / "repo")], check=True)
    event = {"hook_event_name": "PreToolUse", "cwd": str(folder / "repo"), "tool_input": {"command": command},
             "session_id": os.environ.get("REPLAY_SESSION_ID")}
    got = replay_probe.route_event(HERE.parent / "route-event.py", event, stubs)
    hook = got.get("hookSpecificOutput", {})
    print("deny" if hook.get("permissionDecision") == "deny" else "other" if got else "silent")
    if args[1:] == ["text"]:
        print(*[message for message in (hook.get("permissionDecisionReason"), hook.get("additionalContext")) if message], sep="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
