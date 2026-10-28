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
    directory = folder()
    return None if directory is None else [json.loads(path.read_text()) for path in directory.glob("[0-9]*.json")]


def record(number):
    try:
        return json.loads((folder() / f"{int(number)}.json").read_text())
    except (TypeError, OSError, ValueError) as e:
        raise LookupError(f"no change {number} in this repository") from e


def save(entry, new=False):
    """Writes R whole, then touches the signal file, which the issue pane and the heartbeat wait on; NEW claims its number, raising FileExistsError
    when another session took it first."""
    path = folder() / f"{entry['number']}.json"
    # written aside, then put in place in one step, so a reader never meets half a record
    draft = path.with_name(f".{entry['number']}.{os.getpid()}.draft")
    draft.write_text(json.dumps({**entry, "updatedAt": stamp()}))
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
    keep = sorted((entry for entry in found if state in ("all", entry["state"].lower()) and branch in (None, entry["headRefName"])),
                  key=lambda entry: (entry["updatedAt"], entry["number"]), reverse=True)
    return [{"number": entry["number"], "headRefName": entry["headRefName"], "headRefOid": entry.get("headRefOid") or tip(f"refs/heads/{entry['headRefName']}"),
             "mergedAt": entry.get("mergedAt")} for entry in keep[:limit]]


def conflicts(number, repo=None):
    """Whether the change cannot merge cleanly into its base now; None when its branch or base is gone."""
    entry = record(number)
    head, base = tip(f"refs/heads/{entry['headRefName']}"), tip(f"refs/heads/{entry['base']}")
    if not head or not base:
        return None
    return {0: False, 1: True}.get(git("merge-tree", "--write-tree", "--quiet", base, head).returncode)


def first_commit(number, repo=None):
    """When the change's first commit off its base was authored; None when it has none. It raises LookupError when the read failed."""
    entry = record(number)
    head = entry.get("headRefOid") or f"refs/heads/{entry['headRefName']}"
    result = git("log", "--reverse", "--format=%at", f"{entry.get('baseOid') or 'refs/heads/' + entry['base']}..{head}")
    if result.returncode:
        raise LookupError(f"the commits of change {number} could not be read: {result.stderr.strip()}")
    return result.stdout.split() and stamp(int(result.stdout.split()[0])) or None


def changed_since(stamp):
    """Whether any change was filed or merged since STAMP (an ISO time)."""
    return any(entry["updatedAt"] >= stamp for entry in records() or [])


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
    directory = folder()
    directory.mkdir(parents=True, exist_ok=True)
    number = max((entry["number"] for entry in records()), default=0) + 1
    while True:  # two workers filing at once take the next free number each, never one record
        try:
            save({"number": number, "title": title, "body": body, "headRefName": branch, "base": base, "state": "OPEN", "createdAt": stamp()}, new=True)
            return f"file://{directory}/{number}.json"
        except FileExistsError:
            number += 1


def merge(number, sha):
    """Squashes the change's head onto its base as one commit, only when SHA is its branch tip, and fast-forwards the worktree that has the base
    checked out, which refuses rather than overwrites; the new commit's sha."""
    entry = record(number)
    if entry["state"] != "OPEN":
        raise LookupError(f"change {number} is closed")
    head, base = tip(f"refs/heads/{entry['headRefName']}"), tip(f"refs/heads/{entry['base']}")
    # only a sha names what the judge approved; a branch name would follow the tip wherever it moved
    if not head or not re.fullmatch(r"[0-9a-f]{7,40}", sha) or tip(sha) != head:
        raise LookupError(f"change {number}: {sha} is not the tip of {entry['headRefName']} ({head and head[:9]}); judge the tip again")
    tree = git("merge-tree", "--write-tree", base, head)
    if tree.returncode:
        raise LookupError(f"change {number} conflicts with {entry['base']}; rebase it")
    made = git("commit-tree", tree.stdout.split()[0], "-p", base, "-F", "-", stdin=f"{entry['title']} (change {number})\n\n{entry['body']}")
    if made.returncode:
        raise LookupError(f"change {number}: no commit made: {made.stderr.strip()}")
    commit, holder = made.stdout.strip(), worktree_of(entry["base"])
    # the worktree that has the base checked out moves with it, so its files never fall behind the branch
    result = git("merge", "--ff-only", "--quiet", commit, cwd=holder) if holder else git("update-ref", f"refs/heads/{entry['base']}", commit, base)
    if result.returncode:
        raise LookupError(f"change {number}: {holder or entry['base']} did not take the merge: {result.stderr.strip()}")
    save({**entry, "state": "CLOSED", "headRefOid": head, "baseOid": base, "mergeOid": commit, "mergedAt": stamp()})
    return commit
