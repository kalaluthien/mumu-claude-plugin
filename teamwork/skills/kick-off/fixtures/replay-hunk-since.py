#!/usr/bin/env python3
"""Run run-criteria.py `--hunks --since` on a temporary git repository whose change has three hunks in two files. Print
`ok <case>` or `fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `whole-sweep`: with no `--since`, all three hunks are reverted, and the one no criterion needs is named;
- `moved-only`: after a fix that moves only that hunk, `--since <first sweep>` reverts it alone, names it unneeded, and counts the
  two others as unchanged since that sha, not swept;
- `nothing-moved`: `--since` the head itself reverts no hunk and counts all three unchanged, exit 0;
- `later-line`: a fix to the second line of a three-line hunk moves that hunk alone, and the unneeded one, not swept, is not named, exit 0;
- `first-line-removed`: a fix that removes a hunk's first line moves that hunk alone;
- `mode-moved`: a fix that only changes a file's mode moves every hunk of that file;
- `unknown-sha`: a sha the repository lacks is named, exit 1;
- `base-refused`: `--hunks` beside `--base` is refused, exit 2;
- `removal-extended`: a hunk that only removes lines, which a fix extends by the next line, is swept again and named unneeded;
- `removal-kept`: a fix far below it in the same file leaves that hunk unchanged, not swept, and only the fix's own hunk is swept.

usage: replay-hunk-since.py"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = "## Definition of done\n\n1. [check] **The checker prints ok for the change**: `python3 check.py` prints `ok`; on base nothing.\n"
CHECK = "exec(open('a.py').read())\nprint('ok' if A == 2 and 'z' in open('b.txt').read() else 'no')\n"  # no import, whose cached bytecode may outlive a same-size revert
FILLER = "".join(f"F{n} = {n}\n" for n in range(20))
LINES = [f"line {n}\n" for n in range(1, 41)]


def commit(box, files):
    for name, text in files.items():
        replay_probe.write_text(box.repository, name, text)
    box.git("add", "-A")
    box.git("commit", "-qm", "step")
    return box.git("rev-parse", "HEAD").strip()


def sweep(box, *since):
    """(exit code, hunks reverted, hunks not swept, the unneeded hunks named, all it printed) of a `--hunks` sweep, `--since` SINCE when given."""
    done = box.python(SCRIPT, "--hunks", "--ref", "main", *(["--since", *since] if since else []), replay_probe.write_text(box.work, "body.md", BODY), timeout=600)
    text = done.stdout + done.stderr
    summary = re.search(r"^hunks: (\d+) reverted against main, \d+ conditions made False, \d+ mutants made, \d+ unneeded" + (f", (\\d+) unchanged since {since[0]}, not swept" if since else "()") + "$", text, re.M)
    reverted, unchanged = (int(summary.group(1)), int(summary.group(2) or 0)) if summary else (None, None)
    return done.returncode, reverted, unchanged, set(re.findall(r"^(\S+:\d+): unneeded hunk", text, re.M)), text


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("hunk-since-") as work:
        box = replay_probe.Sandbox(work, commit=False)
        commit(box, {"a.py": "A = 1\n" + FILLER + "B = 1\n", "b.txt": "x\n", "check.py": CHECK})
        box.git("checkout", "-qb", "change")
        first = commit(box, {"a.py": "A = 2\n" + FILLER + "B = 2\n", "b.txt": "x\ny\nz\nw\n"})
        *result, text = sweep(box)
        cases.step("whole-sweep", result == [1, 3, 0, {"a.py:22"}], text)
        second = commit(box, {"a.py": "A = 2\n" + FILLER + "B = 3\n"})
        *result, text = sweep(box, first)
        cases.step("moved-only", result == [1, 1, 2, {"a.py:22"}], text)
        *result, text = sweep(box, second)
        cases.step("nothing-moved", result == [0, 0, 3, set()], text)
        third = commit(box, {"b.txt": "x\ny\nz z\nw\n"})
        *result, text = sweep(box, second)
        cases.step("later-line", result == [0, 1, 2, set()], text)
        fourth = commit(box, {"b.txt": "x\nz z\nw\n"})
        *result, text = sweep(box, third)
        cases.step("first-line-removed", result == [0, 1, 2, set()], text)
        (box.repository / "a.py").chmod(0o755)
        box.git("commit", "-qam", "mode")
        *result, text = sweep(box, fourth)
        cases.step("mode-moved", result == [1, 2, 1, {"a.py:22"}], text)
        code, *_, text = sweep(box, "0" * 40)
        cases.step("unknown-sha", code == 1 and text == f"run-criteria: --since {'0' * 40} names no commit here\n", text)
        refused = box.python(SCRIPT, "--hunks", "--base", box.work / "body.md")
        cases.step("base-refused", refused.returncode == 2 and "\nusage: run-criteria.py " in refused.stderr and not refused.stdout, refused.stdout + refused.stderr)
    with replay_probe.scratch("hunk-since-") as work:
        box = replay_probe.Sandbox(work, commit=False)
        commit(box, {"a.py": "A = 1\n", "b.txt": "z\n", "c.txt": "".join(LINES), "check.py": CHECK})
        box.git("checkout", "-qb", "change")
        first = commit(box, {"a.py": "A = 2\n", "c.txt": "".join(LINES[:10] + LINES[11:])})
        second = commit(box, {"c.txt": "".join(LINES[:10] + LINES[12:])})
        *result, text = sweep(box, first)
        cases.step("removal-extended", result == [1, 1, 1, {"c.txt:10"}], text)
        commit(box, {"c.txt": "".join(LINES[:10] + LINES[12:34] + ["line 35 again\n"] + LINES[35:])})
        *result, text = sweep(box, second)
        cases.step("removal-kept", result == [1, 1, 2, {"c.txt:33"}], text)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
