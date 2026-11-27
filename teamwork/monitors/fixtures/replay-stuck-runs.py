#!/usr/bin/env python3
"""Run the heartbeat `print-team-gaps.py --polls <n>` as a manager on a sandbox repository with a git board and the fake herdr, over workers that each run
processes under their own session id, made new on each run so two copies of this runner never see each other: `c-sleep`, which sleeps at no CPU; `c-busy`,
which spins; `c-check`, which spins with `run-criteria.py` in its command; `c-wait`, which sleeps while a child of it spins; `c-nest`, which sleeps with a child
that sleeps; and `c-none`, whose session id is empty. Under limits of 1.5 s with no CPU and 1 s for a check, only `c-sleep` and `c-nest`, once each, get a
`stuck` line, whose command shows the process's words without their paths or environment, and only `c-check` a `slow` line; under the default limits of 15 and
60 minutes none gets either. Print `PASS` or `FAIL: <what it saw>`, and exit 1 on FAIL.

usage: replay-stuck-runs.py"""
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
CODE = {"none": None, "sleep": SLEEP, "busy": SPIN, "check": SPIN,
        "wait": f"import subprocess, sys; subprocess.Popen([sys.executable, '-c', '{SPIN}']); {SLEEP}",
        "nest": f"import subprocess, sys; subprocess.Popen([sys.executable, '-c', '{SLEEP}']); {SLEEP}"}
POLLS = 15  # 0.3 s apart, so a run is read for longer than the 1.5 s limit
WAIT_SECONDS = 60


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("stuck-runs-") as work:
        return replay(work)


def replay(work):
    token = uuid.uuid4().hex
    session = {name: "" if name == "none" else f"sess-{name}-{token}" for name in CODE}
    agents = [replay_probe.agent("x-manager", 1, "working"),
              *[replay_probe.agent(f"c-{name}-worker", pane, "working", agent_session={"value": session[name]}) for pane, name in enumerate(CODE, 2)]]
    sandbox = replay_probe.Sandbox(work, agents)
    started = [replay_probe.Group([sys.executable, "-c", code, *(["run-criteria.py"] if name == "check" else [])],
                                  env={**sandbox.environment, "CLAUDE_CODE_SESSION_ID": session[name]},
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for name, code in CODE.items() if code]
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
    # the command shown is the process's own words, each path cut to its file name and the environment `ps -E` appends left out
    shown = [line for line in short.stdout.splitlines() if line.startswith("stuck c-sleep")]
    if seen != ["slow c-check-worker", "stuck c-nest-worker", "stuck c-sleep-worker"] or wrong or not all("(`python3 -c import time; time.sleep(120)`)" in line for line in shown):
        return replay_probe.fail(f"short limits gave {seen}, default limits gave {wrong}: {short.stdout.strip()[-600:]}")
    return replay_probe.Cases().finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
