#!/usr/bin/env python3
"""Print `PASS` when `AGENTS.md` holds a `Reference layout` rule, `.github/check-repository.py` is clean on a copy of the repository, and the same copy with a Markdown file planted at a skill's top level, one under its `scripts/`
and one in an unlisted folder makes it print three `misplaced` failures and exit 1, else `FAIL: <what differed>`.

usage: replay-reference-layout.py"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[4]
STRAYS = ("teamwork/skills/kick-off/stray-playbook.md", "teamwork/skills/kick-off/scripts/stray-playbook.md", "teamwork/skills/kick-off/misc/stray-playbook.md")


def check(root):
    done = subprocess.run([sys.executable, str(root / ".github/check-repository.py"), str(root)], capture_output=True, text=True)
    # a copy has no git history, so list-unreleased.py cannot run in it
    failures = [line for line in done.stdout.splitlines() if line.startswith(("unreached ", "shared ", "misplaced "))]
    return int(bool(failures)), [line for line in failures if line.startswith("misplaced ")], failures


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    problems = [] if "**Reference layout**" in (ROOT / "AGENTS.md").read_text() else ["AGENTS.md holds no Reference layout rule"]
    problems += [f"{path} is outside the hierarchy" for path in ("teamwork/skills/kick-off/references/handoff-task.md", "teamwork/skills/kick-off/assets/handoff-worker-prompt.md") if not (ROOT / path).is_file()]
    copy = pathlib.Path(tempfile.mkdtemp(prefix="reference-layout-"))
    names = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True, check=True).stdout.split("\n")
    for name in filter(None, names):
        if (ROOT / name).is_file():
            (copy / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, copy / name)
    status, misplaced, last = check(copy)
    if status or misplaced:
        problems.append(f"the clean copy failed: {last}")
    for stray in STRAYS:
        (copy / stray).parent.mkdir(parents=True, exist_ok=True)
        (copy / stray).write_text("# Stray\n")
    status, misplaced, last = check(copy)
    if status != 1 or len(misplaced) != len(STRAYS):
        problems.append(f"the copy with {len(STRAYS)} strays exited {status} with {len(misplaced)} misplaced lines")
    shutil.rmtree(copy, ignore_errors=True)
    print("PASS" if not problems else "FAIL: " + "; ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
