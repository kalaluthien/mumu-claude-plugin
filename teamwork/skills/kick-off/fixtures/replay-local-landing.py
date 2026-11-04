#!/usr/bin/env python3
"""Land a worker's change by use-landing.py in a temporary repository whose `origin` is a bare repository beside it, with a `gh` on PATH that logs each call and fails,
and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-local-landing.py --case <name>
- pushes: the merge puts the new commit on `origin`'s base, and the local base, its checkout and the change record show it
- push-refused: an `origin` that refuses the push makes the merge exit 1 with the remote's reason, and the base here, the remote's base and the change are as they were
- no-gh: change, merge and remove-worktree call no gh
- no-origin: a repository with no remote merges locally and removes the worker's worktree with no gh call, and pushes nothing
- dirty-base: an uncommitted file of the base checkout that the change also edits, its name holding a space, refuses the merge before any push, and nothing moves"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"


def sh(*argv, cwd, env, check=True):
    run = subprocess.run([str(a) for a in argv], cwd=cwd, env=env, capture_output=True, text=True)
    if check and run.returncode:
        raise RuntimeError(f"{' '.join(map(str, argv))}: {run.stdout}{run.stderr}")
    return run


def setup(remote=True):
    work = pathlib.Path(tempfile.mkdtemp(prefix="local-landing-"))
    (work / "bin").mkdir()
    (work / "gh.log").write_text("")
    stub = work / "bin" / "gh"
    stub.write_text(f"#!/bin/sh\necho \"$@\" >> {work / 'gh.log'}\nexit 1\n")
    stub.chmod(0o755)
    (work / "gitconfig").write_text("[user]\n\tname = probe\n\temail = probe@example.com\n[init]\n\tdefaultBranch = main\n")
    env = {**dict(os.environ), "PATH": f"{work / 'bin'}:{os.environ['PATH']}", "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_GLOBAL": str(work / "gitconfig")}
    repo, origin = work / "repo", work / "origin.git"
    sh("git", "init", "-q", repo, cwd=work, env=env)
    (repo / "a.txt").write_text("base\n")
    (repo / "a b.txt").write_text("base\n")
    sh("git", "add", "-A", cwd=repo, env=env)
    sh("git", "commit", "-q", "-m", "base", cwd=repo, env=env)
    if remote:
        sh("git", "init", "-q", "--bare", origin, cwd=work, env=env)
        sh("git", "remote", "add", "origin", origin, cwd=repo, env=env)
        sh("git", "push", "-q", "-u", "origin", "main", cwd=repo, env=env)
    return work, repo, origin, env


def worker(work, repo, env, name="b.txt"):
    tree = pathlib.Path(sh(sys.executable, SCRIPTS / "add-worktree.py", "probe-worker", "main", cwd=repo, env=env).stdout.strip())
    (tree / name).write_text("work\n")
    sh("git", "add", "-A", cwd=tree, env=env)
    sh("git", "commit", "-q", "-m", "work", cwd=tree, env=env)
    (work / "body.md").write_text("Probe change. Closes #1.\n")
    sh(sys.executable, SCRIPTS / "use-landing.py", "change", "probe-worker", "Probe change", work / "body.md", cwd=tree, env=env)
    return tree, sh("git", "rev-parse", "HEAD", cwd=tree, env=env).stdout.strip()


def rev(path, ref, env):
    return sh("git", "rev-parse", "--verify", "-q", ref, cwd=path, env=env, check=False).stdout.strip()


def change_state(repo, env):
    file = repo / ".teamwork" / "changes" / "1.json"
    return json.loads(file.read_text())["state"] if file.exists() else None


def fail(why):
    print(f"FAIL: {why}")
    return 1


def merged(work, repo, origin, env, tree, head):
    return sh(sys.executable, SCRIPTS / "use-landing.py", "merge", "1", head, cwd=tree, env=env, check=False)


def case_pushes():
    work, repo, origin, env = setup()
    tree, head = worker(work, repo, env)
    run = merged(work, repo, origin, env, tree, head)
    if run.returncode:
        return fail(f"merge exited {run.returncode}: {run.stderr.strip()}")
    commit = run.stdout.strip()
    if rev(origin, "refs/heads/main", env) != commit or rev(repo, "main", env) != commit:
        return fail(f"origin main {rev(origin, 'refs/heads/main', env)[:9]}, local main {rev(repo, 'main', env)[:9]}, merge printed {commit[:9]}")
    if not (repo / "b.txt").exists() or change_state(repo, env) != "CLOSED":
        return fail("the checkout lacks the merged file, or the change is still open")
    return 0


def case_push_refused():
    work, repo, origin, env = setup()
    hook = origin / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\necho 'no pushes today' >&2\nexit 1\n")
    hook.chmod(0o755)
    tree, head = worker(work, repo, env)
    before = (rev(repo, "main", env), rev(origin, "refs/heads/main", env))
    run = merged(work, repo, origin, env, tree, head)
    if run.returncode != 1 or "no pushes today" not in run.stderr:
        return fail(f"merge exited {run.returncode}: {run.stdout}{run.stderr}")
    after = (rev(repo, "main", env), rev(origin, "refs/heads/main", env))
    if before != after or (repo / "b.txt").exists() or change_state(repo, env) != "OPEN":
        return fail(f"the base here, the remote's base or the change moved: {before} -> {after}, change {change_state(repo, env)}")
    return 0


def case_no_gh():
    work, repo, origin, env = setup()
    tree, head = worker(work, repo, env)
    run = merged(work, repo, origin, env, tree, head)
    if run.returncode:
        return fail(f"merge exited {run.returncode}: {run.stderr.strip()}")
    removed = sh(sys.executable, SCRIPTS / "remove-worktree.py", "probe-worker", cwd=repo, env=env, check=False)
    calls = (work / "gh.log").read_text().strip()
    if calls:
        return fail(f"gh was called: {calls} (remove-worktree exit {removed.returncode}: {removed.stderr.strip()[-200:]})")
    return 0


def case_no_origin():
    work, repo, origin, env = setup(remote=False)
    tree, head = worker(work, repo, env)
    run = merged(work, repo, origin, env, tree, head)
    if run.returncode or rev(repo, "main", env) != run.stdout.strip() or not (repo / "b.txt").exists():
        return fail(f"merge exited {run.returncode}: {run.stdout}{run.stderr}")
    sh(sys.executable, SCRIPTS / "remove-worktree.py", "probe-worker", cwd=repo, env=env, check=False)
    calls = (work / "gh.log").read_text().strip()
    if calls:
        return fail(f"gh was called: {calls}")
    return 0


def case_dirty_base():
    work, repo, origin, env = setup()
    tree, head = worker(work, repo, env, name="a b.txt")
    (repo / "a b.txt").write_text("mine, not committed\n")
    before = (rev(repo, "main", env), rev(origin, "refs/heads/main", env))
    run = merged(work, repo, origin, env, tree, head)
    after = (rev(repo, "main", env), rev(origin, "refs/heads/main", env))
    if run.returncode != 1 or before != after or change_state(repo, env) != "OPEN" or (repo / "a b.txt").read_text() != "mine, not committed\n":
        return fail(f"merge exited {run.returncode}: {run.stderr.strip()[-200:]}; the bases moved {before} -> {after}")
    return 0


CASES = {"pushes": case_pushes, "push-refused": case_push_refused, "no-gh": case_no_gh, "no-origin": case_no_origin, "dirty-base": case_dirty_base}


def main(args):
    if len(args) != 2 or args[0] != "--case" or args[1] not in CASES:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        if CASES[args[1]]():
            return 1
    except RuntimeError as e:
        return fail(str(e)[-400:])
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
