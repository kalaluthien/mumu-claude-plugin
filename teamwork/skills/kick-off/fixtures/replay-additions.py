#!/usr/bin/env python3
"""Replay owner additions to a held task on a git board in a temporary repository, with a `gh` on `PATH` that logs each call and fails, and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-additions.py --case <name>
- path: an addition recorded by `decide` leaves the body as it was and shows in `list-additions.py`; a worker's `edit --base` folds it; a stale diff of the old body is refused with the board unchanged; nothing is left unfolded
- prefix: with twenty additions recorded, a fold that names the last leaves the other nineteen listed, since `#comment-2` starts `#comment-21`
- writes: three additions take fewer board writes by the path the playbooks give than by one body edit and one precheck comment per addition"""
import os
import pathlib
import subprocess
import sys
import tempfile

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
BODY = "## Goal\n\nProbe the pane.\n\n## Definition of done\n\n1. [check] **probe passes**: `echo PASS` prints `PASS`; on base `FAIL`.\n"
HOLD = "DECIDED: probe-worker holds this.\n\n```teamwork\nholders: probe-worker\n```\n"
ADDED = ("drop the releases line", "show the blocker on the title", "hide closed blockers")


def setup():
    work = pathlib.Path(tempfile.mkdtemp(prefix="additions-"))
    repo = work / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    stub = work / "bin"
    stub.mkdir()
    (stub / "gh").write_text(f'#!/bin/sh\necho "$@" >> {work}/gh.log\nexit 1\n')
    (stub / "gh").chmod(0o755)
    env = {**os.environ, "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "home"), "TEAMWORK_BOARD": "git", "PATH": f"{stub}:{os.environ['PATH']}"}
    (work / "body.md").write_text(BODY)
    made = run(env, repo, "use-board.py", "file", "Probe the pane", work / "body.md")
    number = made.stdout.strip().rsplit("/", 1)[-1]
    (work / "hold.md").write_text(HOLD)
    run(env, repo, "use-board.py", "decide", number, work / "hold.md")
    return work, repo, env, number


def run(env, repo, script, *argv):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, argv)], cwd=repo, capture_output=True, text=True, env=env)


def commits(repo):
    return int(subprocess.run(["git", "rev-list", "--count", "refs/teamwork/board"], cwd=repo, capture_output=True, text=True).stdout)


def body(repo, number):
    return subprocess.run(["git", "show", f"refs/teamwork/board:{number}/body.md"], cwd=repo, capture_output=True, text=True).stdout


def owner_says(work, env, repo, number, wish):
    path = work / "owner.md"
    path.write_text(f"DECIDED: the owner added: {wish}\n\n> {wish}\n\n```decision\ndecision: {wish}\ndecided by: owner\ndoor: two-way\n```\n")
    done = run(env, repo, "use-board.py", "decide", number, path)
    return done.stdout.strip().splitlines()[-1] if done.returncode == 0 else fail_with(done)


def fail_with(done):
    raise SystemExit(f"FAIL: exit {done.returncode}: {(done.stdout + done.stderr).strip()[-300:]}")


def diff_of(work, old, new):
    (work / "old").write_text(old)
    (work / "new").write_text(new)
    path = work / "edit.diff"
    path.write_text(subprocess.run(["diff", "-u", "--label", "a/body", "--label", "b/body", "old", "new"], cwd=work, capture_output=True, text=True).stdout)
    return path


def sha_of(env, repo, script, number):
    found = run(env, repo, script, *(["read"] if script == "use-board.py" else []), number).stdout
    return next(line.split("body sha: ")[1].strip() for line in found.splitlines() if "body sha: " in line)


def check(env, repo, work, ok, why):
    log = work / "gh.log"
    if log.exists():
        raise SystemExit(f"FAIL: a task step called gh: {log.read_text().strip()[:200]}")
    if not ok:
        raise SystemExit(f"FAIL: {why}")


def case_path(work, repo, env, number):
    first = sha_of(env, repo, "use-board.py", number)
    url = owner_says(work, env, repo, number, ADDED[0])
    listed = run(env, repo, "list-additions.py", number)
    check(env, repo, work, listed.returncode == 0 and url in listed.stdout and "not in the body: 1" in listed.stdout and sha_of(env, repo, "list-additions.py", number) == first and body(repo, number) == BODY,
          f"a recorded addition must leave the body alone and be listed once, got {listed.stdout!r}")
    folded = BODY.replace("Probe the pane.", f"Probe the pane; the owner said: {ADDED[0]}.")
    done = run(env, repo, "use-board.py", "edit", number, diff_of(work, BODY, folded), f"DECIDED: folds {url}", "--base", first)
    check(env, repo, work, done.returncode == 0 and body(repo, number) == folded and "not in the body: 0" in run(env, repo, "list-additions.py", number).stdout,
          f"the worker's fold must apply and leave nothing unfolded: {done.stderr.strip()[-200:]}")
    before = commits(repo)
    stale = run(env, repo, "use-board.py", "edit", number, diff_of(work, folded, BODY), "DECIDED: put back the old body", "--base", first)
    check(env, repo, work, stale.returncode != 0 and commits(repo) == before and body(repo, number) == folded,
          f"a diff made from the old body must be refused with nothing written: exit {stale.returncode}, {commits(repo) - before} commits added")


def case_prefix(work, repo, env, number):
    urls = [owner_says(work, env, repo, number, f"wish {k}") for k in range(20)]
    sha = sha_of(env, repo, "list-additions.py", number)
    folded = BODY.replace("Probe the pane.", "Probe the pane; wish 19.")
    done = run(env, repo, "use-board.py", "edit", number, diff_of(work, BODY, folded), f"DECIDED: folds {urls[-1]}", "--base", sha)
    listed = run(env, repo, "list-additions.py", number).stdout
    check(env, repo, work, done.returncode == 0 and "not in the body: 19" in listed and all(url in listed for url in urls[:-1]) and urls[-1] not in listed,
          f"folding the last of twenty must leave the other nineteen listed, got {listed[:300]!r}")


def precheck(work, env, repo, number):
    path = work / "precheck.md"
    path.write_text("REPORTED: criteria at the head pass\n")
    return run(env, repo, "use-board.py", "comment", number, path)


def case_writes(work, repo, env, number):
    old_start = commits(repo)
    text = BODY
    for wish in ADDED:  # one decision, one manager edit, one worker edit and one precheck comment per addition
        url = owner_says(work, env, repo, number, wish)
        for who in ("manager", "worker"):
            text_new = text.replace("Probe the pane", f"Probe the pane ({who} {wish})", 1)
            done = run(env, repo, "use-board.py", "edit", number, diff_of(work, text, text_new), f"DECIDED: {who} folds {url}")
            check(env, repo, work, done.returncode == 0, f"edit: {done.stderr.strip()[-200:]}")
            text = text_new
        precheck(work, env, repo, number)
    old = commits(repo) - old_start
    other_work, other_repo, other_env, other = setup()
    start = commits(other_repo)
    urls = [owner_says(other_work, other_env, other_repo, other, wish) for wish in ADDED]
    listed = run(other_env, other_repo, "list-additions.py", other)
    sha = sha_of(other_env, other_repo, "list-additions.py", other)
    folded = BODY.replace("Probe the pane.", "Probe the pane; " + "; ".join(ADDED) + ".")
    done = run(other_env, other_repo, "use-board.py", "edit", other, diff_of(other_work, BODY, folded), f"DECIDED: folds {' '.join(urls)}", "--base", sha)
    precheck(other_work, other_env, other_repo, other)
    new = commits(other_repo) - start
    check(other_env, other_repo, other_work, listed.returncode == 0 and done.returncode == 0 and "not in the body: 0" in run(other_env, other_repo, "list-additions.py", other).stdout,
          f"the new path must fold all three: {done.stderr.strip()[-200:]}")
    check(env, repo, work, new < old, f"the new path took {new} board writes, the old {old}")
    print(f"three additions: {old} board writes by one edit and one precheck each, {new} by one fold")


CASES = {"path": case_path, "prefix": case_prefix, "writes": case_writes}


def main(args):
    if len(args) != 2 or args[0] != "--case" or args[1] not in CASES:
        print(__doc__, file=sys.stderr)
        return 2
    CASES[args[1]](*setup())
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
