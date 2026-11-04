#!/usr/bin/env python3
"""Replay the owner's rule that a push is sent only while Remote Control is active in the session (#1202), on session records in a temporary config folder,
and print `ok <case>` or `fail <case>: <what it saw>` per case; exit 1 on any fail.
- feed-push: the heartbeat's `feed` line asks for a PushNotification when the manager's session record names a bridge session, else tells the owner in the tab
- script-push: print-remote-control.py prints `active` or `inactive` by the same record

usage: replay-remote-push.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
work = pathlib.Path(tempfile.mkdtemp(prefix="remote-push-"))
sys.path.insert(0, str(ROOT / "lib"))
failed = []


def record(bridge):
    sessions = work / "claude" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / "1.json").write_text(json.dumps({"sessionId": "s1", "name": "x-manager", **({"bridgeSessionId": "session_b"} if bridge else {})}))


def feed_line():
    import team_gaps
    me = {"name": "x-manager", "workspace_id": "w1", "agent_session": {"value": "s1"}}
    issue = {"number": 7, "title": "Probe", "state": "OPEN", "parent": None, "labels": [], "body": "", "comments": []}
    comment = {"url": "https://example.com/c/1", "body": "REPORTED: landed\n"}
    data = {"found": [], "everything": [], "prs": [], "outside": [], "feed": [(issue, comment)], "links": []}
    return [line for line in team_gaps.manager_actions(me, [me], data, set()) if line.startswith("feed ")]


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {detail}", flush=True)
    if not ok:
        failed.append(name)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    os.environ.update({"CLAUDE_CONFIG_DIR": str(work / "claude"), "TEAMWORK_BOARD": "files", "TEAMWORK_BOARD_DIR": str(work / "board")})
    record(bridge=True)
    on = feed_line()
    record(bridge=False)
    off = feed_line()
    step("feed-push", len(on) == 1 and "by PushNotification" in on[0] and len(off) == 1 and "PushNotification" not in off[0] and "send no push" in off[0], on + off)
    outputs = []
    for bridge in (True, False):
        record(bridge)
        outputs.append(subprocess.run([sys.executable, str(HERE.parent / "scripts" / "print-remote-control.py")], capture_output=True, text=True,
                                      env={**os.environ, "CLAUDE_CODE_SESSION_ID": "s1"}).stdout)
    step("script-push", outputs[0].startswith("active") and outputs[1].startswith("inactive"), outputs)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
