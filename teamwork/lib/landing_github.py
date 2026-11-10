"""Merged pull requests, read only by `gh pr list`, for a repository that lands by pull request. A repository whose `origin` is not on GitHub and that sets no `GH_REPO`
gets none, and a failed read gets none either. Only a merge whose branch this repository still holds at the merged head counts, since the history of an old pull request would
otherwise match a worker that reuses its branch name, and a branch that is gone has nothing left to clean."""
import json
import os
import re
import subprocess

import landing_git

HOST = re.compile(r"github\.com[:/]")
LIMIT = 100
FIELDS = "number,headRefName,headRefOid,mergedAt,updatedAt"


def gh(*argv):
    """The JSON `gh pr list ARGV` printed; None when the repository is not a GitHub one, or the read failed or ran past 15 s."""
    origin = landing_git.git("remote", "get-url", "origin").stdout
    if not (os.environ.get("GH_REPO") or HOST.search(origin)):
        return None
    try:
        result = subprocess.run(["gh", "pr", "list", *argv, "--json", FIELDS], capture_output=True, text=True, timeout=15)
        return json.loads(result.stdout) if not result.returncode else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def merged(limit=None, branch=None):
    """The merged pull requests as `number`, `headRefName`, `headRefOid`, `mergedAt`, newest merge first, BRANCH cutting it to one head; empty when none was read."""
    # GitHub lists by creation, so a pull request opened long ago and merged now would fall off a short page without the search
    found = gh("--state", "merged", "--search", "sort:updated-desc", "--limit", str(limit or LIMIT), *(["--head", branch] if branch else []))
    held = set(landing_git.git("for-each-ref", "--format=%(refname:lstrip=2) %(objectname)", "refs/heads", "refs/remotes/origin").stdout.splitlines())
    held |= {line.split(" ", 1)[0].removeprefix("origin/") + " " + line.split(" ", 1)[1] for line in held}  # an `origin/` ref is held under its branch name too
    return [{key: pull[key] for key in ("number", "headRefName", "headRefOid", "mergedAt")} for pull in found or [] if f"{pull['headRefName']} {pull['headRefOid']}" in held]


def changed_since(stamp):
    """Whether any pull request was merged since STAMP (an ISO time); an open one that moved is no news to the heartbeat."""
    found = gh("--state", "merged", "--limit", "1", "--search", "sort:updated-desc")
    return bool(found) and found[0]["mergedAt"] >= stamp
