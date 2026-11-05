#!/usr/bin/env python3
"""Print the characters of the teamwork text a session loads before its first step, per role, at a commit and at the checkout, and PASS when the checkout holds fewer in all and no role holds more.

usage: count-start-text.py <ref>

The text of a role is the description of every teamwork skill, which loads at start, plus the files its kick-off reads before
its first step: `SKILL.md`, `protocol.md`, its playbook and the files that playbook tells it to read first. A file the ref
lacks counts as 0, so a ref before a file existed does not charge the file's growth to a role that never read it."""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
KICK_OFF = "teamwork/skills/kick-off/"
READS = {
    "worker": ["SKILL.md", "references/protocol.md", "references/worker.md", "references/adapters.md",
               "references/adapters/board.md", "references/issue-grammar.md", "references/recall.md"],
    "manager": ["SKILL.md", "references/protocol.md", "references/manager.md", "references/adapters.md",
                "references/adapters/board.md", "references/issue-grammar.md", "references/handoff.md", "references/recall.md"],
    "sentinel": ["SKILL.md", "references/protocol.md", "references/sentinel.md", "references/adapters.md"],
    "judge": ["references/judge.md", "references/protocol.md", "references/adapters.md", "references/adapters/landing-git.md",
              "references/issue-grammar.md"],
}


def show(ref, path):
    if ref is None:
        file = ROOT / path
        return file.read_text() if file.is_file() else ""
    done = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:{path}"], capture_output=True, text=True)
    return done.stdout if done.returncode == 0 else ""


def descriptions(ref):
    skills = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "--name-only", ref or "HEAD", "teamwork/skills/"],
                            capture_output=True, text=True).stdout.split()
    if ref is None:
        skills = [str(path.relative_to(ROOT)) for path in sorted((ROOT / "teamwork/skills").iterdir())]
    total = 0
    for skill in skills:
        match = re.search(r"^description: (.*)$", show(ref, f"{skill}/SKILL.md"), re.MULTILINE)
        total += len(match.group(1)) if match else 0
    return total


def count(ref):
    start = descriptions(ref)
    return {role: start + sum(len(show(ref, KICK_OFF + name)) for name in names) for role, names in READS.items()}


def main(args):
    if len(args) != 1 or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    before, after = count(args[0]), count(None)
    print("| role | at ref | at checkout |\n| --- | --- | --- |")
    for role in READS:
        print(f"| {role} | {before[role]:,} | {after[role]:,} |")
    print(f"| all | {sum(before.values()):,} | {sum(after.values()):,} |")
    fewer = sum(after.values()) < sum(before.values()) and all(after[role] <= before[role] for role in READS)
    print("PASS" if fewer else "FAIL")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
