#!/usr/bin/env python3
"""Take the dream's run lock, <data>/dream.lock, before this session runs the dreaming workflow on <data>, and print
whether to run it.

usage: lock-dream.py <data>

It prints `locked <data>: run the dreaming workflow` and exits 0; `held by a dreaming workflow running on <data>` and
exits 1 when another session dreams on this data now, its lock younger than homework/lib/stamp.py's LOCK_HOURS; or
`failed to lock <data>` and exits 3 when <data> cannot hold the lock, as when it is a file or read-only.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import stamp  # noqa: E402


def main(args):
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        taken = stamp.lock(args[0])
    except OSError as e:
        print(f"failed to lock {args[0]}: {e}; run none")
        return 3
    if taken:
        print(f"locked {args[0]}: run the dreaming workflow")
        return 0
    print(f"held by a dreaming workflow running on {args[0]} (its dream.lock is under {stamp.LOCK_HOURS} hours old): run none")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
