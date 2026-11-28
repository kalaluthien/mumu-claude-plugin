#!/usr/bin/env python3
"""Run run-criteria.py `--hunks` on a temporary git repository whose change edits three far lines of a data file, under a check that
logs its start and end and sleeps, at a 1-minute load this runner sets. Print `ok <case>` or `fail <case>: <detail>` per case, then
`PASS` or `FAIL`, and exit 1 on any failure:
- `idle`: under a load of 0 the sweep's checks overlap;
- `loaded`: under a load above the CPU count they run one at a time, each starting within 3 s of the previous one's end;
- `woken`: under that load, from 1.5 s after a revert's check starts the load is 0 and 2 s later, then in a second sweep 2.8 s later,
  another process marks a job end; each time the next check starts within 0.7 s of the mark, not before it, while the first still runs,
  so neither the first's end nor a timer of any one period, which would start it within 0.7 s of both marks, woke it.

usage: replay-hunk-pacing.py"""
import os
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
# the load the sweep reads is the number in the file TEAMWORK_FIXTURE_LOAD names, so a case sets the machine's load
SITE = "import os\nif os.environ.get('TEAMWORK_FIXTURE_LOAD'):\n    os.getloadavg = lambda: (float(open(os.environ['TEAMWORK_FIXTURE_LOAD']).read()),) * 3\n"
SLOW = "import os, sys, time\nlog = sys.argv[1]\nopen(log, 'a').write('start %f\\n' % time.time())\ntime.sleep(7)\nopen(log, 'a').write('end %f\\n' % time.time())\nprint('ok')\n"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("hunk-pacing-") as work:
        box = replay_probe.Sandbox(work)
        site, log, load, config = box.work / "site", box.work / "checks.log", box.work / "load", box.work / "config"
        site.mkdir()
        (site / "sitecustomize.py").write_text(SITE)
        (box.repository / "slow.py").write_text(SLOW)
        (box.repository / "data.txt").write_text("".join(f"line {n}\n" for n in range(40)))
        box.git("add", "-A")
        box.git("commit", "-qm", "data")
        box.git("checkout", "-qb", "change")
        lines = [f"line {n}\n" if n not in (0, 20, 39) else f"changed {n}\n" for n in range(40)]
        (box.repository / "data.txt").write_text("".join(lines))
        box.git("commit", "-qam", "change")
        body = replay_probe.write_text(box.work, "body.md", f"## Definition of done\n\n1. [check] **The slow check passes**: `python3 slow.py {log}` prints `ok`; on base nothing.\n")
        environment = {**box.environment, "PYTHONPATH": str(site), "TEAMWORK_FIXTURE_LOAD": str(load), "CLAUDE_CONFIG_DIR": str(config)}

        def sweep(level, during=None):
            load.write_text(str(level))
            log.write_text("")
            running = subprocess.Popen([sys.executable, str(SCRIPT), "--hunks", "--fresh", "--ref", "main", str(body)], cwd=box.repository, env=environment,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if during:
                during()
            out = running.communicate(timeout=300)[0]
            events = sorted((float(when), kind) for kind, when in (line.split() for line in log.read_text().splitlines()))
            return events, out

        def overlaps(events):
            running, most = 0, 0
            for _, kind in events:
                running += 1 if kind == "start" else -1
                most = max(most, running)
            return most

        events, out = sweep(0)
        cases.step("idle", overlaps(events) > 1, (events, out))
        many = (os.cpu_count() or 1) * 10
        events, out = sweep(many)
        reverts = events[2:]  # the head's own check runs first, alone
        gaps = [later[0] - earlier[0] for earlier, later in zip(reverts[1::2], reverts[2::2])]
        cases.step("loaded", overlaps(events) == 1 and len(gaps) >= 2 and max(gaps) < 3, (events, out))

        def fall(pause):
            while "start" not in log.read_text() or log.read_text().count("start") < 2:
                time.sleep(0.2)
            time.sleep(1.5)  # past the gate's 1 s spacing, so its next start waits on the mark alone
            load.write_text("0")
            time.sleep(pause)
            config.mkdir(exist_ok=True)
            (config / "check-job-ends").touch()
            marked.append(time.time())

        woken = []
        for pause in (2, 2.8):
            marked = []
            events, out = sweep(many, lambda: fall(pause))
            later = [when for when, kind in events if kind == "start" and marked and when > marked[0] - pause]
            woken.append((bool(later and 0 <= later[0] - marked[0] < 0.7 and overlaps(events) > 1), marked, events, out))
        cases.step("woken", all(held for held, *_ in woken), woken)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
