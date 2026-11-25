#!/usr/bin/env python3
"""Check where the local changes land, and that their data stays out of commits and out of `.git/teamwork`, in a scratch repository and its worktree.
Prints `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`, and exits 1 when any fails.

usage: replay-data-folder.py"""
import pathlib
import sys

LIB = pathlib.Path(__file__).resolve().parents[3] / "lib"
sys.path.insert(0, str(LIB))
import replay_probe  # noqa: E402


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("data-folder-") as work:
        sandbox = replay_probe.Sandbox(work)
        repository, tree = sandbox.repository, work / "tree"
        sandbox.git("worktree", "add", "-q", tree)
        (repository / ".teamwork").mkdir()
        replay_probe.write_text(repository / ".teamwork", "settings.json", "{}\n")
        sandbox.git("add", ".teamwork/settings.json")  # committed, so an unexcluded data folder shows in status by its own name
        sandbox.git("commit", "-q", "-m", "settings")
        # the data an older version kept in the common folder, which the first read must move
        older = repository / ".git" / "teamwork" / "changes"
        older.mkdir(parents=True)
        replay_probe.write_text(older, "3.json", "{}")

        def where(folder):
            done = sandbox.run([sys.executable, "-c", "import landing_git; print(landing_git.folder())"], cwd=folder, PYTHONPATH=LIB)
            return done.stdout.strip() or done.stderr.strip()

        def matches(name, got, want):
            cases.step(name, got == want, f"{got} != {want}")

        def ignored(path):
            return sandbox.run(["git", "check-ignore", "-q", path]).returncode == 0

        changes = repository / ".teamwork" / "changes"
        matches("changes-folder", [where(folder) for folder in (repository, tree)], [str(changes)] * 2)
        matches("moved", ((changes / "3.json").exists(), older.exists(), older.parent.exists()), (True, False, False))
        changes.mkdir(parents=True, exist_ok=True)
        replay_probe.write_text(changes, "1.json", "{}")  # a change record, as use-landing.py leaves it
        matches("excluded", (ignored(".teamwork/changes/1.json"), ignored(".teamwork/settings.json")), (True, False))
        matches("exclude-once", (repository / ".git" / "info" / "exclude").read_text().splitlines().count("/.teamwork/changes/"), 1)
        matches("clean-status", [line for line in sandbox.git("status", "--porcelain").splitlines() if "changes" in line], [])
        matches("no-git-data", (repository / ".git" / "teamwork").exists(), False)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
