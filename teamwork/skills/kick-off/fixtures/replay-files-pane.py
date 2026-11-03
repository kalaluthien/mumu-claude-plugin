#!/usr/bin/env python3
"""Check that the issue pane draws a files board, or with `--board git` a git board, as it draws the same issues from GitHub: file a root whose parts are an open held task, a task waiting on it, a
completed task and a not-planned one through use-board.py, every link a body line, then compare list-issue-board.py's lines on the files board with its lines on GitHub-shaped nodes
written here by hand. Prints `ok pane` and exits 0, else `fail pane:` with the two outputs and exit 1.

usage: replay-files-pane.py [--board git]"""
import difflib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
LIST = ROOT / "hooks" / "list-issue-board.py"
HOLD = "## Goal\n\nProbe {n}.\n\n```teamwork\nholders: probe-worker\n```\n\n## Definition of done\n\n1. [check] **probe passes**: `echo ok` prints `ok`; on base nothing.\n"
PLAIN = "## Goal\n\nProbe {n}.\n\n## Definition of done\n\n1. [check] **probe passes**: `echo ok` prints `ok`; on base nothing.\n"
ROOT_BODY = "Probe the pane by a root.\n\n## Definition of done\n\n" + "".join(f"{n - 1}. [task] #{n} Probe part {n}\n" for n in range(2, 6))
BODIES = {1: ROOT_BODY, 2: HOLD.format(n=2), 3: PLAIN.format(n=3).replace("## Definition", "```teamwork\ndepends on: #2\n```\n\n## Definition"), 4: PLAIN.format(n=4), 5: PLAIN.format(n=5)}
TITLES = {1: "Probe the pane root", 2: "Probe the held task", 3: "Probe the waiting task", 4: "Probe the done task", 5: "Probe the stopped task"}


def node(number, **more):
    return {"number": number, "title": TITLES[number], "url": f"https://github.com/o/r/issues/{number}", "body": BODIES[number], "authorAssociation": "OWNER",
            "labels": {"nodes": []}, "comments": {"nodes": []}, **more}


def github_nodes():
    """What GitHub's read gives for the issues filed below, its native links left out: the open ones, then the closed ones its bodies name."""
    return [node(1), node(2), node(3), node(4, state="CLOSED", stateReason="COMPLETED"), node(5, state="CLOSED", stateReason="NOT_PLANNED")]


def step(name, ok, detail=""):
    """Print `ok <name>`, or `fail <name>: <detail>`, and give the exit status it means."""
    print(f"ok {name}" if ok else f"fail {name}: {detail.strip()}", flush=True)
    return 0 if ok else 1


def main(args):
    if args not in ([], ["--board", "git"]):
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="files-pane-"))
    env = {**os.environ, "TEAMWORK_BOARD": args[1] if args else "files", "TEAMWORK_BOARD_DIR": str(work / "board"), "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "home")}
    subprocess.run(["git", "init", "-q", str(work / "repo")], check=True)  # the git board's repository; the files board ignores it
    use = lambda *argv: subprocess.run([sys.executable, str(USE), *map(str, argv)], env=env, cwd=work / "repo", capture_output=True, text=True, check=True).stdout
    # the root is filed with its part lines masked, since a link to an issue not filed yet is refused, and unmasked once its parts exist
    for number in BODIES:
        (work / f"{number}.md").write_text(BODIES[number].replace("#", "#~") if number == 1 else BODIES[number])
        use("file", TITLES[number], work / f"{number}.md")
    (work / "root.diff").write_text("".join(difflib.unified_diff(BODIES[1].replace("#", "#~").splitlines(True), BODIES[1].splitlines(True), "a", "b")))
    use("edit", 1, work / "root.diff", "DECIDED: the root names its parts")
    for number, flag in ((4, []), (5, ["--not-planned"])):
        (work / "done.md").write_text("REPORTED: probe done\n")
        use("resolve", number, work / "done.md", *flag)
    files = subprocess.run([sys.executable, str(LIST), "x"], env=env, cwd=work / "repo", capture_output=True, text=True)
    (work / "nodes.json").write_text(json.dumps(github_nodes()))
    github = subprocess.run([sys.executable, str(LIST), "--nodes", str(work / "nodes.json")], env={**env, "TEAMWORK_BOARD": "github"}, capture_output=True, text=True)
    same = not files.returncode and not github.returncode and files.stdout == github.stdout and "closed stopped" in files.stdout
    return step("pane", same, f"files board:\n{files.stdout}{files.stderr}\ngithub nodes:\n{github.stdout}{github.stderr}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
