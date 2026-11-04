#!/usr/bin/env python3
"""Edit an issue body of a git board in a temporary repository by `edit-issue-body.py` and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-body-diff.py --case <name>
- newline: a diff made from the body plus a final newline applies, and the body keeps no final newline
- exact: a diff made from the body exactly as stored applies
- mismatch: a diff whose context is not the body's text exits nonzero and leaves the body and the comments as they were
- misordered: a diff whose second hunk starts above the first exits 2, names the hunk out of order and its header, and leaves the body and the comments as they were"""
import os
import pathlib
import subprocess
import sys
import tempfile

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
STORED = "Probe the diff.\n\nSecond paragraph."


def setup():
    work = pathlib.Path(tempfile.mkdtemp(prefix="body-diff-"))
    repo = work / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    env = {**os.environ, "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "home")}
    (work / "body.md").write_text(STORED)
    made = run(env, repo, "use-board.py", "file", "Probe the diff", work / "body.md")
    return work, repo, env, made.stdout.strip().rsplit("/", 1)[-1]


def run(env, repo, script, *argv):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, argv)], cwd=repo, capture_output=True, text=True, env=env)


def diff_of(old, new, work):
    (work / "old").write_text(old)
    (work / "new").write_text(new)
    path = work / "edit.diff"
    # diff(1), which marks a missing final newline as a body written by hand would not
    path.write_text(subprocess.run(["diff", "-u", "--label", "a/body", "--label", "b/body", "old", "new"], cwd=work, capture_output=True, text=True).stdout)
    return path


def read(env, repo, number):
    return run(env, repo, "use-board.py", "read", number).stdout


def apply(work, repo, env, number, old, new):
    sha = next(line.split("body sha: ")[1].strip() for line in read(env, repo, number).splitlines() if "body sha: " in line)
    return run(env, repo, "edit-issue-body.py", number, diff_of(old, new, work), "DECIDED: probe the diff", "--base", sha)


def case_newline(work, repo, env, number):
    done = apply(work, repo, env, number, STORED + "\n", STORED.replace("Second", "Edited second") + "\n")
    if done.returncode:
        return fail(f"exit {done.returncode}: {done.stderr.strip()[-300:]}")
    stored = subprocess.run(["git", "show", "refs/teamwork-blackboard:" + number + "/body.md"], cwd=repo, capture_output=True, text=True).stdout
    if stored != STORED.replace("Second", "Edited second"):
        return fail(f"the body is {stored!r}")
    return 0


def case_exact(work, repo, env, number):
    done = apply(work, repo, env, number, STORED, STORED.replace("Second", "Edited second"))
    if done.returncode or "Edited second paragraph." not in read(env, repo, number):
        return fail(f"exit {done.returncode}: {done.stderr.strip()[-300:]}")
    return 0


def case_mismatch(work, repo, env, number):
    before = read(env, repo, number)
    done = apply(work, repo, env, number, "Other text.\n\nThird paragraph.\n", "Other text.\n\nEdited paragraph.\n")
    if done.returncode == 0 or read(env, repo, number) != before:
        return fail(f"exit {done.returncode}, the body or its comments changed: {done.stderr.strip()[-200:]}")
    return 0


def case_misordered(work, repo, env, number):
    body = "Probe the hunks.\n\n" + "".join(f"line {n}\n" for n in range(1, 21))
    (work / "body.md").write_text(body)
    made = run(env, repo, "use-board.py", "file", "Probe misordered hunks", work / "body.md")
    other = made.stdout.strip().rsplit("/", 1)[-1]
    before = read(env, repo, other)
    late = "@@ -17,3 +17,3 @@\n line 15\n-line 16\n+late 16\n line 17\n"
    early = "@@ -4,3 +4,3 @@\n line 2\n-line 3\n+early 3\n line 4\n"
    (work / "bad.diff").write_text("--- a/body\n+++ b/body\n" + late + early)
    sha = next(line.split("body sha: ")[1].strip() for line in before.splitlines() if "body sha: " in line)
    done = run(env, repo, "edit-issue-body.py", other, work / "bad.diff", "DECIDED: probe misordered hunks", "--base", sha)
    if done.returncode != 2 or "hunk 2" not in done.stderr or "@@ -4,3 +4,3 @@" not in done.stderr or "out of order" not in done.stderr:
        return fail(f"exit {done.returncode}, stderr {done.stderr.strip()[-300:]!r}")
    if read(env, repo, other) != before:
        return fail("the body or its comments changed")
    return 0


def fail(why):
    print(f"FAIL: {why}")
    return 1


CASES = {"newline": case_newline, "exact": case_exact, "mismatch": case_mismatch, "misordered": case_misordered}


def main(args):
    if len(args) != 2 or args[0] != "--case" or args[1] not in CASES:
        print(__doc__, file=sys.stderr)
        return 2
    if CASES[args[1]](*setup()):
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
