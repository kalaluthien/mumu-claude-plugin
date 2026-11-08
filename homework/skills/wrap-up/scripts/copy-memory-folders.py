#!/usr/bin/env python3
"""Copy each project memory folder that git does not track into a dream's backup, at its own path below `/`.

usage: copy-memory-folders.py <config> <backup>   copies <config>/projects/*/memory to <backup><config>/projects/*/memory;
                                                  one `copied <folder>` line per folder, then a count

A folder inside a git work tree whose files git tracks has its own history, so it is skipped. The folder itself is
copied, not its contents, and a symlink is copied as a link so a dangling one cannot stop the backup, since `cp -R <folder>/ <backup>` drops the `memory/` level on BSD cp.
"""
import glob
import os
import pathlib
import shutil
import subprocess
import sys


def tracked(folder):
    """True when git lists a file of the folder; false outside a work tree, as when git fails or the folder is ignored."""
    done = subprocess.run(["git", "-C", str(folder), "ls-files"], capture_output=True, text=True)
    return done.returncode == 0 and bool(done.stdout.strip())


def main(args):
    if len(args) != 2 or args[0].startswith("-") or args[1].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    config, backup = pathlib.Path(args[0]).resolve(), pathlib.Path(args[1])
    count = 0
    for name in sorted(glob.glob(os.path.join(glob.escape(str(config)), "projects", "*", "memory"))):
        folder = pathlib.Path(name)
        if not folder.is_dir() or tracked(folder):
            continue
        target = backup / folder.relative_to("/")
        shutil.copytree(folder, target, symlinks=True, dirs_exist_ok=True)
        print(f"copied {folder}")
        count += 1
    print(f"{count} memory folders copied to {backup}, each at its own path below /.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
