#!/usr/bin/env python3
"""Carry a view.json written for the engine before the Schema over to the zoom engine.

usage: migrate-view.py old-view.json|-     print the view for the zoom engine

The view's keys name levels, nodes, edges and screens by id, and the Schema migration keeps every id, so a view
carries over unchanged; only its layout is rewritten the way the engine writes a view. Exit status 0, or 2 on a
usage error.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[6] / "lib"))

from schema.model import dump  # noqa: E402


def main(args):
    if len(args) != 1 or args[0].startswith("--"):
        print(__doc__, file=sys.stderr)
        return 2
    old = json.load(sys.stdin if args[0] == "-" else open(args[0], encoding="utf-8"))
    print(dump(old))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
