#!/usr/bin/env python3
"""Land a worker's change by use-landing.py in a temporary repository whose `origin` is a bare repository beside it, with a `gh` on PATH that logs each call and fails,
and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-local-landing.py [--case <name>]   (no argument: every one in turn)
- pushes: the merge puts the new commit on `origin`'s base, and the local base, its checkout and the change record show it
- push-refused: an `origin` that refuses the push makes the merge exit 1 with the remote's reason, and the base here, the remote's base and the change are as they were
- no-gh: change, merge and remove-worktree call no gh
- no-origin: a repository with no remote merges locally and removes the worker's worktree with no gh call, and pushes nothing
- swap-retired: a swapped-out worker's branch, the ancestor of its successor's merged branch, is removed with its worktree once the successor's change merges, and one branch is left
- dirty-base: an uncommitted file of the base checkout that the change also edits, its name holding a space, refuses the merge before any push, and nothing moves"""
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
sh = replay_probe.sh


def setup(remote=True):
    work = pathlib.Path(tempfile.mkdtemp(prefix="local-landing-"))
    stub = replay_probe.stub_gh(work)
    (work / "gh.log").write_text("")
    replay_probe.write_git_config(work)
    environment = {**dict(os.environ), "PATH": f"{stub}:{os.environ['PATH']}", "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_GLOBAL": str(work / "gitconfig")}
    repository, origin = work / "repo", work / "origin.git"
    sh("git", "init", "-q", repository, cwd=work, environment=environment)
    (repository / "a.txt").write_text("base\n")
    (repository / "a b.txt").write_text("base\n")
    sh("git", "add", "-A", cwd=repository, environment=environment)
    sh("git", "commit", "-q", "-m", "base", cwd=repository, environment=environment)
    if remote:
        sh("git", "init", "-q", "--bare", origin, cwd=work, environment=environment)
        sh("git", "remote", "add", "origin", origin, cwd=repository, environment=environment)
        sh("git", "push", "-q", "-u", "origin", "main", cwd=repository, environment=environment)
    return work, repository, origin, environment


def worker(work, repository, environment, name="b.txt"):
    tree = pathlib.Path(sh(sys.executable, SCRIPTS / "add-worktree.py", "probe-worker", "main", cwd=repository, environment=environment).stdout.strip())
    (tree / name).write_text("work\n")
    sh("git", "add", "-A", cwd=tree, environment=environment)
    sh("git", "commit", "-q", "-m", "work", cwd=tree, environment=environment)
    (work / "body.md").write_text("Probe change. Closes #1.\n")
    sh(sys.executable, SCRIPTS / "use-landing.py", "change", "probe-worker", "Probe change", work / "body.md", cwd=tree, environment=environment)
    return tree, sh("git", "rev-parse", "HEAD", cwd=tree, environment=environment).stdout.strip()


def rev(path, ref, environment):
    return sh("git", "rev-parse", "--verify", "-q", ref, cwd=path, environment=environment, check=False).stdout.strip()


def change_state(repository, environment):
    file = repository / ".teamwork" / "changes" / "1.json"
    return json.loads(file.read_text())["state"] if file.exists() else None


def merged(work, repository, origin, environment, tree, head):
    return sh(sys.executable, SCRIPTS / "use-landing.py", "merge", "1", head, cwd=tree, environment=environment, check=False)


def case_pushes():
    work, repository, origin, environment = setup()
    tree, head = worker(work, repository, environment)
    run = merged(work, repository, origin, environment, tree, head)
    if run.returncode:
        return replay_probe.fail(f"merge exited {run.returncode}: {run.stderr.strip()}")
    commit = run.stdout.strip()
    if rev(origin, "refs/heads/main", environment) != commit or rev(repository, "main", environment) != commit:
        return replay_probe.fail(f"origin main {rev(origin, 'refs/heads/main', environment)[:9]}, local main {rev(repository, 'main', environment)[:9]}, merge printed {commit[:9]}")
    if not (repository / "b.txt").exists() or change_state(repository, environment) != "CLOSED":
        return replay_probe.fail("the checkout lacks the merged file, or the change is still open")
    return 0


def case_push_refused():
    work, repository, origin, environment = setup()
    hook = origin / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\necho 'no pushes today' >&2\nexit 1\n")
    hook.chmod(0o755)
    tree, head = worker(work, repository, environment)
    before = (rev(repository, "main", environment), rev(origin, "refs/heads/main", environment))
    run = merged(work, repository, origin, environment, tree, head)
    if run.returncode != 1 or "no pushes today" not in run.stderr:
        return replay_probe.fail(f"merge exited {run.returncode}: {run.stdout}{run.stderr}")
    after = (rev(repository, "main", environment), rev(origin, "refs/heads/main", environment))
    if before != after or (repository / "b.txt").exists() or change_state(repository, environment) != "OPEN":
        return replay_probe.fail(f"the base here, the remote's base or the change moved: {before} -> {after}, change {change_state(repository, environment)}")
    return 0


def case_no_gh():
    work, repository, origin, environment = setup()
    tree, head = worker(work, repository, environment)
    run = merged(work, repository, origin, environment, tree, head)
    if run.returncode:
        return replay_probe.fail(f"merge exited {run.returncode}: {run.stderr.strip()}")
    removed = sh(sys.executable, SCRIPTS / "remove-worktree.py", "probe-worker", cwd=repository, environment=environment, check=False)
    calls = (work / "gh.log").read_text().strip()
    if calls:
        return replay_probe.fail(f"gh was called: {calls} (remove-worktree exit {removed.returncode}: {removed.stderr.strip()[-200:]})")
    return 0


def case_no_origin():
    work, repository, origin, environment = setup(remote=False)
    tree, head = worker(work, repository, environment)
    run = merged(work, repository, origin, environment, tree, head)
    if run.returncode or rev(repository, "main", environment) != run.stdout.strip() or not (repository / "b.txt").exists():
        return replay_probe.fail(f"merge exited {run.returncode}: {run.stdout}{run.stderr}")
    sh(sys.executable, SCRIPTS / "remove-worktree.py", "probe-worker", cwd=repository, environment=environment, check=False)
    calls = (work / "gh.log").read_text().strip()
    if calls:
        return replay_probe.fail(f"gh was called: {calls}")
    return 0


def case_swap_retired():
    work, repository, origin, environment = setup()
    old, _ = worker(work, repository, environment)
    new = pathlib.Path(sh(sys.executable, SCRIPTS / "add-worktree.py", "probe-opus-worker", "probe-worker", cwd=repository, environment=environment).stdout.strip())
    (new / "c.txt").write_text("more\n")
    sh("git", "add", "-A", cwd=new, environment=environment)
    sh("git", "commit", "-q", "-m", "more", cwd=new, environment=environment)
    sh(sys.executable, SCRIPTS / "use-landing.py", "change", "probe-opus-worker", "Successor change", work / "body.md", cwd=new, environment=environment)
    head = rev(new, "HEAD", environment)
    run = sh(sys.executable, SCRIPTS / "use-landing.py", "merge", "2", head, cwd=new, environment=environment, check=False)
    if run.returncode:
        return replay_probe.fail(f"merge exited {run.returncode}: {run.stderr.strip()}")
    sh(sys.executable, SCRIPTS / "remove-worktree.py", "probe-worker", "probe-opus-worker", cwd=repository, environment=environment, check=False)
    left = sh("git", "branch", "--list", "probe-*", cwd=repository, environment=environment).stdout.strip()
    if left or old.exists() or new.exists():
        return replay_probe.fail(f"branches {left!r} or worktrees left after the successor merged")
    return 0


def case_dirty_base():
    work, repository, origin, environment = setup()
    tree, head = worker(work, repository, environment, name="a b.txt")
    (repository / "a b.txt").write_text("mine, not committed\n")
    before = (rev(repository, "main", environment), rev(origin, "refs/heads/main", environment))
    run = merged(work, repository, origin, environment, tree, head)
    after = (rev(repository, "main", environment), rev(origin, "refs/heads/main", environment))
    if run.returncode != 1 or before != after or change_state(repository, environment) != "OPEN" or (repository / "a b.txt").read_text() != "mine, not committed\n":
        return replay_probe.fail(f"merge exited {run.returncode}: {run.stderr.strip()[-200:]}; the bases moved {before} -> {after}")
    return 0


CASES = {"pushes": case_pushes, "push-refused": case_push_refused, "no-gh": case_no_gh, "no-origin": case_no_origin, "swap-retired": case_swap_retired, "dirty-base": case_dirty_base}


def main(args):
    if not args:
        return replay_probe.run_every(__file__, "--case", CASES)
    if len(args) != 2 or args[0] != "--case" or args[1] not in CASES:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        if CASES[args[1]]():
            return 1
    except RuntimeError as e:
        return replay_probe.fail(str(e)[-400:])
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
