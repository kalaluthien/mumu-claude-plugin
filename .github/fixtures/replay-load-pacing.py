#!/usr/bin/env python3
"""Run `.github/check-repository.py` on a throwaway git root of three fixture runners that each log their start and end and sleep,
under a 1-minute load this runner sets, and print `ok <case>` or `FAIL <case>: <detail>` per case, then `PASS` as the last line when
all hold, else `FAIL`.

usage: replay-load-pacing.py

Cases:
- `idle`: under a load of 0 the runners overlap;
- `loaded`: under a load above the CPU count they run one at a time, each starting within 3 s of the previous one's end, which wakes it;
- `woken`: under that load, from 1.5 s after the first runner starts the load is 0 and 2 s later another process marks a job end; the next
  runner starts within 1.5 s of the mark, not before it, while the first still runs, so neither a timer nor the first's end woke it.
Exits 0 on `PASS`, 1 on `FAIL`, 2 with this text for any argument. Standard library only, Python 3.9."""

import os
import pathlib
import subprocess
import sys
import tempfile
import time

CHECK = pathlib.Path(__file__).resolve().parents[1] / "check-repository.py"
# the load the check reads is the number in the file LOAD_FILE names, so a case sets the machine's load
SITE = "import os\nif os.environ.get('LOAD_FILE'):\n    os.getloadavg = lambda: (float(open(os.environ['LOAD_FILE']).read()),) * 3\n"
RUNNER = "import os, time\nlog = os.environ['RUNNERS_LOG']\nopen(log, 'a').write('start {name} %f\\n' % time.time())\ntime.sleep({seconds})\nopen(log, 'a').write('end {name} %f\\n' % time.time())\n"


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    passed = True

    def step(name, held, detail):
        nonlocal passed
        print(f"ok {name}" if held else f"FAIL {name}: {' '.join(str(detail).split())[:600]}")
        passed = passed and held

    with tempfile.TemporaryDirectory() as scratch:
        scratch = pathlib.Path(scratch)
        root, site, log, load = scratch / "root", scratch / "site", scratch / "runs.log", scratch / "load"
        site.mkdir()
        (site / "sitecustomize.py").write_text(SITE)
        for name, seconds in (("a", 7), ("b", 7), ("c", 7)):
            path = root / "alpha" / "fixtures" / f"replay-{name}.py"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(RUNNER.format(name=name, seconds=seconds))
        subprocess.run(["git", "init", "-q", root], check=True)
        subprocess.run(["git", "-C", root, "add", "-A"], check=True)
        environment = {**os.environ, "RUNNERS_LOG": str(log), "LOAD_FILE": str(load), "PYTHONPATH": str(site), "CLAUDE_CONFIG_DIR": str(scratch / "config")}

        def check(level, during=None):
            load.write_text(str(level))
            log.write_text("")
            running = subprocess.Popen([sys.executable, str(CHECK), "--fresh", str(root)], env=environment, stdout=subprocess.PIPE, text=True)
            if during:
                during()
            out = running.communicate(timeout=120)[0]
            events = sorted((float(when), kind, name) for kind, name, when in (line.split() for line in log.read_text().splitlines()))
            return events, out.strip().splitlines()[-1:]

        def overlaps(events):
            running, most = 0, 0
            for _, kind, _ in events:
                running += 1 if kind == "start" else -1
                most = max(most, running)
            return most

        events, out = check(0)
        step("idle", overlaps(events) > 1, (events, out))
        many = (os.cpu_count() or 1) * 10
        events, out = check(many)
        gaps = [later[0] - earlier[0] for earlier, later in zip(events[1::2], events[2::2])]
        step("loaded", overlaps(events) == 1 and len(gaps) == 2 and max(gaps) < 3, (events, out))

        marked = []

        def fall():
            while "start" not in log.read_text():
                time.sleep(0.1)
            time.sleep(1.5)  # past the gate's 1 s spacing, so its next start waits on the mark alone
            load.write_text("0")
            time.sleep(2)
            (scratch / "config").mkdir(exist_ok=True)
            (scratch / "config" / "check-job-ends").touch()
            marked.append(time.time())

        events, out = check(many, fall)
        second = [when for when, kind, _ in events if kind == "start"][1:2]
        step("woken", second and 0 <= second[0] - marked[0] < 1.5 and overlaps(events) > 1, (marked, events, out))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
