#!/usr/bin/env python3
"""Edit a task's body on a temporary git board by handing `use-board.py edit` the new body. Print `ok <case>` or `fail <case>: <detail>` per case,
then `PASS` or `FAIL`, and exit 1 on any failure:
- `start`: `read <issue> --body` prints the stored body byte for byte, with or without a final newline, and nothing else;
- `round`: that output with one line changed, handed to `edit`, becomes the stored body, in three calls, and the new comment holds the keyword line and a diff of only the changed line;
- `shown`: `read` cuts that diff to one line and `read --full` prints it;
- `far-apart`: a new body that changes its first and its last line is stored whole, the two changes in one comment;
- `applies`: the diff a comment holds, applied by `patch` to the body before it, gives the body after it, also where a line holds a form feed or U+2028;
- `no-newline`: a new body that drops the final newline is stored without it;
- `diff-given`: a diff handed as the body changes nothing and names `read <issue> --body`;
- `unchanged`: the stored body handed back changes nothing and says so;
- `stale`: a `--base` that is not the stored body's sha changes nothing;
- `one-script`: `edit-issue-body.py` is gone and no playbook or script names it.

usage: replay-body-edit.py"""
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
BODY = "The probe prints ok.\n\n## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints ok; meets: the caller's need.\n\n" + "".join(f"Line {n} of the goal.\n" for n in range(1, 30)) + "\nLast line."
failed = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[-900:]}", flush=True)
    if not ok:
        failed.append(name)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="body-edit-"))
    repository = work / "repo"
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    os.environ.update(HOME=str(work), CLAUDE_CONFIG_DIR=str(work / "home"), GIT_AUTHOR_NAME="probe", GIT_AUTHOR_EMAIL="probe@example.com",
                      GIT_COMMITTER_NAME="probe", GIT_COMMITTER_EMAIL="probe@example.com")
    calls = []

    def use(*argv):
        done = subprocess.run([sys.executable, str(USE), *map(str, argv)], cwd=repository, capture_output=True, text=True)
        calls.append(argv[0])
        return done.returncode, done.stdout, done.stderr

    def stored(number):
        return subprocess.run(["git", "show", f"refs/teamwork-blackboard:{number}/body.md"], cwd=repository, capture_output=True, text=True).stdout

    def state():
        return subprocess.run(["git", "rev-parse", "refs/teamwork-blackboard"], cwd=repository, capture_output=True, text=True).stdout

    def sha(number):
        return next(line.split(": ", 1)[1] for line in use("read", number)[1].splitlines() if line.startswith("body sha: "))

    def write(name, text):
        (work / name).write_text(text)
        return work / name

    use("file", "Print ok from the probe", write("one.md", BODY))
    use("file", "Print ok twice", write("two.md", BODY + "\n"))
    printed = [use("read", number, "--body") for number in (1, 2)]
    step("start", [answer[1] for answer in printed] == [stored(1), stored(2)] == [BODY, BODY + "\n"] and not any(answer[0] or answer[2] for answer in printed), printed)

    del calls[:]
    base = sha(1)
    new = write("new.md", use("read", 1, "--body")[1].replace("Line 7 of the goal.", "Line 7 of the goal, reworded."))
    edited = use("edit", 1, new, "DECIDED: rewords line 7.", "--base", base)
    full = use("read", 1, "--full")[1]
    changed = [line for line in full.splitlines() if line[:1] in ("+", "-") and line[:3] not in ("+++", "---")]
    step("round", edited[0] == 0 and stored(1) == new.read_text() and calls[:3] == ["read", "read", "edit"] and "DECIDED: rewords line 7." in full
         and changed == ["-Line 7 of the goal.", "+Line 7 of the goal, reworded."], [edited, changed, calls])
    cut = use("read", 1)[1]
    step("shown", "+Line 7 of the goal, reworded." not in cut and "which `read --full` prints" in cut, cut[-600:])

    far = write("far.md", stored(2).replace("The probe prints ok.", "The probe prints ok, twice.").replace("Last line.", "Last line, reworded."))
    edited = use("edit", 2, far, "DECIDED: rewords both ends.", "--base", sha(2))
    full = use("read", 2, "--full")[1]
    step("far-apart", edited[0] == 0 and stored(2) == far.read_text() and full.count("```diff") == 1 and "+The probe prints ok, twice." in full and "+Last line, reworded." in full, [edited, full[-900:]])

    earlier = write("earlier.md", stored(2))
    odd = write("odd.md", stored(2).replace("Line 3 of the goal.", "Line 3 of\x0cthe goal.").replace("Line 20 of the goal.", "Line 20 of\u2028the goal."))
    edited = use("edit", 2, odd, "DECIDED: adds odd characters.", "--base", sha(2))
    recorded = use("read", 2, "--full")[1].rsplit("```diff\n", 1)[-1].rsplit("```", 1)[0]
    patched = subprocess.run(["patch", "-s", str(earlier), str(write("recorded.diff", recorded))], capture_output=True, text=True)
    step("applies", edited[0] == 0 and patched.returncode == 0 and earlier.read_text() == odd.read_text() == stored(2), [edited, patched.stdout, patched.stderr])

    edited = use("edit", 2, write("bare.md", stored(2).rstrip("\n").replace("twice", "three times")), "DECIDED: prints three times.", "--base", sha(2))
    step("no-newline", edited[0] == 0 and stored(2).endswith("Last line, reworded.") and "three times" in stored(2), [edited, stored(2)[-60:]])

    before = state()
    diff = write("edit.diff", "--- a/body\n+++ b/body\n@@ -1 +1 @@\n-The probe prints ok.\n+The probe prints ok, edited.\n")
    given = use("edit", 1, diff, "DECIDED: hands a diff.", "--base", sha(1))
    step("diff-given", given[0] != 0 and not given[1] and "read 1 --body" in given[2] and given[2].count("\n") == 1 and state() == before, given)

    same = use("edit", 1, write("same.md", stored(1)), "DECIDED: changes nothing.", "--base", sha(1))
    step("unchanged", same[0] != 0 and not same[1] and "as it stands" in same[2] and state() == before, same)

    stale = use("edit", 1, write("late.md", stored(1) + "\nA late line.\n"), "DECIDED: adds a late line.", "--base", base)
    step("stale", stale[0] != 0 and not stale[1] and "changed since you read it" in stale[2] and state() == before, stale)

    pages = [path for folder in ("lib", "hooks", "monitors", "skills") for path in (ROOT / folder).rglob("*") if path.suffix in (".py", ".md", ".tsx", ".json") and path != pathlib.Path(__file__).resolve()]
    named = [str(path.relative_to(ROOT)) for path in pages if "edit-issue-body" in path.read_text()]
    step("one-script", not named and not (USE.parent / "edit-issue-body.py").exists(), named)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
