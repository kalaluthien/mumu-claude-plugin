#!/usr/bin/env python3
"""Build one repository of each kind in a temporary folder, run check-repository-owner.py on them, and print one line per
kind and `probe: <passed> of <kinds> kinds right`; exit 0 only when all are right.

usage: replay-repository-owner.py

The repositories are built at run time, since a fixture folder cannot hold a `.git`.
"""
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
CHECK = HERE.parent / "scripts" / "check-repository-owner.py"
LOGIN = "fixture-owner"


def git(*args):
    subprocess.run(["git", *args], check=True, capture_output=True)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    top = pathlib.Path(tempfile.mkdtemp(prefix="replay-repository-owner-"))
    own, other, local, plain = top / "own", top / "other", top / "local", top / "plain"
    git("init", "-q", str(own))
    git("-C", str(own), "remote", "add", "origin", f"git@github.com:{LOGIN}/tools.git")
    (own / ".gitignore").write_text("/plugins/\n")
    copy = own / "plugins" / "copy"
    copy.mkdir(parents=True)
    git("init", "-q", str(other))
    git("-C", str(other), "remote", "add", "origin", f"https://github.com/{LOGIN}-other/tools.git")
    git("init", "-q", str(local))
    plain.mkdir()
    kinds = [("own origin", own, "own"), ("another's origin", other, "foreign"), ("no origin", local, "own"),
             ("ignored by its repository", copy, "foreign"), ("in no repository", plain, "foreign")]
    result = subprocess.run([sys.executable, str(CHECK), LOGIN, *(str(path) for _, path, _ in kinds)],
                            capture_output=True, text=True, check=False)
    lines = result.stdout.splitlines()
    passed = 0
    for (name, _, want), line in zip(kinds, lines):
        right = line.split(" ", 1)[0] == want
        passed += right
        print(f"{'ok' if right else 'WRONG'} {name}: want {want}, got {line}")
    print(f"probe: {passed} of {len(kinds)} kinds right")
    return 0 if passed == len(kinds) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
