"""Changes in local git: each is a record `<n>.json` in the main checkout's `.teamwork/changes`, the same for every worktree and never committed,
holding its title, body, branch and base, and once merged the head it took. A merge squashes that head onto the base as one commit, and with an `origin`
pushes it there as a fast-forward of the base before it moves anything here, so a refused push leaves the change open and the base as it was.
A repository that tracks `.github/plan-release.py` also releases at the merge: the merge asks that script, taken from the merge commit, for the tags to
push, and a refusal by it refuses the merge."""
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile

import board_writers
import data_folder
import iso_time
import team_signal

RELEASE_HOOK = ".github/plan-release.py"


def git(*argv, cwd=None, stdin=None):
    return subprocess.run(["git", *argv], cwd=cwd, input=stdin, capture_output=True, text=True)


def folder():
    """The changes folder of the repository holding the current folder; None outside one."""
    return data_folder.folder("changes")


def records():
    directory = folder()
    return None if directory is None else [json.loads(path.read_text()) for path in directory.glob("[0-9]*.json")]


def record(number):
    try:
        return json.loads((folder() / f"{int(number)}.json").read_text())
    except (TypeError, OSError, ValueError) as e:
        raise LookupError(f"no change {number} in this repository") from e


def save(entry, new=False):
    """Writes ENTRY whole, then touches the signal file, which the task pane and the heartbeat wait on; NEW claims its number, raising FileExistsError
    when another session took it first."""
    path = folder() / f"{entry['number']}.json"
    # written aside, then put in place in one step, so a reader never meets half a record
    draft = path.with_name(f".{entry['number']}.{os.getpid()}.draft")
    draft.write_text(json.dumps({**entry, "updatedAt": iso_time.stamp()}))
    try:
        os.link(draft, path) if new else os.replace(draft, path)
    finally:
        draft.unlink(missing_ok=True)
    team_signal.touch()


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


def bare_flagged():
    """Whether `core.bare` is true on a repository that has a main checkout (its common folder is a `.git`), where git then lists that checkout as bare."""
    common = data_folder.common_folder()
    return bool(common) and common.name == ".git" and git("config", "--bool", "core.bare").stdout.strip() == "true"


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
            save({"number": number, "title": title, "body": body, "headRefName": branch, "base": base, "state": "OPEN", "createdAt": iso_time.stamp()}, new=True)
            return f"file://{directory}/{number}.json"
        except FileExistsError:
            number += 1


def close(number, reason, writer):
    """Closes the open change NUMBER unmerged, its REASON kept, when `board_writers` lets WRITER close it; its url. LookupError, nothing changed, naming why not."""
    entry = record(number)
    if entry["state"] != "OPEN":
        raise LookupError(f"change {number} is closed")
    refusals = board_writers.check("close", number, entry, writer) + ([] if reason.strip() else ["a close names its reason"])
    if refusals:
        raise LookupError(f"change {number} stays open: " + "; ".join(refusals))
    save({**entry, "state": "CLOSED", "headRefOid": tip(f"refs/heads/{entry['headRefName']}"), "reason": reason.strip(), "closedAt": iso_time.stamp()})
    return f"file://{folder()}/{entry['number']}.json"


def clobbered(holder, base, commit):
    """The files of HOLDER's worktree that hold uncommitted changes and that the move from BASE to COMMIT would also change, so the move can be refused before anything is pushed."""
    # NUL-separated, since a path with a space is quoted by the line form and split by whitespace; a renamed file lists its new path, then its old one
    fields = iter(git("status", "--porcelain", "-z", "--untracked-files=all", cwd=holder).stdout.split("\0"))
    dirty = set()
    for field in fields:
        if field:
            dirty.add(field[3:])
            if field[0] in "RC":
                dirty.add(next(fields, ""))
    return sorted(dirty & set(git("diff", "--name-only", "-z", base, commit, cwd=holder).stdout.split("\0")))


def release_tags(number, base, commit):
    """The tags the repository's release hook asks for when COMMIT lands on BASE; none when the repository tracks no hook. Raises LookupError with the hook's reason when it refuses."""
    source = git("show", f"{commit}:{RELEASE_HOOK}")
    if source.returncode:
        return []
    with tempfile.TemporaryDirectory() as folder:
        script = pathlib.Path(folder, "plan-release.py")
        script.write_text(source.stdout)
        planned = subprocess.run([sys.executable, "-I", str(script), base, commit], capture_output=True, text=True)
    if planned.returncode:
        raise LookupError(f"change {number}: the release hook refused, so nothing was merged: {planned.stderr.strip() or planned.stdout.strip()}")
    return planned.stdout.split()


def push(number, base_name, commit, tags=()):
    """Pushes COMMIT to `origin` as the new tip of BASE_NAME, a fast-forward only, and each of TAGS with it in one atomic push; whether it pushed, since a
    repository with no `origin` pushes nothing. Raises LookupError with the remote's reason when it refuses."""
    if git("remote", "get-url", "origin").returncode:
        return False
    result = git("push", "--atomic", "--porcelain", "origin", f"{commit}:refs/heads/{base_name}", *(f"refs/tags/{tag}" for tag in tags))
    if result.returncode:
        reason = (result.stderr.strip() or result.stdout.strip()).splitlines()
        raise LookupError(f"change {number}: origin refused the push of {base_name}, so nothing was merged: {' | '.join(reason[-4:])}")
    return True


def change_text(base, ref):
    """REF's diff from where it left BASE, whitespace kept, without the line numbers and blob ids a rebase alone changes; None for no diff."""
    fork = git("merge-base", base, ref).stdout.strip()
    diff = git("diff", "--no-color", "--no-ext-diff", fork, ref).stdout if fork else ""
    return "".join(re.sub(r"^@@ [^@]* @@", "@@", line) for line in diff.splitlines(keepends=True) if not line.startswith("index ")) or None


def same_diff(base, approved, head):
    """Whether APPROVED and HEAD make the same change, so a rebase that moved only the base keeps the judge's verdict."""
    return bool(approved) and change_text(base, approved) is not None and change_text(base, approved) == change_text(base, head)


def conflict_markers(base, head):
    """The `<file>:<line>` of each line HEAD adds since it left BASE that is a leftover merge conflict marker, as `git diff --check` finds them, but not a bare `=======`, which a Markdown heading underline also is
    and which a real conflict never holds without its `<<<<<<<` or `>>>>>>>` line."""
    fork = git("merge-base", base, head).stdout.strip()
    found = git("diff", "--check", "--no-color", "--no-ext-diff", fork, head).stdout if fork else ""
    places = [line.rsplit(":", 1)[0] for line in found.splitlines() if line.endswith(": leftover conflict marker")]
    return [place for place in places if git("show", f"{head}:{place.rsplit(':', 1)[0]}").stdout.splitlines()[int(place.rsplit(":", 1)[1]) - 1].rstrip() != "======="]


def merge(number, sha):
    """Squashes the change's head onto its base as one commit, only when SHA is its branch tip or a commit whose diff a rebase left the same, tags it as the repository's release hook asks, pushes both to
    `origin` when there is one, and fast-forwards the worktree that has the base checked out, which refuses rather than overwrites; the new commit's sha.
    The change is merged once `origin` holds the commit, or with no `origin` once the base moved; until then a failure leaves no tag behind."""
    entry = record(number)
    if entry["state"] != "OPEN":
        raise LookupError(f"change {number} is closed")
    head, base = tip(f"refs/heads/{entry['headRefName']}"), tip(f"refs/heads/{entry['base']}")
    # only a sha names what the judge approved; a branch name would follow the tip wherever it moved
    if not head or not re.fullmatch(r"[0-9a-f]{7,40}", sha) or tip(sha) != head and not same_diff(base, tip(sha), head):
        raise LookupError(f"change {number}: {sha} is not the tip of {entry['headRefName']} ({head and head[:9]}), and its diff is not the tip's; judge the tip again")
    if markers := conflict_markers(base, head):
        raise LookupError(f"change {number} adds a leftover merge conflict marker at {', '.join(markers[:5])}; resolve it and judge the tip again")
    # git then lists the main checkout as bare, so no worktree holds the base and a ref move would leave its files behind
    if bare_flagged():
        raise LookupError(f"change {number}: core.bare is true, so the checkout of {entry['base']} would stay behind the merge; run `git config core.bare false`")
    tree = git("merge-tree", "--write-tree", base, head)
    if tree.returncode:
        raise LookupError(f"change {number} conflicts with {entry['base']}; rebase it")
    made = git("commit-tree", tree.stdout.split()[0], "-p", base, "-F", "-", stdin=f"{entry['title']} (change {number})\n\n{entry['body']}")
    if made.returncode:
        raise LookupError(f"change {number}: no commit made: {made.stderr.strip()}")
    commit, holder = made.stdout.strip(), worktree_of(entry["base"])
    if holder and (files := clobbered(holder, base, commit)):
        raise LookupError(f"change {number}: {holder} holds uncommitted changes to {', '.join(files[:5])}, which the merge would overwrite; commit or move them")
    tags, tagged = release_tags(number, base, commit), []
    closed = {**entry, "state": "CLOSED", "headRefOid": head, "baseOid": base, "mergeOid": commit, "tags": tags, "mergedAt": iso_time.stamp()}
    try:
        for tag in tags:
            result = git("tag", tag, commit)
            if result.returncode:
                raise LookupError(f"change {number}: tag {tag} was not made, so nothing was merged: {result.stderr.strip()}")
            tagged.append(tag)
        pushed = push(number, entry["base"], commit, tags)
        # the worktree that has the base checked out moves with it, so its files never fall behind the branch
        result = git("merge", "--ff-only", "--quiet", commit, cwd=holder) if holder else git("update-ref", f"refs/heads/{entry['base']}", commit, base)
        if result.returncode and not pushed:
            raise LookupError(f"change {number}: {holder or entry['base']} did not take the merge, so nothing was merged: {result.stderr.strip()}")
    except LookupError:
        for tag in tagged:  # a tag stays only with the merge it names
            git("tag", "-d", tag)
        raise
    save(closed)
    if result.returncode:
        # a pull --rebase replays the base's own commits on origin's tip; with no worktree on the base, a worktree made for it moves no other branch
        name = shlex.quote(entry["base"])
        if holder:
            catch_up = f"git -C {shlex.quote(str(holder))} pull --rebase origin {name}"
        else:
            spare = shlex.quote(str(folder() / f"catch-up-{number}"))
            catch_up = (f"git -C {shlex.quote(str(folder()))} worktree add {spare} {name} && git -C {spare} pull --rebase origin {name} "
                        f"&& git -C {shlex.quote(str(folder()))} worktree remove {spare}")
        raise LookupError(f"change {number}: merged on origin as {commit[:9]}, but {holder or entry['base']} did not take it: {result.stderr.strip()}; "
                          f"bring it up to origin by `{catch_up}`")
    return commit
