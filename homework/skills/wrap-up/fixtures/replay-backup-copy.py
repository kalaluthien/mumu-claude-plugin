#!/usr/bin/env python3
"""Run the dream's backup copy on a scratch config and print PASS when each memory folder lands at its own path with its
`memory/` level, FAIL otherwise.

usage: replay-backup-copy.py"""
import pathlib
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "copy-memory-folders.py"
WORKFLOW = pathlib.Path(__file__).resolve().parents[3] / "workflows" / "dreaming-workflow.js"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="replay-backup-copy-") as scratch:
        root = pathlib.Path(scratch).resolve()
        config, backup = root / "config", root / "backup"
        for project in ("-a", "-b"):
            folder = config / "projects" / project / "memory"
            folder.mkdir(parents=True)
            (folder / "MEMORY.md").write_text(f"- note {project}\n")
        (config / "projects" / "-a" / "memory" / "dangling").symlink_to("/nonexistent")
        if not SCRIPT.is_file():
            print(f"FAIL: {SCRIPT} is missing")
            return 1
        subprocess.run([sys.executable, str(SCRIPT), str(config), str(backup)], capture_output=True)
        landed = [backup / (config / "projects" / project / "memory" / "MEMORY.md").relative_to("/") for project in ("-a", "-b")]
        missing = [str(path) for path in landed if not path.is_file()]
        if missing:
            print("FAIL: not at their own path:", *missing)
            return 1
        if "copy-memory-folders.py" not in WORKFLOW.read_text():
            print("FAIL: the dream's set-up step does not run the copy script")
            return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
