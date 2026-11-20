#!/usr/bin/env python3
"""Run `session.own_name()` under a stand-in `claude` in a pane whose recorded session is the caller's, as a session started as a worker, as a bare
`claude -p` and as a session renamed to the worker, and print `PASS` as the last line when only the started and the renamed one get the worker's name,
else `FAIL: <what differed>` and exit 1.

usage: replay-own-name.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

LIB = pathlib.Path(__file__).resolve().parents[3] / "lib"
sys.path.insert(0, str(LIB))
import agent  # noqa: E402
import replay_probe  # noqa: E402

NAME = "t-worker"
SESSION = "00000000-0000-4000-8000-000000000002"
# each case: the stand-in's options, whether the transcript holds the worker's title, the name it must get
CASES = {"started": (agent.command(NAME, "plugin", "opus", "high", []), False, NAME),
         "bare": (["-p", "probe", "--model", "haiku"], False, None),
         "renamed": (["--model", "opus"], True, NAME)}
LOOKUP = f"import sys; sys.path.insert(0, {str(LIB)!r}); import session; print(session.own_name())"


def named(work, options, titled):
    config = work / "config" / "projects" / "folder"
    config.mkdir(parents=True, exist_ok=True)
    transcript = config / f"{SESSION}.jsonl"
    transcript.unlink(missing_ok=True)
    if titled:
        transcript.write_text(json.dumps({"type": "custom-title", "customTitle": NAME, "sessionId": SESSION}, separators=(",", ":")) + "\n")
    stubs = replay_probe.fake_herdr(work, [{"pane_id": "p1", "name": NAME, "agent": "claude", "agent_session": {"value": SESSION}}])
    environment = {**os.environ, "PATH": f"{stubs}:{os.environ['PATH']}", "HERDR_PANE_ID": "p1", "CLAUDE_CODE_SESSION_ID": SESSION,
                   "CLAUDE_CONFIG_DIR": str(work / "config")}
    argv = replay_probe.as_claude([sys.executable, "-c", LOOKUP], options, work / "stand-in")
    out = subprocess.run(argv, env=environment, capture_output=True, text=True, timeout=60).stdout.strip()
    return None if out == "None" else out


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as folder:
        wrong = [f"{case} got {got!r}, not {expected!r}" for case, (options, titled, expected) in CASES.items()
                 if (got := named(pathlib.Path(folder), options, titled)) != expected]
    if wrong:
        return replay_probe.fail("; ".join(wrong))
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
