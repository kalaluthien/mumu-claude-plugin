#!/usr/bin/env python3
"""Run run-criteria.py `--hunks` on a temporary git repository whose change holds a 30-hunk file that every revert breaks, a
3-hunk file with an unneeded hunk beside two needed ones, a 30-hunk file no check reads, an 8-hunk file whose second half is needed, an 8-hunk file of multi-line deletions whose second half is needed, a file deleted from a folder only it filled, an executable file with an unneeded comment, a file of CRLF lines whose changed line is unneeded, a file whose path holds a space and that a check needs, a file and a symlink target of Korean names that a check needs, a symlink that a check needs as it is, a symlink that it only needs as a link, an executable added file, an added file, a file whose last line lost its newline and a Python file whose added refusal no check reaches. Print `ok <case>` or `fail <case>: <detail>` per case, then `PASS` or
`FAIL`, and exit 1 on any failure:
- `few-runs`: the check ran at most 3 times with the big file reverted in part or whole;
- `names-unneeded`: the unneeded hunk's line and the unreached refusal's line are named, no line of the big file, the deleted file or the symlink is, and the call exits 1, with the folder of the deleted file, the symlink and the mode of the executable file as the head has them for every later revert;
- `names-whole`: every hunk of the unread file is named, since reverting them together passes;
- `names-half`: the first four hunks of the half-needed file are named and the line says four are not judged one by one;
- `names-deletions`: the same for the file of deletions, whose hunks git apply would place wrongly in the order that suits a replacement;
- `names-edges`: the added file, the file whose last line had no newline and the symlink that only has to be a link are named, since reverting each leaves a file no check tells from the base's;
- `takes-back-bytes`: 400 random pairs of files, whose lines hold form feeds, carriage returns, trailing spaces and empty lines, with or without a final newline, are taken back by `take_back` to the base byte for byte;
- `names-korean`: the file and the symlink with a Korean name or target, which a check needs, are named by no line, and no line names a mojibake path;
- `each-judges-all`: with `--each` the check ran once per hunk of the big file.

usage: replay-hunk-groups.py"""
import importlib.util
import pathlib
import random
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints ok; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints ok when it runs**: `{command}` prints `ok`; on base nothing.\n")
HUNKS = 30
PIECES = ["a", "b", "", "x\x0cy", "t  ", "c\r", "d\x0bx", "e\x85", "same", "-dash", "+plus", "@@ at", "\\ slash"]
PAIRS = 400
RUN_SECONDS = 600  # a `--hunks` call runs the check once per revert


def random_lines(generator):
    body = [generator.choice(PIECES) for _ in range(generator.randint(0, 9))]
    return "".join(piece + "\n" for piece in body[:-1]) + "".join(piece + generator.choice(["", "\n"]) for piece in body[-1:])


def take_back_bytes(sandbox):
    """The pairs whose head, taken back, differs from their base, each diffed by git in SANDBOX's environment."""
    # a property of the script's own function over random files, which a run of the script reaches only through a check per pair
    spec = importlib.util.spec_from_file_location("run_criteria", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    generator = random.Random(1450)
    work = sandbox.work / "take-back"
    for name in ("old", "new"):
        (work / name).mkdir(parents=True)
    wrong = []
    for _ in range(PAIRS):
        base, head = random_lines(generator), random_lines(generator)
        (work / "old" / "f").write_bytes(base.encode("latin-1"))
        (work / "new" / "f").write_bytes(head.encode("latin-1"))
        diff = subprocess.run(["git", "diff", "--no-index", "-U0", "--src-prefix=a/", "--dst-prefix=b/", "old/f", "new/f"], cwd=work, env=sandbox.environment, capture_output=True).stdout
        wrong += [(base, head)] * (module.take_back(head, [patch for _, _, patch in module.split_hunks(diff.decode("latin-1"))]) != base)
    return wrong


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("hunk-groups-") as folder:
        return replay(folder)


def replay(folder):
    cases = replay_probe.Cases()
    sandbox = replay_probe.Sandbox(folder, commit=False)
    work, git, log = sandbox.repository, sandbox.git, folder / "runs.log"

    git("init", "-q", "-b", "main")
    (work / "big.txt").write_text("".join(f"old {n}\nkeep {n}\n" for n in range(HUNKS)))
    (work / "small.txt").write_text("a old\nkeep\nb old\nkeep\nc old\n")
    (work / "crlf.txt").write_bytes(b"a\r\nb\r\n")
    (work / "한글.txt").write_text("x\n")
    (work / "ln").symlink_to("a-target")
    (work / "d e").mkdir()
    (work / "d e" / "a b.txt").write_text("x\n")
    (work / "run.sh").write_text("echo hi\n")
    (work / "run.sh").chmod(0o755)
    (work / "d").mkdir()
    (work / "d" / "gone.txt").write_text("here\n")
    (work / "link").symlink_to("old-target")
    (work / "link2").symlink_to("a-target")
    (work / "wide.txt").write_text("".join(f"old {n}\nkeep {n}\n" for n in range(HUNKS)))
    (work / "half.txt").write_text("".join(f"old {n}\nkeep {n}\n" for n in range(8)))
    (work / "dels.txt").write_text("".join(f"gone {n} a\ngone {n} b\nkeep {n}\n" for n in range(8)))
    (work / "nonl.txt").write_text("a\nlast")
    (work / "c.py").write_text("import sys\nprint('old')\n")
    git("add", ".")
    git("commit", "-q", "-m", "base")
    git("checkout", "-q", "-b", "change")
    (work / "big.txt").write_text("".join(f"new {n}\nkeep {n}\n" for n in range(HUNKS)))
    (work / "small.txt").write_text("a new\nkeep\nb new\nkeep\nc new\n")
    (work / "d" / "gone.txt").unlink()
    (work / "d e" / "a b.txt").write_text("unneeded\n")
    (work / "한글.txt").write_text("y\n")
    (work / "ln").unlink()
    (work / "ln").symlink_to("새-target")
    (work / "crlf.txt").write_bytes(b"a\r\nc\r\n")
    (work / "run.sh").write_text("echo hi\n# comment\n")
    (work / "link").unlink()
    (work / "link").symlink_to("new-target")
    (work / "link2").unlink()
    (work / "link2").symlink_to("b-target")
    (work / "exe.sh").write_text("echo\n")
    (work / "exe.sh").chmod(0o755)
    (work / "wide.txt").write_text("".join(f"new {n}\nkeep {n}\n" for n in range(HUNKS)))
    (work / "half.txt").write_text("".join(f"new {n}\nkeep {n}\n" for n in range(8)))
    (work / "dels.txt").write_text("".join(f"keep {n}\n" for n in range(8)))
    (work / "nonl.txt").write_text("a\nlast2\n")
    (work / "added.txt").write_text("added\n")
    (work / "c.py").write_text("import sys\nif len(sys.argv) > 1: sys.exit('refused')\nprint('new')\n")
    git("add", "-A")
    git("commit", "-qm", "change")
    # a run that leaves a line in the log is one where the big file is not whole, so a reverted run; the unneeded hunk is the middle one of small.txt
    command = (f"test $(grep -c '^new' big.txt) = {HUNKS} || echo big >> {log}; "
               f"test $(grep -c '^new' big.txt) = {HUNKS} && test $(grep -c '^new [4-7]$' half.txt) = 4 && test $(tail -n 4 dels.txt | grep -c '^gone') = 0 && test \"$(wc -c < nonl.txt | tr -d ' ')\" != 7 && (test -s added.txt || test ! -e added.txt) && grep -q '^a new' small.txt && grep -q '^c new' small.txt && (test ! -d d || touch d/stamp) && test ! -d d && test -L link2 && test \"$(readlink link)\" = new-target && test -x exe.sh && test -x run.sh && grep -q '^y' 한글.txt && test \"$(readlink ln)\" = 새-target && test $(wc -c < crlf.txt | tr -d ' ') = 6 && grep -q '^unneeded' \"d e/a b.txt\" && python3 c.py | grep -q new && echo ok")
    body = folder / "body.md"
    body.write_text(BODY.format(command=command))

    def call(*options):
        log.write_text("")
        done = sandbox.python(SCRIPT, "--hunks", "--ref", "main", *options, body, timeout=RUN_SECONDS)
        return done.returncode, done.stdout, done.stderr, len(log.read_text().split())

    code, out, error, runs = call()
    cases.step("few-runs", runs <= 3 and "big.txt: 30 hunks not judged one by one" in out, (runs, out, error))
    cases.step("names-unneeded", code == 1 and "small.txt:3: unneeded hunk" in out and "big.txt:" not in out.replace("big.txt: ", "") and "c.py:2: unneeded condition" in out and "small.txt:1" not in out and "small.txt:5" not in out and "gone.txt" not in out and "link:" not in out and "a b.txt" not in out, (code, out, error))
    cases.step("names-whole", all(f"wide.txt:{2 * n + 1}: unneeded hunk" in out for n in range(HUNKS)), (code, out, error))
    cases.step("names-half", all(f"half.txt:{2 * n + 1}: unneeded hunk" in out for n in range(4)) and "half.txt:9" not in out and "half.txt: 4 hunks not judged one by one" in out, (code, out, error))
    cases.step("names-deletions", out.count("dels.txt:") == 5 and "dels.txt: 4 hunks not judged one by one" in out, (code, out, error))
    cases.step("names-edges", "added.txt:1: unneeded hunk" in out and "nonl.txt:2: unneeded hunk" in out and "link2:1: unneeded hunk" in out and "run.sh:2: unneeded hunk" in out and "crlf.txt:2: unneeded hunk" in out, (code, out, error))
    changed = git("-c", "core.quotepath=false", "diff", "--name-only", "main...HEAD").split("\n")
    cases.step("names-korean", {"한글.txt", "ln"} <= set(changed) and "ln:" not in out and all(line.split(":")[0].isascii() for line in out.splitlines() if "unneeded" in line), (code, out, error))
    code, out, error, runs = call("--each")
    cases.step("each-judges-all", runs == HUNKS and "small.txt:3: unneeded hunk" in out, (runs, code, out, error))
    wrong = take_back_bytes(sandbox)
    cases.step("takes-back-bytes", not wrong, wrong[:2])
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
