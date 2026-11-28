#!/usr/bin/env python3
"""Run the heartbeat `print-team-gaps.py --polls <n>` as a manager on a sandbox repository with a git board and the fake herdr, over a worker whose session runs
`/bin/sh -c`, a system binary `ps -E` shows no environment for, with one process that sleeps and one that spins beside it, as a pipeline of one tool call does. Under a limit of 1.5 s
with no CPU the heartbeat prints no `stuck` line, since the call as a whole uses CPU. Print `PASS` or `FAIL: <what it saw>`, and exit 1 on FAIL.

usage: replay-shell-pipeline-runs.py"""
import pathlib
import subprocess
import sys
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

MONITOR = ROOT / "monitors" / "print-team-gaps.py"
SPIN, SLEEP = 'import time; t = time.time(); exec("while time.time() - t < 120: pass")', "import time; time.sleep(120)"  # each ends on its own, so a killed runner leaves none
POLLS = 15  # 0.3 s apart, so a run is read for longer than the 1.5 s limit
WAIT_SECONDS = 60


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("shell-pipeline-runs-") as work:
        token = f"sess-pipeline-{uuid.uuid4().hex}"
        sandbox = replay_probe.Sandbox(work, [replay_probe.agent("x-manager", 1, "working"), replay_probe.agent("c-pipe-worker", 2, "working", agent_session={"value": token})])
        call = f'"{sys.executable}" -c \'{SPIN}\' | "{sys.executable}" -c \'{SLEEP}\''
        started = replay_probe.Group(["/bin/sh", "-c", call], env={**sandbox.environment, "CLAUDE_CODE_SESSION_ID": token},
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(1.5)
            done = sandbox.python(MONITOR, "--polls", POLLS, pane="w1:p1", timeout=WAIT_SECONDS, TEAMWORK_MONITOR_POLL="0.3", TEAMWORK_STUCK_SECONDS="1.5")
        finally:
            started.kill()
            started.wait()
    if done.returncode != 0:
        return replay_probe.fail(f"print-team-gaps.py --polls {POLLS} ended {done.returncode}: {done.stderr.strip()[-300:]}")
    stuck = [line for line in done.stdout.splitlines() if line.startswith("stuck ")]
    return replay_probe.fail(f"a pipeline that spins was called stuck: {stuck}") if stuck else replay_probe.Cases().finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
