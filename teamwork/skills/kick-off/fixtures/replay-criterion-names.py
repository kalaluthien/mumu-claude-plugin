#!/usr/bin/env python3
"""Check that criterion names are complete sentences, on a git board in a temporary repository or on this repository's own, and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-criterion-names.py --case <name>
- gate: `file` refuses a body whose criterion is named by a label and posts nothing, `edit` refuses a diff that adds one and leaves the body as it was, both name the Complete sentence rule, a body whose names are sentences is filed, and the pane's list shows each full sentence on its `○` line
- open: every open task of this repository's board names each criterion by a sentence that `issue_state.sentence` and `issue_state.plain` accept"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
LIB = pathlib.Path(__file__).resolve().parents[3] / "lib"
LISTER = pathlib.Path(__file__).resolve().parents[3] / "hooks" / "list-issue-board.py"
SENTENCE = "The closed list shows the latest four tasks"
BODY = "## Goal\n\nProbe the names.\n\n## Definition of done\n\n1. [check] **{name}**: `echo PASS` prints `PASS`; on base `FAIL`.\n"


def run(env, repo, script, *argv):
    return subprocess.run([sys.executable, str(script), *map(str, argv)], cwd=repo, capture_output=True, text=True, env=env)


def fail(why):
    print(f"FAIL: {why}")
    return 1


def case_gate():
    work = pathlib.Path(tempfile.mkdtemp(prefix="names-"))
    repo = work / "proj"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    env = {**os.environ, "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "home")}
    (work / "label.md").write_text(BODY.format(name="Four closed"))
    filed = run(env, repo, SCRIPTS / "use-board.py", "file", "Probe the names", work / "label.md")
    if filed.returncode != 2 or "Complete sentence" not in filed.stderr or run(env, repo, SCRIPTS / "use-board.py", "read", "1").returncode == 0:
        return fail(f"a label was filed or not named: exit {filed.returncode}, {filed.stderr.strip()[-200:]!r}")
    (work / "sentence.md").write_text(BODY.format(name=SENTENCE))
    filed = run(env, repo, SCRIPTS / "use-board.py", "file", "Probe the names", work / "sentence.md")
    if filed.returncode:
        return fail(f"a sentence was refused: {filed.stderr.strip()[-200:]!r}")
    shown = run(env, repo, LISTER, "proj").stdout
    if f"○ {SENTENCE}" not in shown:
        return fail(f"the pane's list lacks the sentence on its circle line: {shown!r}")
    before = run(env, repo, SCRIPTS / "use-board.py", "read", "1").stdout
    sha = next(line.split("body sha: ")[1].strip() for line in before.splitlines() if "body sha: " in line)
    (work / "old").write_text(BODY.format(name=SENTENCE))
    (work / "new").write_text(BODY.format(name=SENTENCE) + "2. [check] **Honest count**: `echo PASS` prints `PASS`; on base `FAIL`.\n")
    diff = subprocess.run(["diff", "-u", "--label", "a/body", "--label", "b/body", "old", "new"], cwd=work, capture_output=True, text=True).stdout
    (work / "edit.diff").write_text(diff)
    edited = run(env, repo, SCRIPTS / "use-board.py", "edit", "1", work / "edit.diff", "DECIDED: add a label", "--base", sha)
    if edited.returncode != 2 or "Complete sentence" not in edited.stderr or run(env, repo, SCRIPTS / "use-board.py", "read", "1").stdout != before:
        return fail(f"an edit that adds a label was not refused cleanly: exit {edited.returncode}, {edited.stderr.strip()[-200:]!r}")
    return 0


def case_open():
    sys.path.insert(0, str(LIB))
    import issue_state
    common = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=True).stdout.strip()
    show = lambda path: subprocess.run(["git", f"--git-dir={common}", "show", f"refs/teamwork-blackboard:{path}"], capture_output=True, text=True).stdout
    tree = subprocess.run(["git", f"--git-dir={common}", "ls-tree", "--name-only", "-r", "refs/teamwork-blackboard"], capture_output=True, text=True).stdout.split()
    bad = []
    for path in tree:
        if path.endswith("issue.json") and str(json.loads(show(path)).get("state", "")).lower() == "open":
            body = show(path.replace("issue.json", "body.md"))
            for item in issue_state.ITEM.findall(issue_state.sections(body).get("done", "")):
                name = issue_state.CRITERION.match(item).group(3)
                if name and (issue_state.sentence("criterion name", name) or issue_state.plain("criterion name", name)):
                    bad.append(f"{path.rsplit('/', 2)[0]}: {name}")
    return fail("; ".join(bad)) if bad else 0


CASES = {"gate": case_gate, "open": case_open}


def main(args):
    if len(args) != 2 or args[0] != "--case" or args[1] not in CASES:
        print(__doc__, file=sys.stderr)
        return 2
    if CASES[args[1]]():
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
