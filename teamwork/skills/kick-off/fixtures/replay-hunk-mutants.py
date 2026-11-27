#!/usr/bin/env python3
"""Run run-criteria.py `--hunks` on a temporary git repository whose change adds a script that calls git with an argument list, decodes
its output, writes it by two codecs and joins two tests by `and`, adds a line to a script that held all three kinds already, and adds the
checker under `fixtures/` that holds them too. Print `ok <case>` or `fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `survivors-named`: a check that needs only the scripts' last lines makes `--hunks` name, as surviving mutants with what each becomes, the
  argument list without its second and without its third element, a subscript's tuple without its slice, each of the three codecs swapped, and
  the `and` without each operand, beside the argument's index, exit 1; fourteen mutants are made, each script raising at its first line, the list without `git` and a pair without
  either word among them, which stop the script, and none for the tuple without its last element, which is no Python, a pair that is
  assigned to, a codec no Python knows or its second argument, one that is no text, or a word that names a codec given to another call;
- `all-killed`: a check that reads what the script prints and writes for a name outside ASCII, an empty one and a refused one names none, fourteen made, exit 0;
- `old-lines-spared`: neither sweep names a line the change did not add, nor a line of the checker under `fixtures/`.

usage: replay-hunk-mutants.py"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = "## Definition of done\n\n1. [check] **The checker prints ok for the change**: `python3 fixtures/check-tool.py {mode}` prints `ok`; on base nothing.\n"
TOOL = '''import subprocess
import sys


class Pick:
    def __getitem__(self, key):
        return key

    def unused(self, data):
        return data.decode("no-such-codec", "ascii") + data.decode(sys.getdefaultencoding())


head, tail = "named", "none"
out = subprocess.run(["git", "stripspace", "--strip-comments"], stdin=open(sys.argv[1], "rb", encoding=None), capture_output=True).stdout
name = out.decode("latin-1").strip()
with open("out.txt", "w", encoding="utf-8") as file:
    file.write(name)
with open("raw.bin", "wb") as file:
    file.write(name.encode("utf-8"))
print(head if name and not name.startswith("x") else tail)
print(len(Pick()["a":"b", "c"]), len("ascii"))
print("ok".strip("ascii"))
'''
OLD = 'WORDS = ["a", "b"]\nTEXT = b"a".decode("ascii") and WORDS[0] or WORDS[1]\n'
CHECKER = '''import pathlib
import subprocess
import sys


def run(*argv):
    return subprocess.run([sys.executable, *argv], capture_output=True).stdout.decode("utf-8")


def wrote(name):
    return pathlib.Path("out.txt").read_bytes() == name and pathlib.Path("raw.bin").read_bytes() == name


passed = run("tool.py", "plain.txt").endswith("ok\\n") and run("old.py") == "old\\n"
if sys.argv[1] == "strong":
    passed = passed and wrote(b"plain") and run("tool.py", "name.txt") == "named\\n2 5\\nok\\n" and wrote(b"caf\\xc3\\xa9")
    passed = passed and run("tool.py", "empty.txt") == "none\\n2 5\\nok\\n" and run("tool.py", "refused.txt") == "none\\n2 5\\nok\\n" and wrote(b"xyz")
print("ok" if passed else "no")
'''
LINE = "tool.py:{}: surviving mutant: no criterion fails when the {} becomes {}, so make a criterion fail on it or drop it"
SURVIVORS = {
    LINE.format(14, 'list `["git", "stripspace", "--strip-comments"]`', "`['git', '--strip-comments']`"),
    LINE.format(14, 'list `["git", "stripspace", "--strip-comments"]`', "`['git', 'stripspace']`"),
    LINE.format(14, "number `1`", "`0`"),
    LINE.format(15, 'codec `"latin-1"`', '`"utf-8"`'),
    LINE.format(16, 'codec `"utf-8"`', '`"latin-1"`'),
    LINE.format(19, 'codec `"utf-8"`', '`"latin-1"`'),
    LINE.format(20, 'operands `name and not name.startswith("x")`', "`name`"),
    LINE.format(20, 'operands `name and not name.startswith("x")`', "`not name.startswith('x')`"),
    LINE.format(21, 'tuple `"a":"b", "c"`', "`('c',)`"),
}


def sweep(box, mode):
    """(exit code, the summary's counts of mutants made and unneeded, the lines naming a finding, all it printed) of a `--hunks` sweep whose check runs in MODE."""
    done = box.python(SCRIPT, "--hunks", "--ref", "main", replay_probe.write_text(box.work, "body.md", BODY.format(mode=mode)), timeout=900)
    text = done.stdout + done.stderr
    summary = re.search(r"^hunks: 3 reverted against main, 0 conditions made False, (\d+) mutants made, (\d+) unneeded$", text, re.M)
    return done.returncode, summary and [int(count) for count in summary.groups()], {line for line in text.splitlines() if ": surviving mutant" in line or ": unneeded" in line}, text


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("hunk-mutants-") as work:
        box = replay_probe.Sandbox(work, commit=False)
        for name, data in {"plain.txt": b"plain\n", "name.txt": b"# note\ncaf\xe9\n", "empty.txt": b"", "refused.txt": b"xyz\n", "old.py": OLD.encode()}.items():
            (box.repository / name).write_bytes(data)
        box.git("add", "-A")
        box.git("commit", "-qm", "base")
        box.git("checkout", "-qb", "change")
        (box.repository / "fixtures").mkdir()
        for name, text in {"tool.py": TOOL, "old.py": OLD + 'print("old")\n', "fixtures/check-tool.py": CHECKER}.items():
            (box.repository / name).write_text(text)
        box.git("add", "-A")
        box.git("commit", "-qm", "change")
        code, counts, weak, text = sweep(box, "weak")
        cases.step("survivors-named", (code, counts, weak) == (1, [14, 9], SURVIVORS), text)
        code, counts, strong, text = sweep(box, "strong")
        cases.step("all-killed", (code, counts, strong) == (0, [14, 0], set()), text)
        cases.step("old-lines-spared", not any("old.py" in line or "fixtures/" in line for line in weak | strong) and len(weak | strong) == len(SURVIVORS), sorted(weak | strong))
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
