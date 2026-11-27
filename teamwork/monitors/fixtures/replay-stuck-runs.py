#!/usr/bin/env python3
"""Run the heartbeat `print-team-gaps.py --polls <n>` as a manager on a sandbox repository with a git board and the fake herdr, over three workers
each running one process under its session id: `c-sleep`, which sleeps at no CPU; `c-busy`, which spins; and `c-check`, which spins with
`run-criteria.py` in its command. Under limits of 1.5 s with no CPU and 1 s for a check, only `c-sleep` gets a `stuck` line and only `c-check` a `slow`
line; under the default limits of 15 and 60 minutes none gets either. Print `PASS` or `FAIL: <what it saw>`, and exit 1 on FAIL.

usage: replay-stuck-runs.py"""
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

MONITOR = ROOT / "monitors" / "print-team-gaps.py"
CODE = {"sleep": "import time; time.sleep(120)", "busy": "while True: pass", "check": "while True: pass"}
POLLS = 15  # 0.3 s apart, so a run is read for longer than the 1.5 s limit
WAIT_SECONDS = 60


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("stuck-runs-") as work:
        return replay(work)


def replay(work):
    agents = [replay_probe.agent("x-manager", 1, "working"),
              *[replay_probe.agent(f"c-{name}-worker", pane, "working", agent_session={"value": f"sess-{name}"}) for pane, name in enumerate(CODE, 2)]]
    sandbox = replay_probe.Sandbox(work, agents)
    started = [replay_probe.Group([sys.executable, "-c", code, *(["run-criteria.py"] if name == "check" else [])],
                                  env={**sandbox.environment, "CLAUDE_CODE_SESSION_ID": f"sess-{name}"},
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for name, code in CODE.items()]
    try:
        time.sleep(1.5)  # so the check's elapsed time, which `ps` gives in whole seconds, passes its 1 s limit
        short = sandbox.python(MONITOR, "--polls", POLLS, pane="w1:p1", timeout=WAIT_SECONDS, TEAMWORK_MONITOR_POLL="0.3",
                               TEAMWORK_STUCK_SECONDS="1.5", TEAMWORK_SLOW_SECONDS="1")
        default = sandbox.python(MONITOR, "--polls", POLLS, pane="w1:p1", timeout=WAIT_SECONDS, TEAMWORK_MONITOR_POLL="0.3")
    finally:
        for process in started:
            process.kill()
            process.wait()
    for done in (short, default):
        if done.returncode != 0:
            return replay_probe.fail(f"print-team-gaps.py --polls {POLLS} ended {done.returncode}: {done.stderr.strip()[-300:]}")
    seen = sorted(line.split(":")[0] for line in short.stdout.splitlines() if line.startswith(("stuck ", "slow ")))
    wrong = [line for line in default.stdout.splitlines() if line.startswith(("stuck ", "slow "))]
    if seen != ["slow c-check-worker", "stuck c-sleep-worker"] or wrong:
        return replay_probe.fail(f"short limits gave {seen}, default limits gave {wrong}: {short.stdout.strip()[-600:]}")
    return replay_probe.Cases().finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
