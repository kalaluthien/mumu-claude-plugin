"""Changes in local git: each is a record `<n>.json` in the main checkout's `.teamwork/changes`, the same for every worktree and never committed,
holding its title, body, branch and base, and once merged the head it took. A merge squashes that head onto the base as one commit, as GitHub's does."""
import json
import os
import re
import subprocess
from datetime import datetime, timezone

import data_folder
import team_signal

CLOSES = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)", re.I)


def git(*argv, cwd=None, stdin=None):
    return subprocess.run(["git", *argv], cwd=cwd, input=stdin, capture_output=True, text=True)


def folder():
    """The changes folder of the repository holding the current folder; None outside one."""
    return data_folder.folder("changes")


def stamp(seconds=None):
    return datetime.fromtimestamp(seconds or datetime.now().timestamp(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def records():
    d = folder()
    return None if d is None else [json.loads(p.read_text()) for p in d.glob("[0-9]*.json")]


def record(number):
    try:
        return json.loads((folder() / f"{int(number)}.json").read_text())
    except (TypeError, OSError, ValueError) as e:
        raise LookupError(f"no change {number} in this repository") from e


def save(r, new=False):
    """Writes R whole, then touches the signal file, which the issue pane and the heartbeat wait on; NEW claims its number, raising FileExistsError
    when another session took it first."""
    path = folder() / f"{r['number']}.json"
    # written aside, then put in place in one step, so a reader never meets half a record
    draft = path.with_name(f".{r['number']}.{os.getpid()}.draft")
    draft.write_text(json.dumps({**r, "updatedAt": stamp()}))
    try:
        os.link(draft, path) if new else os.replace(draft, path)
    finally:
        draft.unlink(missing_ok=True)
    team_signal.SIGNAL.parent.mkdir(parents=True, exist_ok=True)
    team_signal.SIGNAL.touch()


def tip(ref):
    return git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").stdout.strip() or None


def pulls(state="open", repo=None, limit=None, branch=None):
    """Changes as `number`, `headRefName`, `headRefOid`, `mergedAt`, newest update first; an open one's head is its branch tip now. None outside a repository."""
    found = records()
    if found is None:
        return None
    keep = sorted((r for r in found if state in ("all", r["state"].lower()) and branch in (None, r["headRefName"])),
                  key=lambda r: (r["updatedAt"], r["number"]), reverse=True)
    return [{"number": r["number"], "headRefName": r["headRefName"], "headRefOid": r.get("headRefOid") or tip(f"refs/heads/{r['headRefName']}"),
             "mergedAt": r.get("mergedAt")} for r in keep[:limit]]


def conflicts(number, repo=None):
    """Whether the change cannot merge cleanly into its base now; None when its branch or base is gone."""
    r = record(number)
    head, base = tip(f"refs/heads/{r['headRefName']}"), tip(f"refs/heads/{r['base']}")
    if not head or not base:
        return None
    return {0: False, 1: True}.get(git("merge-tree", "--write-tree", "--quiet", base, head).returncode)


def first_commit(number, repo=None):
    """When the change's first commit off its base was authored; None when it has none. It raises LookupError when the read failed."""
    r = record(number)
    head = r.get("headRefOid") or f"refs/heads/{r['headRefName']}"
    p = git("log", "--reverse", "--format=%at", f"{r.get('baseOid') or 'refs/heads/' + r['base']}..{head}")
    if p.returncode:
        raise LookupError(f"the commits of change {number} could not be read: {p.stderr.strip()}")
    return p.stdout.split() and stamp(int(p.stdout.split()[0])) or None


def changed_since(stamp):
    """Whether any change was filed or merged since STAMP (an ISO time)."""
    return any(r["updatedAt"] >= stamp for r in records() or [])


def worktree_of(branch):
    """The worktree that has BRANCH checked out, or None."""
    path = None
    for line in git("worktree", "list", "--porcelain").stdout.splitlines():
        if line.startswith("worktree "):
            path = line.split(" ", 1)[1]
        elif line == f"branch refs/heads/{branch}":
            return path
    return None


def change(branch, title, body, base):
    """Files BRANCH as a change into BASE; its url."""
    for name in (branch, base):
        if not tip(f"refs/heads/{name}"):
            raise LookupError(f"no branch {name} in this repository")
    d = folder()
    d.mkdir(parents=True, exist_ok=True)
    number = max((r["number"] for r in records()), default=0) + 1
    while True:  # two workers filing at once take the next free number each, never one record
        try:
            save({"number": number, "title": title, "body": body, "headRefName": branch, "base": base, "state": "OPEN", "createdAt": stamp()}, new=True)
            return f"file://{d}/{number}.json"
        except FileExistsError:
            number += 1


def merge(number, sha):
    """Squashes the change's head onto its base as one commit, only when SHA is its branch tip, and fast-forwards the worktree that has the base
    checked out, which refuses rather than overwrites; the new commit's sha."""
    r = record(number)
    if r["state"] != "OPEN":
        raise LookupError(f"change {number} is closed")
    head, base = tip(f"refs/heads/{r['headRefName']}"), tip(f"refs/heads/{r['base']}")
    # only a sha names what the judge approved; a branch name would follow the tip wherever it moved
    if not head or not re.fullmatch(r"[0-9a-f]{7,40}", sha) or tip(sha) != head:
        raise LookupError(f"change {number}: {sha} is not the tip of {r['headRefName']} ({head and head[:9]}); judge the tip again")
    tree = git("merge-tree", "--write-tree", base, head)
    if tree.returncode:
        raise LookupError(f"change {number} conflicts with {r['base']}; rebase it")
    made = git("commit-tree", tree.stdout.split()[0], "-p", base, "-F", "-", stdin=f"{r['title']} (change {number})\n\n{r['body']}")
    if made.returncode:
        raise LookupError(f"change {number}: no commit made: {made.stderr.strip()}")
    commit, holder = made.stdout.strip(), worktree_of(r["base"])
    # the worktree that has the base checked out moves with it, so its files never fall behind the branch
    p = git("merge", "--ff-only", "--quiet", commit, cwd=holder) if holder else git("update-ref", f"refs/heads/{r['base']}", commit, base)
    if p.returncode:
        raise LookupError(f"change {number}: {holder or r['base']} did not take the merge: {p.stderr.strip()}")
    save({**r, "state": "CLOSED", "headRefOid": head, "baseOid": base, "mergeOid": commit, "mergedAt": stamp()})
    return commit
