#!/usr/bin/env python3
"""Print `PASS` when `AGENTS.md` holds a `Reference layout` rule, `.github/check-repository.py` is clean on a copy of the repository, and the same copy with a Markdown file planted at a skill's top level, one under its `scripts/`
and one in an unlisted folder makes it print three `misplaced` failures and exit 1, else `FAIL: <what differed>` and exit 1.

usage: replay-reference-layout.py"""
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "teamwork" / "lib"))
import replay_probe  # noqa: E402

STRAYS = ("teamwork/skills/kick-off/stray-playbook.md", "teamwork/skills/kick-off/scripts/stray-playbook.md", "teamwork/skills/kick-off/misc/stray-playbook.md")


def check(root, environment):
    done = replay_probe.sh(sys.executable, root / ".github/check-repository.py", "--skip-fixtures", root, cwd=root, environment=environment, check=False, timeout=600)
    # a copy has no git history, so list-unreleased.py cannot run in it
    failures = [line for line in done.stdout.splitlines() if line.startswith(("unreached ", "shared ", "misplaced "))]
    return int(bool(failures)), [line for line in failures if line.startswith("misplaced ")], failures


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    problems = [] if "**Reference layout**" in (ROOT / "AGENTS.md").read_text() else ["AGENTS.md holds no Reference layout rule"]
    names = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True, check=True).stdout.split("\n")
    with replay_probe.scratch("reference-layout-") as work:
        copy, environment = work / "copy", replay_probe.isolated(work)
        for name in filter(None, names):
            if (ROOT / name).is_file():
                (copy / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, copy / name)
        status, misplaced, last = check(copy, environment)
        if status or misplaced:
            problems.append(f"the clean copy failed: {last}")
        for stray in STRAYS:
            (copy / stray).parent.mkdir(parents=True, exist_ok=True)
            (copy / stray).write_text("# Stray\n")
        status, misplaced, last = check(copy, environment)
        if status != 1 or len(misplaced) != len(STRAYS):
            problems.append(f"the copy with {len(STRAYS)} strays exited {status} with {len(misplaced)} misplaced lines")
    return replay_probe.fail("; ".join(problems)) if problems else replay_probe.Cases().finish()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
