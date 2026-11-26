#!/usr/bin/env python3
"""Land a worker's change by use-landing.py in a scratch repository whose `origin` is a bare repository beside it, with the `gh` stand-in, which logs each call and fails,
and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-local-landing.py [--case <name>]   (no argument: every one in turn)
- pushes: the merge puts the new commit on `origin`'s base, and the local base, its checkout and the change record show it
- push-refused: an `origin` that refuses the push makes the merge exit 1 with the remote's reason, and the base here, the remote's base and the change are as they were
- no-gh: change, merge and remove-worktree call no gh
- no-origin: a repository with no remote merges locally and removes the worker's worktree with no gh call, and pushes nothing
- swap-retired: a swapped-out worker's branch, the ancestor of its successor's merged branch, is removed with its worktree once the successor's change merges, and one branch is left
- owned-branches: removing a worker removes each merged `<name>-<word>` branch it owns, here and on `origin`, keeps one with unmerged commits and an `origin` one of no worker branch name and says so, and leaves a branch of another name
- rebased: a sha a judge approved still merges once a rebase onto a moved base left its diff the same, and is refused once the rebased branch changed its diff, by its text or by whitespace alone
- conflict-marker: a change whose file adds a leftover `|||||||` conflict marker line is refused with its file and line, and nothing moves, while one that adds a Markdown `=======` heading underline merges
- dirty-base: an uncommitted file of the base checkout that the change also edits, its name holding a space, refuses the merge before any push, and nothing moves
- closed: a `close` with no reason and an unknown verb print the usage, exit 2 and change nothing; another worker's `close` of a change, and its own worker's with a blank reason, exit 1 and leave it open, its own worker's closes it unmerged with its reason, trimmed, the branch's tip and the time, and a second close and a merge of it are then refused, the base as it was"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
LANDING = SCRIPTS.parent / "references" / "adapters" / "landing-git" / "scripts" / "use-landing.py"


def setup(work, remote=True):
    """A sandbox whose repository holds `a.txt` and `a b.txt`, pushed to a bare `origin` at `sandbox.origin` when REMOTE."""
    sandbox = replay_probe.Sandbox(work, commit=False)
    sandbox.origin = work / "origin.git"
    for name in ("a.txt", "a b.txt"):
        replay_probe.write_text(sandbox.repository, name, "base\n")
    sandbox.git("add", "-A")
    sandbox.git("commit", "-q", "-m", "base")
    if remote:
        sandbox.git("init", "-q", "--bare", sandbox.origin, cwd=work)
        sandbox.git("remote", "add", "origin", sandbox.origin)
        sandbox.git("push", "-q", "-u", "origin", "main")
    return sandbox


def script(sandbox, path, *argv, cwd=None, check=False, claude=None):
    """The run of the plugin script PATH, under a stand-in `claude` started with the options CLAUDE when given; a failed one raises RuntimeError when CHECK."""
    done = sandbox.python(path, *argv, cwd=cwd, claude=claude)
    if check and done.returncode:
        raise RuntimeError(f"{pathlib.Path(path).name} {' '.join(map(str, argv))}: {done.stdout}{done.stderr}")
    return done


def worker(sandbox, name="b.txt", text="work\n"):
    tree = pathlib.Path(script(sandbox, SCRIPTS / "add-worktree.py", "probe-worker", "main", check=True).stdout.strip())
    commit_in(sandbox, tree, name, text, "work")
    replay_probe.write_text(sandbox.work, "body.md", "Probe change. Closes #1.\n")
    script(sandbox, LANDING, "change", "probe-worker", "Probe change", sandbox.work / "body.md", cwd=tree, check=True)
    return tree, rev(sandbox, tree, "HEAD")


def commit_in(sandbox, tree, name, text, message):
    replay_probe.write_text(tree, name, text)
    sandbox.git("add", "-A", cwd=tree)
    sandbox.git("commit", "-q", "-m", message, cwd=tree)


def rev(sandbox, path, ref):
    return replay_probe.sh("git", "rev-parse", "--verify", "-q", ref, cwd=path, environment=sandbox.environment, check=False).stdout.strip()


def bases(sandbox):
    return rev(sandbox, sandbox.repository, "main"), rev(sandbox, sandbox.origin, "refs/heads/main")


def change_state(sandbox):
    file = sandbox.repository / ".teamwork" / "changes" / "1.json"
    return json.loads(file.read_text())["state"] if file.exists() else None


def merged(sandbox, tree, head, number="1"):
    return script(sandbox, LANDING, "merge", number, head, cwd=tree)


def case_pushes(work):
    sandbox = setup(work)
    tree, head = worker(sandbox)
    run = merged(sandbox, tree, head)
    if run.returncode:
        return replay_probe.fail(f"merge exited {run.returncode}: {run.stderr.strip()}")
    commit = run.stdout.strip()
    if bases(sandbox) != (commit, commit):
        return replay_probe.fail(f"local and origin main {bases(sandbox)}, merge printed {commit[:9]}")
    if not (sandbox.repository / "b.txt").exists() or change_state(sandbox) != "CLOSED":
        return replay_probe.fail("the checkout lacks the merged file, or the change is still open")
    return 0


def case_push_refused(work):
    sandbox = setup(work)
    replay_probe.write_text(sandbox.origin / "hooks", "pre-receive", "#!/bin/sh\necho 'no pushes today' >&2\nexit 1\n").chmod(0o755)
    tree, head = worker(sandbox)
    before = bases(sandbox)
    run = merged(sandbox, tree, head)
    if run.returncode != 1 or "no pushes today" not in run.stderr:
        return replay_probe.fail(f"merge exited {run.returncode}: {run.stdout}{run.stderr}")
    if before != bases(sandbox) or (sandbox.repository / "b.txt").exists() or change_state(sandbox) != "OPEN":
        return replay_probe.fail(f"the base here, the remote's base or the change moved: {before} -> {bases(sandbox)}, change {change_state(sandbox)}")
    return 0


def case_no_gh(work, remote=True):
    sandbox = setup(work, remote)
    tree, head = worker(sandbox)
    run = merged(sandbox, tree, head)
    if run.returncode or rev(sandbox, sandbox.repository, "main") != run.stdout.strip() or not (sandbox.repository / "b.txt").exists():
        return replay_probe.fail(f"merge exited {run.returncode}: {run.stdout}{run.stderr}")
    removed = script(sandbox, SCRIPTS / "remove-worktree.py", "probe-worker")
    if sandbox.gh_calls():
        return replay_probe.fail(f"gh was called: {sandbox.gh_calls()} (remove-worktree exit {removed.returncode}: {removed.stderr.strip()[-200:]})")
    return 0


def case_no_origin(work):
    return case_no_gh(work, remote=False)


def case_swap_retired(work):
    sandbox = setup(work)
    old, _ = worker(sandbox)
    new = pathlib.Path(script(sandbox, SCRIPTS / "add-worktree.py", "probe-opus-worker", "probe-worker", check=True).stdout.strip())
    commit_in(sandbox, new, "c.txt", "more\n", "more")
    script(sandbox, LANDING, "change", "probe-opus-worker", "Successor change", work / "body.md", cwd=new, check=True)
    run = merged(sandbox, new, rev(sandbox, new, "HEAD"), "2")
    if run.returncode:
        return replay_probe.fail(f"merge exited {run.returncode}: {run.stderr.strip()}")
    script(sandbox, SCRIPTS / "remove-worktree.py", "probe-worker", "probe-opus-worker")
    left = sandbox.git("branch", "--list", "probe-*").strip()
    if left or old.exists() or new.exists():
        return replay_probe.fail(f"branches {left!r} or worktrees left after the successor merged")
    return 0


def case_dirty_base(work):
    sandbox = setup(work)
    tree, head = worker(sandbox, name="a b.txt")
    (sandbox.repository / "a b.txt").write_text("mine, not committed\n")
    before = bases(sandbox)
    run = merged(sandbox, tree, head)
    if run.returncode != 1 or before != bases(sandbox) or change_state(sandbox) != "OPEN" or (sandbox.repository / "a b.txt").read_text() != "mine, not committed\n":
        return replay_probe.fail(f"merge exited {run.returncode}: {run.stderr.strip()[-200:]}; the bases moved {before} -> {bases(sandbox)}")
    return 0


def case_conflict_marker(work):
    sandbox = setup(work / "marker")
    tree, head = worker(sandbox, text="work\n||||||| parent of 1234567 (work)\n<<<<<<< HEAD\n")
    before = bases(sandbox)
    run = merged(sandbox, tree, head)
    if run.returncode != 1 or "b.txt:2" not in run.stderr or before != bases(sandbox) or change_state(sandbox) != "OPEN":
        return replay_probe.fail(f"merge exited {run.returncode}: {run.stderr.strip()[-200:]}; the bases moved {before} -> {bases(sandbox)}")
    sandbox = setup(work / "underline")
    tree, head = worker(sandbox, name="b.md", text="Title\n=======\ntext\n")
    run = merged(sandbox, tree, head)
    if run.returncode:
        return replay_probe.fail(f"a Markdown heading underline was refused: {run.stderr.strip()[-200:]}")
    return 0


def rebased(work, edit):
    sandbox = setup(work)
    tree, approved = worker(sandbox)
    commit_in(sandbox, sandbox.repository, "c.txt", "base moved\n", "moved")
    sandbox.git("push", "-q", "origin", "main")
    sandbox.git("rebase", "-q", "main", cwd=tree)
    if edit:
        (tree / "b.txt").write_text(edit)
        sandbox.git("commit", "-q", "-a", "--amend", "--no-edit", cwd=tree)
    return merged(sandbox, tree, approved), sandbox


def case_rebased(work):
    run, sandbox = rebased(work / "same", None)
    if run.returncode or not (sandbox.repository / "b.txt").exists() or change_state(sandbox) != "CLOSED":
        return replay_probe.fail(f"a rebase with the same diff: merge exited {run.returncode}: {run.stderr.strip()}")
    for n, edit in enumerate(("other work\n", "  work\n")):
        run, sandbox = rebased(work / str(n), edit)
        if run.returncode != 1 or "judge the tip again" not in run.stderr or change_state(sandbox) != "OPEN":
            return replay_probe.fail(f"a rebase that changed the diff to {edit!r}: merge exited {run.returncode}: {run.stdout}{run.stderr}")
    return 0


def case_owned_branches(work):
    sandbox = setup(work)
    tree, head = worker(sandbox)
    if merged(sandbox, tree, head).returncode:
        return replay_probe.fail("the worker's change did not merge")
    for branch in ("probe-worker-docs", "probe-worker-two-words", "probe-workers"):
        sandbox.git("branch", branch, "main")
        sandbox.git("push", "-q", "origin", branch)
    sandbox.git("checkout", "-q", "-b", "probe-worker-wip")
    sandbox.git("commit", "-q", "--allow-empty", "-m", "wip")
    sandbox.git("checkout", "-q", "main")
    out = script(sandbox, SCRIPTS / "remove-worktree.py", "probe-worker").stdout
    local = set(sandbox.git("branch", "--format=%(refname:short)").split())
    remote = set(sandbox.git("branch", "--format=%(refname:short)", cwd=sandbox.origin).split())
    if local != {"main", "probe-workers", "probe-worker-wip"} or remote != {"main", "probe-workers", "probe-worker-two-words"} \
            or "branch probe-worker-wip kept, unmerged commits" not in out or "origin branch probe-worker-two-words kept, not a worker branch name" not in out:
        return replay_probe.fail(f"local {sorted(local)}, origin {sorted(remote)}; printed {out.strip()}")
    return 0


def case_closed(work):
    sandbox = setup(work)
    tree, head = worker(sandbox)
    for argv in (("close", "1"), ("reopen", "1", "taken over by another task")):
        wrong = script(sandbox, LANDING, *argv, cwd=tree, claude=["--name", "probe-worker"])
        if wrong.returncode != 2 or "usage:" not in wrong.stderr or change_state(sandbox) != "OPEN":
            return replay_probe.fail(f"`{' '.join(argv)}` exited {wrong.returncode}: {wrong.stdout}{wrong.stderr}; the change is {change_state(sandbox)}")
    other = script(sandbox, LANDING, "close", "1", "taken over by another task", cwd=tree, claude=["--name", "other-worker"])
    if other.returncode != 1 or "other-worker (worker) may not write a close on change 1: only manager, worker on its own branch may" not in other.stderr or change_state(sandbox) != "OPEN":
        return replay_probe.fail(f"another worker's close exited {other.returncode}: {other.stdout}{other.stderr}; the change is {change_state(sandbox)}")
    blank = script(sandbox, LANDING, "close", "1", "  ", cwd=tree, claude=["--name", "probe-worker"])
    if blank.returncode != 1 or "a close names its reason" not in blank.stderr or change_state(sandbox) != "OPEN":
        return replay_probe.fail(f"its own worker's close with a blank reason exited {blank.returncode}: {blank.stdout}{blank.stderr}; the change is {change_state(sandbox)}")
    own = script(sandbox, LANDING, "close", "1", "  taken over by another task ", cwd=tree, claude=["--name", "probe-worker"])
    entry = json.loads((sandbox.repository / ".teamwork" / "changes" / "1.json").read_text())
    if own.returncode or entry["state"] != "CLOSED" or entry.get("mergedAt") or entry.get("reason") != "taken over by another task" \
            or entry.get("headRefOid") != sandbox.git("rev-parse", "probe-worker").strip() or not re.fullmatch(r"\d{4}-\d\d-\d\dT[\d:.]+(Z|[+-]\d\d:?\d\d)", entry.get("closedAt", "")):
        return replay_probe.fail(f"its own worker's close exited {own.returncode}: {own.stdout}{own.stderr}; the change is {entry}")
    again = script(sandbox, LANDING, "close", "1", "taken over by another task", cwd=tree, claude=["--name", "probe-worker"])
    if again.returncode != 1 or "change 1 is closed" not in again.stderr:
        return replay_probe.fail(f"a second close of the closed change exited {again.returncode}: {again.stdout}{again.stderr}")
    before = bases(sandbox)
    run = merged(sandbox, tree, head)
    if run.returncode != 1 or "change 1 is closed" not in run.stderr or bases(sandbox) != before:
        return replay_probe.fail(f"a merge of the closed change exited {run.returncode}: {run.stdout}{run.stderr}; the bases moved {before} -> {bases(sandbox)}")
    return 0


CASES = {"pushes": case_pushes, "push-refused": case_push_refused, "no-gh": case_no_gh, "no-origin": case_no_origin, "swap-retired": case_swap_retired, "rebased": case_rebased,
         "conflict-marker": case_conflict_marker, "dirty-base": case_dirty_base, "owned-branches": case_owned_branches,
         "closed": case_closed}


def main(args):
    if not args:
        return replay_probe.run_every(__file__, "--case", CASES)
    if len(args) != 2 or args[0] != "--case" or args[1] not in CASES:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("local-landing-") as work:
        try:
            if CASES[args[1]](work):
                return 1
        except RuntimeError as e:
            return replay_probe.fail(str(e)[-400:])
    return replay_probe.Cases().finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
