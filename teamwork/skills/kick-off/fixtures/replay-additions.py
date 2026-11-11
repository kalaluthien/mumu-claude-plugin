#!/usr/bin/env python3
"""Replay owner additions to a held task on a git board in a temporary repository, with a `gh` on `PATH` that logs each call and fails, and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-additions.py [--case <name>]   (no argument: every one in turn)
- path: an addition recorded by `decide` leaves the body as it was and shows in `list-additions.py`; a worker's `edit --base` folds it; a stale diff of the old body is refused with the board unchanged; nothing is left unfolded
- prefix: with twenty additions recorded, a fold that names the last leaves the other nineteen listed, since `#comment-2` starts `#comment-21`
- writes: three additions take fewer board writes by the path the playbooks give than by one body edit and one precheck comment per addition"""
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
BODY = "## Goal\n\nProbe the pane.\n\nPath: caller: the probe run; meets: the owner\n\n## Definition of done\n\n1. [check] **The probe prints PASS when it runs**: `echo PASS` prints `PASS`; on base `FAIL`.\n"
ADDED = ("drop the releases line", "show the blocker on the title", "hide closed blockers")


def setup():
    work = pathlib.Path(tempfile.mkdtemp(prefix="additions-"))
    repository = work / "repo"
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    stub = replay_probe.stub_gh(work)
    environment = {**os.environ, "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "home"), "PATH": f"{stub}:{os.environ['PATH']}"}
    (work / "body.md").write_text(BODY)
    made = run(environment, repository, "use-board.py", "file", "Probe the pane", work / "body.md")
    number = made.stdout.strip().rsplit("/", 1)[-1]
    run(environment, repository, "use-board.py", "hold", number, "probe-worker")
    return work, repository, environment, number


def run(environment, repository, script, *argv):
    return replay_probe.run_python(SCRIPTS / script, repository, environment, *argv)


def commits(repository):
    return int(subprocess.run(["git", "rev-list", "--count", "refs/teamwork-blackboard"], cwd=repository, capture_output=True, text=True).stdout)


def body(repository, number):
    return subprocess.run(["git", "show", f"refs/teamwork-blackboard:{number}/body.md"], cwd=repository, capture_output=True, text=True).stdout


def owner_says(work, environment, repository, number, wish):
    path = work / "owner.md"
    path.write_text(f"DECIDED: {wish}\n\n> {wish}\n")
    done = run(environment, repository, "use-board.py", "decide", number, path, "--by", "owner")
    return done.stdout.strip().splitlines()[-1] if done.returncode == 0 else fail_with(done)


def fail_with(done):
    raise SystemExit(f"FAIL: exit {done.returncode}: {(done.stdout + done.stderr).strip()[-300:]}")


def diff_of(work, old, new):
    """The file of NEW, the body an edit hands over; OLD is what the caller read."""
    path = work / "edit.md"
    path.write_text(new)
    return path


def sha_of(environment, repository, script, number):
    found = run(environment, repository, script, *(["read"] if script == "use-board.py" else []), number).stdout
    return next(line.split("body sha: ")[1].strip() for line in found.splitlines() if "body sha: " in line)


def check(environment, repository, work, ok, why):
    log = work / "gh.log"
    if log.exists():
        raise SystemExit(f"FAIL: a task step called gh: {log.read_text().strip()[:200]}")
    if not ok:
        raise SystemExit(f"FAIL: {why}")


def case_path(work, repository, environment, number):
    first = sha_of(environment, repository, "use-board.py", number)
    url = owner_says(work, environment, repository, number, ADDED[0])
    listed = run(environment, repository, "list-additions.py", number)
    check(environment, repository, work, listed.returncode == 0 and url in listed.stdout and "not in the body: 1" in listed.stdout and sha_of(environment, repository, "list-additions.py", number) == first and body(repository, number) == BODY,
          f"a recorded addition must leave the body alone and be listed once, got {listed.stdout!r}")
    folded = BODY.replace("Probe the pane.", f"Probe the pane; the owner said: {ADDED[0]}.")
    done = run(environment, repository, "use-board.py", "edit", number, diff_of(work, BODY, folded), f"DECIDED: folds {url}", "--base", first)
    check(environment, repository, work, done.returncode == 0 and body(repository, number) == folded and "not in the body: 0" in run(environment, repository, "list-additions.py", number).stdout,
          f"the worker's fold must apply and leave nothing unfolded: {done.stderr.strip()[-200:]}")
    before = commits(repository)
    stale = run(environment, repository, "use-board.py", "edit", number, diff_of(work, folded, BODY), "DECIDED: put back the old body", "--base", first)
    check(environment, repository, work, stale.returncode != 0 and commits(repository) == before and body(repository, number) == folded,
          f"a diff made from the old body must be refused with nothing written: exit {stale.returncode}, {commits(repository) - before} commits added")


def case_prefix(work, repository, environment, number):
    urls = [owner_says(work, environment, repository, number, f"wish {k}") for k in range(20)]
    sha = sha_of(environment, repository, "list-additions.py", number)
    folded = BODY.replace("Probe the pane.", "Probe the pane; wish 19.")
    done = run(environment, repository, "use-board.py", "edit", number, diff_of(work, BODY, folded), f"DECIDED: folds {urls[-1]}", "--base", sha)
    listed = run(environment, repository, "list-additions.py", number).stdout
    check(environment, repository, work, done.returncode == 0 and "not in the body: 19" in listed and all(url in listed for url in urls[:-1]) and urls[-1] not in listed,
          f"folding the last of twenty must leave the other nineteen listed, got {listed[:300]!r}")


def precheck(work, environment, repository, number):
    path = work / "precheck.md"
    path.write_text("REPORTED: criteria at the head pass\n")
    return run(environment, repository, "use-board.py", "comment", number, path)


def case_writes(work, repository, environment, number):
    old_start = commits(repository)
    text = BODY
    for wish in ADDED:  # one decision, one manager edit, one worker edit and one precheck comment per addition
        url = owner_says(work, environment, repository, number, wish)
        for who in ("manager", "worker"):
            text_new = text.replace("Probe the pane", f"Probe the pane ({who} {wish})", 1)
            done = run(environment, repository, "use-board.py", "edit", number, diff_of(work, text, text_new), f"DECIDED: {who} folds {url}", "--base", sha_of(environment, repository, "use-board.py", number))
            check(environment, repository, work, done.returncode == 0, f"edit: {done.stderr.strip()[-200:]}")
            text = text_new
        precheck(work, environment, repository, number)
    old = commits(repository) - old_start
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
    check(environment, repository, work, new < old, f"the new path took {new} board writes, the old {old}")
    print(f"three additions: {old} board writes by one edit and one precheck each, {new} by one fold")


CASES = {"path": case_path, "prefix": case_prefix, "writes": case_writes}


def main(args):
    if not args:
        return replay_probe.run_every(__file__, "--case", CASES)
    if len(args) != 2 or args[0] != "--case" or args[1] not in CASES:
        print(__doc__, file=sys.stderr)
        return 2
    CASES[args[1]](*setup())
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
