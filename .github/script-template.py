#!/usr/bin/env python3
"""Echo a word: the docstring opens with one sentence saying what the script does.

usage: script-template.py <word> [--upper-case]

One `usage:` line per call, then what the script prints and how it exits. Standard library only, Python 3.9."""

import pathlib
import sys

# A plugin script reaches its plugin's lib/ at the depth <n> its folder sits below the plugin root.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
# Its own folder; a folder above it is ROOT = pathlib.Path(__file__).resolve().parents[<n>].
HERE = pathlib.Path(__file__).resolve().parent

FLAGS = {"--upper-case"}  # a flag is lowercase words joined by -


def main(args):
    words = [arg for arg in args if arg not in FLAGS]
    # A call it cannot read prints the docstring on stderr, nothing on stdout, and exits 2; a hook never exits 2 here, since Claude Code reads exit 2 as a block.
    if len(words) != 1 or words[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    print(words[0].upper() if "--upper-case" in args else words[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
