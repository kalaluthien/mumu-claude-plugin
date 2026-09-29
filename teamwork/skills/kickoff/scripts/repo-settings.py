#!/usr/bin/env python3
"""Apply the safe standard GitHub settings to the repository of a checkout, changing only what differs.

usage: repo-settings.py <checkout>

- squash is the only merge method, as `pr-merge.py` merges;
- a merged head branch is deleted.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import sessions  # noqa: E402
import gh  # noqa: E402

REPO = {"allow_squash_merge": True, "allow_merge_commit": False, "allow_rebase_merge": False, "delete_branch_on_merge": True}
# No default-branch rulesets step: GitHub answers it 403 on a free plan's private repository.


def differs(want, have):
    """Whether any key of `want` has another value in `have`, a dict compared by its keys and a list by its items."""
    if isinstance(want, dict):
        return not isinstance(have, dict) or any(differs(v, have.get(k)) for k, v in want.items())
    if isinstance(want, list):
        return not isinstance(have, list) or len(want) != len(have) or any(differs(w, h) for w, h in zip(want, have))
    return want != have


def api(cwd, *argv, body=None):
    out = gh.gh("api", *argv, *(["--input", "-"] if body is not None else []), cwd=cwd, stdin=json.dumps(body) if body is not None else None)
    return json.loads(out) if out.strip() else None


def apply(cwd):
    """Set `REPO` on `cwd`'s repository where it differs; the list of what changed."""
    if not differs(REPO, api(cwd, "repos/{owner}/{repo}")):
        return []
    api(cwd, "-X", "PATCH", "repos/{owner}/{repo}", body=REPO)
    return ["repository"]


def main(argv):
    if len(argv) != 1:
        sys.exit("usage: repo-settings.py <checkout>")
    try:
        changed = apply(str(sessions.checkout(argv[0])))
    except (RuntimeError, ValueError, KeyError, TypeError) as e:
        sys.exit(f"repo-settings.py: {e}")
    print("changed: " + ", ".join(changed) if changed else "unchanged")


if __name__ == "__main__":
    main(sys.argv[1:])
