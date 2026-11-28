#!/usr/bin/env python3
"""Start 8 processes that comment on one task and file tasks at once on a scratch git board, then count every record.

usage: replay-board-writers.py [--case concurrent|unguarded]   (no argument: every one in turn)

- `concurrent`: prints `PASS` as its last line only when every comment and task the writers posted is on the board exactly once,
  every writer exited 0, and the ref's history is one line of commits, one per write.
- `unguarded`: runs the same scenario on a copy of the board code whose `update-ref` drops its old-value argument, and prints `PASS`
  only when the scenario then finds a lost record, which shows that argument is what keeps the records.

Each case prints a line per finding, then `PASS` or `FAIL`, and exits 1 on `FAIL`."""
import collections
import json
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
REF = "refs/teamwork-blackboard"
WRITERS = 8
COMMENTS = 12  # per writer
FILINGS = 4  # per writer
GUARDED = 'REF, new, self.tip or "")'
UNGUARDED = "REF, new)"

WRITER_SCRIPT = """
for k in $(seq {comments}); do
  python3 "$USE" comment 1 --reported "w{writer}-c$k" >/dev/null 2>>"$WORK/errors-{writer}" || echo "comment w{writer}-c$k exited $?" >> "$WORK/errors-{writer}"
  if [ "$k" -le {filings} ]; then
    printf 'w{writer}-t%s\\n' "$k" > "$WORK/body-{writer}"
    python3 "$USE" file --title "w{writer}-t$k" --body "$WORK/body-{writer}" >/dev/null 2>>"$WORK/errors-{writer}" || echo "file w{writer}-t$k exited $?" >> "$WORK/errors-{writer}"
  fi
done
"""


def run_writers(use, box):
    """Returns the findings, each a sentence; none means every record is there once."""
    work, repository, git = box.work, box.repository, box.git
    environment = {**box.environment, "USE": str(use), "WORK": str(work)}
    replay_probe.write_text(work, "seed", "The task the writers comment on.\n")
    box.python(use, "file", "--title", "Seed", "--body", work / "seed")
    running = [subprocess.Popen(["sh", "-c", WRITER_SCRIPT.format(writer=i, comments=COMMENTS, filings=FILINGS)], cwd=repository, env=environment) for i in range(WRITERS)]
    for process in running:
        process.wait()

    findings = []
    for i in range(WRITERS):
        errors = work / f"errors-{i}"
        if errors.exists() and errors.read_text().strip():
            findings.append(f"writer {i} reported: {errors.read_text().strip().splitlines()[0]}")

    paths = git("ls-tree", "-r", "--name-only", REF).split()
    read = lambda path: git("show", f"{REF}:{path}")
    comments = collections.Counter(json.loads(read(path))["line"] for path in paths if path.startswith("1/comments/"))
    titles = collections.Counter(json.loads(read(path))["title"] for path in paths if path.endswith("/task.json") and path != "1/task.json")
    for kind, found, expected in (("comment", comments, {f"w{i}-c{k}" for i in range(WRITERS) for k in range(1, COMMENTS + 1)}),
                                  ("task", titles, {f"w{i}-t{k}" for i in range(WRITERS) for k in range(1, FILINGS + 1)})):
        lost = sorted(expected - set(found))
        doubled = sorted(name for name, n in found.items() if n > 1)
        if lost:
            findings.append(f"{len(lost)} of {len(expected)} {kind}s are missing, such as {lost[0]}")
        if doubled:
            findings.append(f"{len(doubled)} {kind}s are on the board twice, such as {doubled[0]}")

    history = [line.split() for line in git("rev-list", "--parents", REF).splitlines()]
    forks = [line[0] for line in history if len(line) > 2]
    expected_commits = 1 + WRITERS * (COMMENTS + FILINGS)
    if forks:
        findings.append(f"{len(forks)} commits of the history have two parents, such as {forks[0]}")
    if len(history) != expected_commits:
        findings.append(f"the history holds {len(history)} commits, not {expected_commits}: one per write and the seed")
    return findings


def main(args):
    if not args:
        return replay_probe.run_every(__file__, "--case", ("concurrent", "unguarded"))
    if len(args) != 2 or args[0] != "--case" or args[1] not in ("concurrent", "unguarded"):
        print(__doc__, file=sys.stderr)
        return 2
    case = args[1]
    with replay_probe.scratch("board-writers-") as work:
        box = replay_probe.Sandbox(work)
        use = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
        if case == "unguarded":
            copy = work / "unguarded"
            shutil.copytree(ROOT / "lib", copy / "lib")
            shutil.copytree(ROOT / "skills" / "kick-off", copy / "skills" / "kick-off", ignore=shutil.ignore_patterns("fixtures"))
            board_git = copy / "lib" / "board_git.py"
            text = board_git.read_text()
            if GUARDED not in text:
                return replay_probe.fail(f"the board code no longer holds `{GUARDED}`, so the unguarded copy cannot be made")
            board_git.write_text(text.replace(GUARDED, UNGUARDED))
            use = copy / "skills" / "kick-off" / "scripts" / "use-board.py"
        findings = run_writers(use, box)
    for finding in findings:
        print(finding)
    passed = bool(findings) == (case == "unguarded")
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
