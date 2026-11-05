#!/usr/bin/env python3
"""Start 8 processes that comment on one issue and file issues at once on a throwaway git board, then count every record.

usage: replay-board-writers.py --case concurrent|unguarded

- `concurrent`: prints `PASS` as its last line only when every comment and issue the writers posted is on the board exactly once,
  every writer exited 0, and the ref's history is one line of commits, one per write.
- `unguarded`: runs the same scenario on a copy of the board code whose `update-ref` drops its old-value argument, and prints `PASS`
  only when the scenario then finds a lost record, which shows that argument is what keeps the records.

Each case prints a line per finding, then `PASS` or `FAIL`."""
import collections
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
REF = "refs/teamwork-blackboard"
WRITERS = 8
COMMENTS = 12  # per writer
FILINGS = 4  # per writer
GUARDED = 'REF, new, self.tip or "")'
UNGUARDED = "REF, new)"

WRITER_SCRIPT = """
for k in $(seq {comments}); do
  printf 'w{writer}-c%s\\n' "$k" > "$WORK/body-{writer}"
  python3 "$USE" comment 1 "$WORK/body-{writer}" >/dev/null 2>>"$WORK/errors-{writer}" || echo "comment w{writer}-c$k exited $?" >> "$WORK/errors-{writer}"
  if [ "$k" -le {filings} ]; then
    printf 'w{writer}-t%s\\n' "$k" > "$WORK/body-{writer}"
    python3 "$USE" file "w{writer}-t$k" "$WORK/body-{writer}" >/dev/null 2>>"$WORK/errors-{writer}" || echo "file w{writer}-t$k exited $?" >> "$WORK/errors-{writer}"
  fi
done
"""


def git(repository, *args):
    return subprocess.run(["git", "-C", str(repository), *args], capture_output=True, text=True, check=True).stdout


def run_writers(use, work, repository):
    """Returns the findings, each a sentence; none means every record is there once."""
    environment = {**os.environ, "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "home"), "USE": str(use), "WORK": str(work)}
    (work / "seed").write_text("The issue the writers comment on.\n")
    subprocess.run([sys.executable, str(use), "file", "Seed", str(work / "seed")], cwd=repository, env=environment, capture_output=True, check=True)
    running = [subprocess.Popen(["sh", "-c", WRITER_SCRIPT.format(writer=i, comments=COMMENTS, filings=FILINGS)], cwd=repository, env=environment) for i in range(WRITERS)]
    for process in running:
        process.wait()

    findings = []
    for i in range(WRITERS):
        errors = work / f"errors-{i}"
        if errors.exists() and errors.read_text().strip():
            findings.append(f"writer {i} reported: {errors.read_text().strip().splitlines()[0]}")

    paths = git(repository, "ls-tree", "-r", "--name-only", REF).split()
    read = lambda path: git(repository, "show", f"{REF}:{path}")
    comments = collections.Counter(read(path).strip() for path in paths if path.startswith("1/comments/"))
    titles = collections.Counter(json.loads(read(path))["title"] for path in paths if path.endswith("/issue.json") and path != "1/issue.json")
    for kind, found, expected in (("comment", comments, {f"w{i}-c{k}" for i in range(WRITERS) for k in range(1, COMMENTS + 1)}),
                                  ("issue", titles, {f"w{i}-t{k}" for i in range(WRITERS) for k in range(1, FILINGS + 1)})):
        lost = sorted(expected - set(found))
        doubled = sorted(name for name, n in found.items() if n > 1)
        if lost:
            findings.append(f"{len(lost)} of {len(expected)} {kind}s are missing, such as {lost[0]}")
        if doubled:
            findings.append(f"{len(doubled)} {kind}s are on the board twice, such as {doubled[0]}")

    history = [line.split() for line in git(repository, "rev-list", "--parents", REF).splitlines()]
    forks = [line[0] for line in history if len(line) > 2]
    expected_commits = 1 + WRITERS * (COMMENTS + FILINGS)
    if forks:
        findings.append(f"{len(forks)} commits of the history have two parents, such as {forks[0]}")
    if len(history) != expected_commits:
        findings.append(f"the history holds {len(history)} commits, not {expected_commits}: one per write and the seed")
    return findings


def main(args):
    if len(args) != 2 or args[0] != "--case" or args[1] not in ("concurrent", "unguarded"):
        print(__doc__, file=sys.stderr)
        return 2
    case = args[1]
    work = pathlib.Path(tempfile.mkdtemp(prefix="board-writers-"))
    try:
        repository = work / "repo"
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        use = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
        if case == "unguarded":
            copy = work / "unguarded"
            shutil.copytree(ROOT / "lib", copy / "lib")
            shutil.copytree(ROOT / "skills" / "kick-off", copy / "skills" / "kick-off", ignore=shutil.ignore_patterns("fixtures"))
            board_git = copy / "lib" / "board_git.py"
            text = board_git.read_text()
            if GUARDED not in text:
                print(f"the board code no longer holds `{GUARDED}`, so the unguarded copy cannot be made")
                print("FAIL")
                return 0
            board_git.write_text(text.replace(GUARDED, UNGUARDED))
            use = copy / "skills" / "kick-off" / "scripts" / "use-board.py"
        findings = run_writers(use, work, repository)
        for finding in findings:
            print(finding)
        print("PASS" if bool(findings) == (case == "unguarded") else "FAIL")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
