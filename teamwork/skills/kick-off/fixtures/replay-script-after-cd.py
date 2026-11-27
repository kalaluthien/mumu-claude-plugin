#!/usr/bin/env python3
"""Check that `use-board.py` refuses a body or a comment that runs a teamwork script after a `cd`, in a scratch git repository, and print `ok <case>` or `fail <case>: <what it saw>`
per case, then `PASS script after cd` or `FAIL script after cd`; exit 1 on any failure:
- `refused`: `file` with a body, `comment` with a text and `edit` with a new body that each run `use-board.py` after a `cd` into a folder in one command line exit 2 naming the `cd` and printing the line, and post and store nothing;
- `other folder`: the same with a script of the plugin's `monitors/` folder;
- `allowed`: the same three writes with the call made by `--repository <folder>`, or after a `cd ~`, or a `cd` before a fixture or a module that is no script, in place of it exit 0.

usage: replay-script-after-cd.py"""
import pathlib
import sys

SKILL = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL.parents[1] / "lib"))
import replay_probe  # noqa: E402

USE = SKILL / "scripts" / "use-board.py"
CALL = "python3 use-board.py read 1"
BAD = f"cd /somewhere && {CALL}"
GOOD = (f"{CALL} --repository /somewhere", f"cd ~ && {CALL}", "cd /somewhere && python3 replay-location-arguments.py", "cd /somewhere && python3 task_state.py")
OTHER = "cd /somewhere && python3 print-team-gaps.py"


def writes(box, repository, work, line):
    """The three runs of file, comment and edit with LINE inside their text, in that order."""
    body = replay_probe.BODY.replace("Do it.", f"Do it: {line}")
    filed = box.python(USE, "file", "--title", "Probe a call", "--body", replay_probe.write_text(work, "file.md", body), cwd=repository)
    commented = box.python(USE, "comment", "1", "--reported", "--text", replay_probe.write_text(work, "comment.md", f"Run {line}\n"), cwd=repository)
    sha = box.python(USE, "read", "1", cwd=repository).stdout.split("body sha: ", 1)[1].split()[0]
    edited = box.python(USE, "edit", "1", "--body", replay_probe.write_text(work, "edit.md", body + "\n"), "--reason", "add a call", "--base", sha, cwd=repository)
    return filed, commented, edited


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases("script after cd")
    with replay_probe.scratch("script-after-cd-") as work:
        box = replay_probe.Sandbox(work, [replay_probe.agent("probe-worker", 1)])
        repository = box.init(work / "repository")
        box.python(USE, "file", "--title", "Probe a root", "--body", replay_probe.write_text(work, "root.md", replay_probe.BODY), cwd=repository)
        refused = writes(box, repository, work, BAD)
        cases.step("refused", all(run.returncode == 2 and "`cd`" in run.stderr for run in refused), [(run.returncode, run.stderr[-200:]) for run in refused])
        other = writes(box, repository, work, OTHER)
        cases.step("other folder", all(run.returncode == 2 and OTHER in run.stderr for run in other), [(run.returncode, run.stderr[-200:]) for run in other])
        for line in GOOD:
            made = writes(box, repository, work, line)
            cases.step("allowed", all(run.returncode == 0 for run in made), [(line, run.returncode, run.stderr[-200:]) for run in made])
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
