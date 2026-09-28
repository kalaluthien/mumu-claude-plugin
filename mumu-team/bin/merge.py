#!/usr/bin/env python3
"""Squash-merge a pull request whose newest verdict is `APPROVED: <head>`, or `APPROVED: <A>` carried to the head across merges
of the default branch that leave its own diff byte-identical: the only merge path."""
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import github  # noqa: E402

URL = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+")
APPROVAL = re.compile(r"approved:?\s+(\S+)", re.I)
FINDINGS = re.compile(r"findings\b:?.*", re.I)
REF = r"(?:([\w.-]+/[\w.-]+)?#(\d+)|https://github\.com/([\w.-]+/[\w.-]+)/issues/(\d+))"
CLOSING = re.compile(rf"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+{REF}", re.I)
PART = re.compile(rf"\bpart of:?\s+{REF}", re.I)
SHARES = re.compile(r"^## Shares\s*$", re.M)


def approval(pr):
    """(the sha an `APPROVED:` since the newest `FINDINGS:` names: the head when one names it, else the newest's, else None;
    the sha the newest `APPROVED:` names when a `FINDINGS:` is newer, else None), comments and reviews read oldest first."""
    notes = [(n.get("createdAt") or n.get("submittedAt") or "", n["body"]) for n in (pr.get("comments") or []) + (pr.get("reviews") or [])]
    shas, stale = [], None
    for _, body in sorted(notes, key=lambda n: n[0]):
        line = body.strip().splitlines()[0].strip() if body.strip() else ""
        if FINDINGS.fullmatch(line):
            shas, stale = [], (shas[-1] if shas else stale)
        elif m := APPROVAL.fullmatch(line):
            shas.append(m[1].lower())
    return (pr["headRefOid"] if pr["headRefOid"] in shas else shas[-1] if shas else None), stale


def git(*argv, stdin=None):
    """stdout of `git <argv>` in the checkout merge.py runs from."""
    return github.run("git", *argv, stdin=stdin)


def ancestor(sha, of):
    """Whether `sha` is an ancestor of `of`, raising when git cannot tell."""
    done = subprocess.run(["git", "merge-base", "--is-ancestor", sha, of], capture_output=True, text=True)
    if done.returncode > 1:
        raise RuntimeError(f"git merge-base --is-ancestor {sha} {of}: {done.stderr.strip()}")
    return done.returncode == 0


def patch_id(sha, base):
    """`git patch-id --verbatim` of the diff from `sha`'s merge base with `base` to `sha`, or None when that diff is empty."""
    diff = git("diff", "--no-color", "--no-ext-diff", "--binary", git("merge-base", sha, base).strip(), sha)
    return git("patch-id", "--verbatim", stdin=diff).split()[0] if diff else None


def uncarried(approved, head, base):
    """Why the approval of `approved` does not carry to `head`, or None when it does: `approved` is an ancestor of `head`, each
    commit on the first-parent path between them is a merge whose other parent is on `base`, and the diff from the merge base
    with `base` is the same non-empty patch at both."""
    try:
        if not ancestor(approved, head):
            return "it is not an ancestor of the head"
        for commit in git("rev-list", "--first-parent", f"{approved}..{head}").split():
            parents = git("rev-list", "--parents", "-n1", commit).split()[1:]
            if len(parents) != 2 or not ancestor(parents[1], base):
                return f"{commit} is not a merge of {base}"
        before, after = patch_id(approved, base), patch_id(head, base)
    except (RuntimeError, IndexError) as e:
        return f"its diff cannot be read: {e}"
    if not before or not after:
        return "its diff is empty"
    return None if before == after else f"its patch-id moved from {before} to {after}"


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
        if SHARES.search(json.loads(github.gh("issue", "view", url, "--json", "body"))["body"] or ""):
            return url
    return None


def paths(compare):
    """Each path a compare response's diff from the merge base changes, a rename's old path included."""
    return {p for f in compare.get("files") or [] for p in (f["filename"], f.get("previous_filename")) if p}


def main(args):
    if len(args) != 1 or not URL.fullmatch(args[0]):
        sys.exit("usage: merge.py <pr-url>, the PR's full https://github.com/<owner>/<repo>/pull/<n> url")
    url = args[0]
    try:
        pr = json.loads(github.gh("pr", "view", url, "--json", "headRefOid,comments,reviews,title,body,commits,baseRefName"))
    except RuntimeError as e:
        sys.exit(f"merge.py: could not read {url}: {e}")
    head, repo = pr["headRefOid"], "/".join(url.split("/")[3:5])
    approved, stale = approval(pr)
    if not approved:
        after = f"; `APPROVED: {stale}` is older than a `FINDINGS:`" if stale else ""
        sys.exit(f"merge.py: no comment or review opens with `APPROVED: {head}` since the newest `FINDINGS:`{after}; launch the judge at this head")
    if approved != head and (why := uncarried(approved, head, f"origin/{pr['baseRefName']}")):
        sys.exit(f"merge.py: `APPROVED: {approved}` does not carry to the head {head}: {why}; resume the judge at this head")
    if not (CLOSING.search(pr.get("body") or "") or PART.search(pr.get("body") or "")):
        sys.exit("merge.py: the body names no task: open it with `Closes #<task>`, or a share's `Part of #<task>`, over the criteria table")
    try:
        ahead = json.loads(github.gh("api", f"repos/{repo}/compare/{pr['baseRefName']}...{head}"))
        behind, task = int(ahead["behind_by"]), shared(pr, repo)
        both = sorted(paths(ahead) & paths(json.loads(github.gh("api", f"repos/{repo}/compare/{head}...{pr['baseRefName']}")))) if behind else []
    except (RuntimeError, ValueError, KeyError, TypeError) as e:
        sys.exit(f"merge.py: could not read {url}'s base or task: {e}")
    if behind and both:
        sys.exit(f"merge.py: the head lacks {behind} commit(s) of {pr['baseRefName']}, which change paths it changes too: {', '.join(both)}; "
                 "merge it in, rerun every check on the merged tree, push and run merge.py again")
    if behind:
        sys.exit(f"merge.py: the head lacks {behind} commit(s) of {pr['baseRefName']}, which change no path it changes; "
                 "merge it in, push and run merge.py again; no rerun needed")
    if task and any(CLOSING.search(t) for t in texts(pr)):
        sys.exit(f"merge.py: {task} has `## Shares`, so only its lead closes it; drop each closing keyword from the title, body and commits, and write `Part of #<n>`")
    try:
        print(github.gh("pr", "merge", url, "--squash", "--match-head-commit", head), end="")
    except RuntimeError as e:
        sys.exit(f"merge.py: {e}")


if __name__ == "__main__":
    main(sys.argv[1:])
