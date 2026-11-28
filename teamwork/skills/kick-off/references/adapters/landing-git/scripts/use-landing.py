#!/usr/bin/env python3
"""Do one operation of the local git landing, which keeps each change in the main checkout's `.teamwork/changes`.

usage: use-landing.py <operation> <args> [--repository <folder>]

  change <branch> <title> <body-file> [base]   file BRANCH as a change into BASE, by default the main checkout's branch; print its url
  merge <change> <sha>                         squash SHA, the branch tip a judge approved, onto the base; print the new commit
  close <change> <reason>                      close an open change unmerged, a worker only its own; print its url"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[6] / "lib"))
import board_writers  # noqa: E402
import data_folder  # noqa: E402
import landing_git  # noqa: E402


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    args = data_folder.enter(args, __doc__)
    verb, *operands = args or [""]
    if any(argument.startswith("--") for argument in args):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        if verb == "change" and len(operands) in (3, 4):
            if landing_git.folder() is None:
                sys.exit("use-landing: run it inside the repository")
            base = landing_git.git("symbolic-ref", "--short", "HEAD", cwd=data_folder.common_folder().parent).stdout.strip()
            print(landing_git.change(operands[0], operands[1], pathlib.Path(operands[2]).read_text(), operands[3] if operands[3:] else base))
        elif verb == "merge" and len(operands) == 2:
            print(landing_git.merge(*operands))
        elif verb == "close" and len(operands) == 2:
            print(landing_git.close(operands[0], operands[1], board_writers.writer()))
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except (OSError, LookupError) as e:
        sys.exit(f"use-landing: {e}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
