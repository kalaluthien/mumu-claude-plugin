#!/usr/bin/env python3
"""Start route-event.py's SessionStart in a worker's worktree, under a stand-in `claude` started as start-session.py starts the worker, as a bare
`claude -p` and as a session renamed to the worker, with herdr recording each as the pane's session, and print `PASS` as the last line when only the
started and the renamed one are told the worker role, else `FAIL: <what differed>` and exit 1.

usage: replay-session-role.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import agent  # noqa: E402
import replay_probe  # noqa: E402

ROUTE = pathlib.Path(__file__).resolve().parents[1] / "route-event.py"
NAME = "t-worker"
SESSION = "00000000-0000-4000-8000-000000000001"
ROLE_LINE = f"You are {NAME}, a teamwork worker"
# each case: the stand-in's options, whether the transcript holds the worker's title, whether the role line must come
CASES = {"started": (agent.command(NAME, "plugin", "opus", "high", []), False, True),
         "bare": (["-p", "probe", "--model", "haiku"], False, False),
         "renamed": (["--model", "opus"], True, True)}


def told(work, options, titled):
    worktree = work / "live" / ".claude" / "worktrees" / NAME
    worktree.mkdir(parents=True, exist_ok=True)
    transcript = work / f"{SESSION}.jsonl"
    transcript.unlink(missing_ok=True)
    if titled:
        transcript.write_text(json.dumps({"type": "custom-title", "customTitle": NAME, "sessionId": SESSION}, separators=(",", ":")) + "\n")
    stubs = replay_probe.fake_herdr(work, [{"pane_id": "p1", "name": NAME, "agent": "claude", "agent_session": {"value": SESSION}}])
    event = {"hook_event_name": "SessionStart", "source": "startup", "session_id": SESSION, "cwd": str(worktree), "transcript_path": str(transcript)}
    argv = replay_probe.as_claude([ROUTE], options, work / "stand-in")
    environment = {**os.environ, "PATH": f"{stubs}:{os.environ['PATH']}", "HERDR_PANE_ID": "p1"}
    out = subprocess.run(argv, cwd=worktree, env=environment, input=json.dumps(event), capture_output=True, text=True, timeout=60).stdout
    return ROLE_LINE in out


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as folder:
        wrong = [f"{case} {'got no' if expected else 'got the'} worker role" for case, (options, titled, expected) in CASES.items()
                 if told(pathlib.Path(folder), options, titled) != expected]
    if wrong:
        return replay_probe.fail("; ".join(wrong))
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
