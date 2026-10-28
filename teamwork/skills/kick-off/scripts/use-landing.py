#!/usr/bin/env python3
"""Do one operation of the local git landing, which keeps each change in the main checkout's `.teamwork/changes`.

usage: use-landing.py <operation> <args>

  change <branch> <title> <body-file> [base]   file BRANCH as a change into BASE, by default the main checkout's branch; print its url
  merge <change> <sha>                         squash SHA, the branch tip a judge approved, onto the base; print the new commit"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import data_folder  # noqa: E402
import landing_git  # noqa: E402


def main(args):
    verb, *operands = args or [""]
    try:
        if verb == "change" and len(operands) in (3, 4):
            if landing_git.folder() is None:
                sys.exit("use-landing: run it inside the repository")
            base = landing_git.git("symbolic-ref", "--short", "HEAD", cwd=data_folder.common_folder().parent).stdout.strip()
            print(landing_git.change(operands[0], operands[1], pathlib.Path(operands[2]).read_text(), operands[3] if operands[3:] else base))
        elif verb == "merge" and len(operands) == 2:
            print(landing_git.merge(*operands))
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except (OSError, LookupError) as e:
        sys.exit(f"use-landing: {e}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
