#!/usr/bin/env python3
"""Print the worker prompt's steering lines by key, so a manager never reads the table whole. With no key it prints each key with the case it fits,
never the lines; with keys it prints their lines, refusing, exit 2, an unknown key, a key beside one that takes its line alone, and lines over the cap.

usage: print-steering.py [<key>...]"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import steering_lines  # noqa: E402


def main(args):
    if any(arg.startswith("-") for arg in args):
        print(__doc__, file=sys.stderr)
        return 2
    if not args:
        for row in steering_lines.rows():
            print(f"{row['key']}{' (alone)' if row['with'] == 'alone' else ''}: {row['case']}")
        print("Pass the keys that fit as `--steer <key>` to start-session.py, or as arguments here for the lines to `tell` a live worker.")
        return 0
    try:
        print(steering_lines.lines(args))
    except ValueError as e:
        print(f"print-steering: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
