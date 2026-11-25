#!/usr/bin/env python3
"""Run run-criteria.py on a scratch git repository whose one `[check]` logs each run. Print `ok <case>` or `fail <case>: <detail>`
per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `same-files-once`: the call twice on the same files runs the check once, and the second table says one check was replayed;
- `other-worktree-once`: the call from a second worktree of the same files, which has another path, runs the check again, since its output may hold the path;
- `detached-worktrees-run`: two detached worktrees on one commit, with equal files, each run the check, since the output may hold the path;
- `changed-file-runs`: a change to a file runs the check again;
- `fresh-runs`: `--fresh` on the same files runs it again;
- `git-state-runs`: the same files with another index, after a soft reset, run a check that reads `git status` again;
- `other-check-runs`: another check on files where a check passed runs;
- `staged-edit-runs`: a second edit staged after a first, with the same commit and status, runs the check again;
- `status-runs`: the same files, commit and index tree with a different staged state run a check that reads `git diff --cached` again;
- `base-fresh-runs`: `--base --fresh` runs the check again;
- `head-runs`: an amended commit with equal files and status runs a check that reads `git log` again;
- `branch-runs`: another branch on the same commit runs a check that reads the branch again;
- `no-git-runs`: a folder that is no git checkout runs the check on every call and keeps no memory;
- `locked-git-dir-runs`: a git dir the run cannot write still prints the table, exits 0 and keeps no memory;
- `failure-runs`: a check that fails runs on every call;
- `base-once`: `--base` twice runs the check once;
- `base-moves-runs`: after a commit on the base ref, `--base` runs the check again;
- `outside-file-runs`: a check that reads a file outside the repository by its absolute path runs again once that file changed, and is replayed while it did not.

usage: replay-criteria-cache.py"""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints ok; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints ok when it runs**: `{command}` prints `ok`; on base nothing.\n")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("criteria-cache-") as work:
        return replay(work)


def replay(work):
    box, cases = replay_probe.Sandbox(work, commit=False), replay_probe.Cases()
    step, git, repository = cases.step, box.git, box.repository
    log = work / "runs.log"

    (repository / "a.txt").write_text("one\n")
    git("add", ".")
    git("commit", "-q", "-m", "base")

    def call(command, *options, cwd=repository):
        log.write_text("")
        body = work / "body.md"
        body.write_text(BODY.format(command=command))
        done = box.python(SCRIPT, *options, body, cwd=cwd)
        return done.stdout, done.stderr, len(log.read_text().split())

    passing = f"echo run >> {log}; grep -q one a.txt && echo ok"
    call(passing)
    out, error, runs = call(passing)
    step("same-files-once", runs == 0 and "cached: 1 checks replayed" in out and "| pass | ok |" in out, (runs, out, error))
    second = work / "second"
    git("worktree", "add", "-q", str(second), "-b", "second")
    out, error, runs = call(passing, cwd=second)
    step("other-worktree-once", runs == 1, (runs, out, error))
    for name in ("first", "second"):
        git("worktree", "add", "-q", "--detach", str(work / f"{name}-detached"))
    runs = [call(passing, cwd=work / f"{name}-detached")[2] for name in ("first", "second")]
    step("detached-worktrees-run", runs == [1, 1], runs)
    (repository / "a.txt").write_text("one two\n")
    out, error, runs = call(passing)
    step("changed-file-runs", runs == 1 and "cached" not in out, (runs, out, error))
    out, error, runs = call(passing, "--fresh")
    step("fresh-runs", runs == 1, (runs, out, error))
    clean = f"echo run >> {log}; test -z \"$(git status --porcelain)\" && echo ok"
    git("commit", "-qam", "second")
    call(clean)
    git("reset", "-q", "--soft", "HEAD~1")
    out, error, runs = call(clean)
    step("git-state-runs", runs == 1 and "| fail |" in out, (runs, out, error))
    unstaged = f"echo run >> {log}; test -z \"$(git diff --cached --name-only)\" && echo ok"
    git("reset", "-q")
    (repository / "a.txt").write_text("changed\n")
    call(unstaged)
    git("add", "a.txt")
    out, error, runs = call(unstaged)
    step("status-runs", runs == 1 and "| fail |" in out, (runs, out, error))
    git("reset", "-q")
    failing = f"echo run >> {log}; grep -q absent a.txt && echo ok"
    call(passing)
    out, error, runs = call(failing)
    step("other-check-runs", runs == 1 and "| fail |" in out, (runs, out, error))
    shown = f"echo run >> {log}; test -s a.txt && echo ok"
    for text in ("alpha\n", "beta\n"):
        (repository / "a.txt").write_text(text)
        git("add", "a.txt")
        out, error, runs = call(shown)
    step("staged-edit-runs", runs == 1 and "cached" not in out, (runs, out, error))
    call(failing)
    out, error, runs = call(failing)
    step("failure-runs", runs == 1 and "| fail |" in out, (runs, out, error))
    quoted = BODY.replace("on base nothing.", "on base `ok`.")
    body = work / "body.md"
    body.write_text(quoted.format(command=f"echo run >> {log}; echo ok"))
    log.write_text("")
    again = [box.python(SCRIPT, "--base", "--ref", "main", body).stdout for _ in range(2)]
    step("base-once", len(log.read_text().split()) == 1 and "cached: 1 checks replayed" in again[1] and "cached" not in again[0], (log.read_text(), again))
    log.write_text("")
    box.python(SCRIPT, "--base", "--ref", "main", "--fresh", body)
    step("base-fresh-runs", len(log.read_text().split()) == 1, log.read_text())
    git("commit", "-qam", "moved")
    log.write_text("")
    moved = box.python(SCRIPT, "--base", "--ref", "main", body).stdout
    step("base-moves-runs", len(log.read_text().split()) == 1 and "cached" not in moved, (log.read_text(), moved))
    git("commit", "-q", "--allow-empty", "-m", "first")
    subject = f"echo run >> {log}; git log -1 --format=%s | grep -q first && echo ok"
    call(subject)
    git("commit", "-q", "--amend", "--allow-empty", "-m", "other")
    out, error, runs = call(subject)
    step("head-runs", runs == 1 and "| fail |" in out, (runs, out, error))
    named = f"echo run >> {log}; git symbolic-ref --short HEAD | grep -q main && echo ok"
    call(named)
    git("checkout", "-q", "-b", "side")
    out, error, runs = call(named)
    step("branch-runs", runs == 1 and "| fail |" in out, (runs, out, error))
    outside = work / "outside.txt"
    outside.write_text("one\n")
    reader = f"echo run >> {log}; grep -q one {outside} && echo ok"
    call(reader)
    same = call(reader)[2]
    outside.write_text("one two\n")
    out, error, runs = call(reader)
    step("outside-file-runs", same == 0 and runs == 1 and "cached" not in out, (same, runs, out, error))
    plain = work / "plain"
    plain.mkdir()
    (plain / "a.txt").write_text("one\n")
    runs = [call(passing, cwd=plain)[2] for _ in range(2)]
    step("no-git-runs", runs == [1, 1] and not list(plain.rglob("teamwork-passes")), runs)
    locked = work / "locked"
    locked.mkdir()
    (locked / "a.txt").write_text("one\n")
    git("init", "-q", "-b", "main", cwd=locked)
    git("add", ".", cwd=locked)
    git("commit", "-q", "-m", "base", cwd=locked)
    subprocess.run(["chmod", "-R", "a-w", str(locked / ".git")], check=True)
    body = work / "body.md"
    body.write_text(BODY.format(command="grep -q one a.txt && echo ok"))
    done = box.python(SCRIPT, body, cwd=locked)
    subprocess.run(["chmod", "-R", "u+w", str(locked / ".git")], check=True)
    step("locked-git-dir-runs", done.returncode == 0 and "| pass | ok |" in done.stdout and "Traceback" not in done.stderr, (done.returncode, done.stdout, done.stderr))
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
