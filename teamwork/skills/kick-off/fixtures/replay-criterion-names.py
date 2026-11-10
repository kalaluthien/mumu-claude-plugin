#!/usr/bin/env python3
"""Check that criterion names are complete sentences, on a git board in a temporary repository, and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-criterion-names.py [--case <name>]   (no argument: every one in turn)
- gate: `file` refuses a body whose criterion is named by a label and posts nothing, `edit` refuses a diff that adds one and leaves the body as it was, both name the Complete sentence rule, a body whose names are sentences is filed, and the pane's list shows each full sentence on its `☐` line"""
import os
import pathlib
import subprocess
import sys
import tempfile

LIB = pathlib.Path(__file__).resolve().parents[3] / "lib"
sys.path.insert(0, str(LIB))
import replay_probe  # noqa: E402

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
LISTER = pathlib.Path(__file__).resolve().parents[3] / "hooks" / "list-issue-board.py"
SENTENCE = "The closed list shows the latest four tasks"
BODY = "## Goal\n\nProbe the names.\n\nPath: caller: the session start; meets: the owner in the pane\n\n## Definition of done\n\n1. [check] **{name}**: `echo PASS` prints `PASS`; on base `FAIL`.\n"


def case_gate():
    work = pathlib.Path(tempfile.mkdtemp(prefix="names-"))
    repository = work / "proj"
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    environment = {**os.environ, "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "home")}
    (work / "label.md").write_text(BODY.format(name="Four closed"))
    filed = replay_probe.run_python(SCRIPTS / "use-board.py", repository, environment, "file", "Probe the names", work / "label.md")
    if filed.returncode != 2 or "Complete sentence" not in filed.stderr or replay_probe.run_python(SCRIPTS / "use-board.py", repository, environment, "read", "1").returncode == 0:
        return replay_probe.fail(f"a label was filed or not named: exit {filed.returncode}, {filed.stderr.strip()[-200:]!r}")
    (work / "sentence.md").write_text(BODY.format(name=SENTENCE))
    filed = replay_probe.run_python(SCRIPTS / "use-board.py", repository, environment, "file", "Probe the names", work / "sentence.md")
    if filed.returncode:
        return replay_probe.fail(f"a sentence was refused: {filed.stderr.strip()[-200:]!r}")
    shown = replay_probe.run_python(LISTER, repository, environment, "proj").stdout
    if f"☐ {SENTENCE}" not in shown or "○ " in shown:
        return replay_probe.fail(f"the pane's list lacks the sentence on its box line or keeps a circle: {shown!r}")
    before = replay_probe.run_python(SCRIPTS / "use-board.py", repository, environment, "read", "1").stdout
    sha = next(line.split("body sha: ")[1].strip() for line in before.splitlines() if "body sha: " in line)
    (work / "old").write_text(BODY.format(name=SENTENCE))
    (work / "new").write_text(BODY.format(name=SENTENCE) + "2. [check] **Honest count**: `echo PASS` prints `PASS`; on base `FAIL`.\n")
    diff = subprocess.run(["diff", "-u", "--label", "a/body", "--label", "b/body", "old", "new"], cwd=work, capture_output=True, text=True).stdout
    (work / "edit.diff").write_text(diff)
    edited = replay_probe.run_python(SCRIPTS / "use-board.py", repository, environment, "edit", "1", work / "edit.diff", "DECIDED: add a label", "--base", sha)
    if edited.returncode != 2 or "Complete sentence" not in edited.stderr or replay_probe.run_python(SCRIPTS / "use-board.py", repository, environment, "read", "1").stdout != before:
        return replay_probe.fail(f"an edit that adds a label was not refused cleanly: exit {edited.returncode}, {edited.stderr.strip()[-200:]!r}")
    return 0



CASES = {"gate": case_gate}


def main(args):
    if not args:
        return replay_probe.run_every(__file__, "--case", CASES)
    if len(args) != 2 or args[0] != "--case" or args[1] not in CASES:
        print(__doc__, file=sys.stderr)
        return 2
    if CASES[args[1]]():
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
