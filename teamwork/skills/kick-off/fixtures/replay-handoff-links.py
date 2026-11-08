#!/usr/bin/env python3
"""Print `PASS` when the handoff files are named for what they hold (`references/handoff-task.md` and `assets/handoff-worker-prompt.md` exist, `references/handoff.md` does not), no Markdown file of `teamwork/` names `handoff.md`,
and `.github/check-repository.py` reports no failure, else `FAIL: <what differed>`.

usage: replay-handoff-links.py"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
KICK_OFF = ROOT / "teamwork/skills/kick-off"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    problems = [f"{path} {'is missing' if want else 'still exists'}" for path, want in (
        ("references/handoff-task.md", True), ("assets/handoff-worker-prompt.md", True), ("references/handoff.md", False)) if (KICK_OFF / path).is_file() != want]
    names = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard", "teamwork"], capture_output=True, text=True, check=True).stdout.split()
    problems += [f"{name} names handoff.md" for name in names if name.endswith(".md") and (ROOT / name).is_file() and (ROOT / name) != pathlib.Path(__file__).resolve() and re.search(r"(?<![\w-])handoff\.md", (ROOT / name).read_text(errors="replace"))]
    checked = subprocess.run([sys.executable, str(ROOT / ".github/check-repository.py"), str(ROOT)], capture_output=True, text=True)
    if checked.returncode:
        problems.append("check-repository.py: " + checked.stdout.strip().splitlines()[-1])
    print("PASS" if not problems else "FAIL: " + "; ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
