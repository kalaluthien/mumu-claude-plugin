#!/usr/bin/env python3
"""Replay check-page.py on each page in this folder and on the starter diagram page, comparing each with the verdict its name expects.

usage: replay-check-page.py

A `follows-*.html` page, and `../assets/diagram-page.html`, must print `follows` and exit 0; a `break-<rule>.html` page
must print only `break <rule>:` lines and exit 1. It prints one PASS or FAIL line per page, then PASS or FAIL."""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
CHECK = HERE.parent / "scripts" / "check-page.py"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    pages = sorted(HERE.glob("*.html")) + [HERE.parent / "assets" / "diagram-page.html"]
    failed = 0
    for page in pages:
        run = subprocess.run([sys.executable, str(CHECK), str(page)], capture_output=True, text=True)
        lines = run.stdout.splitlines()
        if page.name.startswith("break-"):
            rule = page.stem.removeprefix("break-")
            right = run.returncode == 1 and lines and all(line.startswith(f"break {rule}: ") for line in lines)
        else:
            right = run.returncode == 0 and lines == ["follows"]
        failed += not right
        print(f"{'PASS' if right else 'FAIL'} {page.name}: {' / '.join(lines) or run.stderr.strip()}")
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
