#!/usr/bin/env python3
"""Print the name of the lead of the checkout in cwd: `<folder>-lead` when the task given carries `scope:<folder>` and the
checkout has that folder, else `<repo>-lead`.

usage: lead-name.py [<task-url>]
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import names  # noqa: E402
import github  # noqa: E402
from github import repo as repo_view  # noqa: E402


def main(argv):
    if len(argv) > 1:
        sys.exit("usage: lead-name.py [<task-url>]")
    try:
        scopes = [label["name"].removeprefix("scope:") for label in
                  json.loads(github.gh("issue", "view", argv[0], "--json", "labels"))["labels"]
                  if label["name"].startswith("scope:")] if argv else []
        folders = [f for f in scopes if pathlib.Path(f).is_dir()]
        print(f"{folders[0]}-lead" if len(folders) == 1 else names.lead(repo_view("name")))
    except (RuntimeError, ValueError, KeyError, TypeError) as e:
        sys.exit(f"lead-name.py: {e}")


if __name__ == "__main__":
    main(sys.argv[1:])
