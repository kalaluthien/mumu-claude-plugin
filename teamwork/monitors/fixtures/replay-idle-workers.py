#!/usr/bin/env python3
"""Run the heartbeat `print-team-gaps.py --polls <n>` as a manager on a sandbox repository with a git board and the fake herdr, over five workers at their
prompt that hold nothing open: `b-busy`, with a process still running under its session id, as a check it detached with `( ... ) &` does; `b-minutes` and `b-hours`, whose
only process is one of 21 minutes or 11 hours 59 minutes, which a stand-in `ps` adds to the real listing; `b-free`, whose only processes are its own heartbeat and processes older
than 12 hours in the forms `dd-hh:mm:ss` and `hh:mm:ss`; and `b-empty`, whose session id is empty. Wait for the heartbeat to end, print `PASS` when only `b-free` and `b-empty`
got an `idle` line, else `FAIL: <what it saw>`, and exit 1 on FAIL.

usage: replay-idle-workers.py"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

MONITOR = ROOT / "monitors" / "print-team-gaps.py"
BUSY, FREE, MINUTES, HOURS = "sess-busy", "sess-free", "sess-minutes", "sess-hours"
# processes a stand-in `ps` lists beside the real ones, by the form of the elapsed time of `ps`: two young, in the minutes and the hours forms, and two older than 12 hours
EXTRA_PROCESSES = (f"9001 21:05 python3 check CLAUDE_CODE_SESSION_ID={MINUTES} HOME=/x\n"
                   f"9002 11:59:00 python3 check CLAUDE_CODE_SESSION_ID={HOURS} HOME=/x\n"
                   f"9003 1-00:00:05 python3 left CLAUDE_CODE_SESSION_ID={FREE} HOME=/x\n"
                   f"9004 13:00:00 python3 left CLAUDE_CODE_SESSION_ID={FREE} HOME=/x\n")
POLLS = 5  # polls, each of which would print an `idle` line it wrongly saw
WAIT_SECONDS = 60


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("idle-workers-") as work:
        return replay(work)


def replay(work):
    agents = [replay_probe.agent(name, pane, status, **({"agent_session": {"value": session}} if session is not None else {}))
              for name, pane, status, session in (("x-manager", 1, "working", None), ("b-busy-worker", 2, "idle", BUSY), ("b-free-worker", 3, "idle", FREE),
                                                  ("b-empty-worker", 4, "idle", ""), ("b-minutes-worker", 5, "idle", MINUTES), ("b-hours-worker", 6, "idle", HOURS))]
    sandbox = replay_probe.Sandbox(work, agents)
    extra = replay_probe.write_text(work, "extra-processes.txt", EXTRA_PROCESSES)
    replay_probe.write_text(sandbox.bin, "ps", f'#!/bin/sh\ncase "$*" in *etime=*) /bin/ps "$@"; cat "{extra}";; *) exec /bin/ps "$@";; esac\n').chmod(0o755)
    started = []

    def detach(session, *words):
        started.append(replay_probe.Group([sys.executable, "-c", "import time; time.sleep(120)", *words], env={**sandbox.environment, "CLAUDE_CODE_SESSION_ID": session},
                                          stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))

    detach(BUSY)
    detach(FREE, str(MONITOR) + " ")  # a worker's own heartbeat
    try:
        done = sandbox.python(MONITOR, "--polls", POLLS, pane="w1:p1", timeout=WAIT_SECONDS, TEAMWORK_MONITOR_POLL="0.3")
    finally:
        for process in started:
            process.kill()
            process.wait()
    if done.returncode != 0:
        return replay_probe.fail(f"print-team-gaps.py --polls {POLLS} ended {done.returncode}: {done.stderr.strip()[-300:]}")
    wrong = [name for name in ("busy", "minutes", "hours") if f"idle b-{name}-worker" in done.stdout]
    missed = [name for name in ("free", "empty") if f"idle b-{name}-worker" not in done.stdout]
    if wrong or missed:
        return replay_probe.fail(f"idle lines for {wrong} and none for {missed}: {done.stdout.strip()[-500:]}")
    return replay_probe.Cases().finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
