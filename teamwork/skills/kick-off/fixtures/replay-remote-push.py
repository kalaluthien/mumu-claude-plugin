#!/usr/bin/env python3
"""Replay the owner's rule that a push is sent only while Remote Control is active in the session (#1202), on session records in a scratch Claude config folder,
a git board and the fake herdr, and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`; exit 1 on any fail.
- feed-push: the heartbeat's `feed` line for a worker's report asks for a PushNotification when the manager's session record names a bridge session, else tells the owner in the tab
- script-push: print-remote-control.py prints `active` or `inactive` by the same record

usage: replay-remote-push.py"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

USE_BOARD = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
REMOTE_CONTROL = ROOT / "skills" / "kick-off" / "references" / "adapters" / "message-claude" / "scripts" / "print-remote-control.py"
POLLS = 12  # about twice the polls the report below takes to reach the feed


def record(sandbox, bridge):
    sessions = sandbox.config / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / "1.json").write_text(json.dumps({"sessionId": "s1", "name": "x-manager", **({"bridgeSessionId": "session_b"} if bridge else {})}))


def feed_lines(sandbox, work, root, report):
    """The `feed` lines a manager's heartbeat prints for REPORT, which the worker posts on ROOT once the heartbeat's first poll read the board, since a first read feeds nothing old."""
    with sandbox.monitor("w1:p1", POLLS, work / f"{report}.log") as live:
        # a manager's poll lists the sessions once, and once more before a line, so a third list opens the second poll at the latest
        live.until(lambda: live.lists() >= 3)
        sandbox.python(USE_BOARD, "comment", root, "--reported", report, pane="w1:p2")
        code = live.end()
    return [line for line in live.text().splitlines() if line.startswith("feed ")] + ([] if code == 0 else [f"exit {code}"])

def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("remote-push-") as work:
        sandbox = replay_probe.Sandbox(work, [replay_probe.agent("x-manager", 1, "working", agent_session={"value": "s1"}), replay_probe.agent("r-worker", 2, "working")])
        body = replay_probe.write_text(work, "body.md", "Probe the push.\n")
        root = sandbox.python(USE_BOARD, "file", "--title", "Probe a root", "--body", body, "--label", "scope:x", pane="w1:p1").stdout.strip().rsplit("/", 1)[-1].removesuffix(".json")
        sandbox.python(USE_BOARD, "hold", root, "--holders", "r-worker", pane="w1:p1")
        record(sandbox, bridge=True)
        on = feed_lines(sandbox, work, root, "landed-on")
        record(sandbox, bridge=False)
        off = feed_lines(sandbox, work, root, "landed-off")
        cases.step("feed-push", len(on) == 1 and "by PushNotification" in on[0] and len(off) == 1 and "PushNotification" not in off[0] and "send no push" in off[0], on + off)
        outputs = []
        for bridge in (True, False):
            record(sandbox, bridge)
            outputs.append(sandbox.python(REMOTE_CONTROL, CLAUDE_CODE_SESSION_ID="s1").stdout)
        cases.step("script-push", outputs[0].startswith("active") and outputs[1].startswith("inactive"), outputs)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
