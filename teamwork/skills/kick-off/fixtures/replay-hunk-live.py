#!/usr/bin/env python3
"""Run run-criteria.py `--hunks --jobs 3` on a temporary git repository whose change edits three files a live check watches, under a stub
`claude` that takes a second and notes when two sessions overlap. Print `ok <case>` or `fail <case>: <detail>` per case, then `PASS` or
`FAIL`, and exit 1 on any failure:
- `one-session-at-a-time`: the parallel jobs start the head's session and one per revert one after another, four in all, the cap of 4,
  and the sweep prints `live runs: 4 of 4 started`;
- `bad-jobs-refused`: `--jobs 0` and `--jobs -1` print the usage and start no session, exit 2.

usage: replay-hunk-live.py"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = ("## Definition of done\n\n1. [check] **The stub session earns a verdict**: `claude -p hello | python3 judge.py` prints `PASS`; "
        "watches: app; on base `FAIL`\n")
JUDGE = "import sys\nprint('PASS' if 'verdict' in sys.stdin.read() else 'FAIL')\n"
# a session that finds another's folder notes the overlap, since mkdir of an existing folder fails
CLAUDE = "#!/bin/sh\nmkdir {work}/session 2>/dev/null || echo overlap >> {work}/claude.log\necho started >> {work}/claude.log\nsleep 1\nrmdir {work}/session 2>/dev/null\necho verdict\n"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("hunk-live-") as work:
        box = replay_probe.Sandbox(work)
        replay_probe.write_text(box.bin, "claude", CLAUDE.format(work=work)).chmod(0o755)
        (box.repository / "app").mkdir()
        for name in ("one", "two", "three"):
            (box.repository / "app" / f"{name}.txt").write_text("old\n")
        (box.repository / "judge.py").write_text(JUDGE)
        box.git("add", "-A")
        box.git("commit", "-qm", "base")
        box.git("checkout", "-qb", "change")
        for name in ("one", "two", "three"):
            (box.repository / "app" / f"{name}.txt").write_text("new\n")
        box.git("commit", "-qam", "change")
        body = replay_probe.write_text(work, "body.md", BODY)
        log = work / "claude.log"
        done = box.python(SCRIPT, "--hunks", "--jobs", "3", "--ref", "main", body, timeout=300)
        lines = log.read_text().split() if log.exists() else []
        out = done.stdout + done.stderr
        cases.step("one-session-at-a-time", lines == ["started"] * 4 and "live runs: 4 of 4 started" in out, f"sessions: {lines}\n{out}")
        refused = [box.python(SCRIPT, "--hunks", "--jobs", jobs, "--ref", "main", body, timeout=60) for jobs in ("0", "-1")]
        after = log.read_text().split()
        cases.step("bad-jobs-refused", [each.returncode for each in refused] == [2, 2] and all("usage:" in each.stderr for each in refused) and after == lines,
                   "\n".join(each.stdout + each.stderr for each in refused))
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
