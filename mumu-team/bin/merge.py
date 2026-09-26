#!/usr/bin/env python3
"""Squash-merge a pull request at a head some comment or review opens `APPROVED: <head>` on: the only merge path."""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
from gh import gh  # noqa: E402

URL = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+")
APPROVAL = re.compile(r"approved:?\s+(\S+)", re.I)
REF = r"(?:([\w.-]+/[\w.-]+)?#(\d+)|https://github\.com/([\w.-]+/[\w.-]+)/issues/(\d+))"
CLOSING = re.compile(rf"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+{REF}", re.I)
PART = re.compile(rf"\bpart of:?\s+{REF}", re.I)
SHARES = re.compile(r"^## Shares\s*$", re.M)


def approved(pr):
    """Whether a comment or review of the PR opens with an approval of its head."""
    notes = (pr.get("comments") or []) + (pr.get("reviews") or [])
    first_lines = [n["body"].strip().splitlines()[0].strip() for n in notes if n["body"].strip()]
    return any((m := APPROVAL.fullmatch(line)) and m[1].lower() == pr["headRefOid"] for line in first_lines)


def texts(pr):
    """The PR's title, body and each commit message: the words GitHub reads closing keywords from."""
    return [pr.get("title") or "", pr.get("body") or ""] + [
        f"{c.get('messageHeadline') or ''}\n{c.get('messageBody') or ''}" for c in pr.get("commits") or []]


def issues(pattern, text, repo):
    """The url of each issue `pattern` names in `text`, a bare `#n` read as one of `repo`'s."""
    return [f"https://github.com/{m[1] or m[3] or repo}/issues/{m[2] or m[4]}" for m in pattern.finditer(text)]


def shared(pr, repo):
    """The first issue the PR closes or is part of whose body has `## Shares`, else None."""
    for url in dict.fromkeys(u for t in texts(pr) for pattern in (CLOSING, PART) for u in issues(pattern, t, repo)):
        if SHARES.search(json.loads(gh("issue", "view", url, "--json", "body"))["body"] or ""):
            return url
    return None


def main(args):
    if len(args) != 1 or not URL.fullmatch(args[0]):
        sys.exit("usage: merge.py <pr-url>, the PR's full https://github.com/<owner>/<repo>/pull/<n> url")
    url = args[0]
    try:
        pr = json.loads(gh("pr", "view", url, "--json", "headRefOid,comments,reviews,title,body,commits,baseRefName"))
    except RuntimeError as e:
        sys.exit(f"merge.py: could not read {url}: {e}")
    head, repo = pr["headRefOid"], "/".join(url.split("/")[3:5])
    if not approved(pr):
        sys.exit(f"merge.py: no comment or review opens with `APPROVED: {head}`; launch the reviewer at this head")
    try:
        behind = int(gh("api", f"repos/{repo}/compare/{pr['baseRefName']}...{head}", "-q", ".behind_by"))
        task = shared(pr, repo)
    except (RuntimeError, ValueError, KeyError, TypeError) as e:
        sys.exit(f"merge.py: could not read {url}'s base or task: {e}")
    if behind:
        sys.exit(f"merge.py: the head lacks {behind} commit(s) of {pr['baseRefName']}; merge it in, rerun every criterion, push and re-review")
    if task and any(CLOSING.search(t) for t in texts(pr)):
        sys.exit(f"merge.py: {task} has `## Shares`, so only its lead closes it; drop each closing keyword from the title, body and commits, and write `Part of #<n>`")
    try:
        print(gh("pr", "merge", url, "--squash", "--match-head-commit", head), end="")
    except RuntimeError as e:
        sys.exit(f"merge.py: {e}")


if __name__ == "__main__":
    main(sys.argv[1:])
