#!/usr/bin/env python3
"""Replay owner additions to a held task on a git board in a scratch repository, with a `gh` on `PATH` that logs each call and fails, and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-additions.py [--case <name>]   (no argument: every one in turn)
- path: an addition recorded by `decide` leaves the body as it was and shows in `list-additions.py`; a worker's `edit --base` folds it; an edit whose `--base` names the old body is refused with the board unchanged; nothing is left unfolded
- prefix: with twenty additions recorded, a fold that names the last leaves the other nineteen listed, since `#comment-2` starts `#comment-21`
- writes: three additions take fewer board writes by the path the playbooks give than by one body edit and one precheck comment per addition"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
LISTER = "../references/worker/scripts/list-additions.py"
BODY = replay_probe.BODY
ADDED = ("drop the releases line", "show the blocker on the title", "hide closed blockers")


def setup(work):
    """(sandbox, number) of a task filed and held on a scratch board in WORK."""
    box = replay_probe.Sandbox(work, [replay_probe.agent("probe-worker", 1)])
    made = run(box, "use-board.py", "file", "--title", "Probe the pane", "--body", replay_probe.write_text(work, "body.md", BODY))
    number = made.stdout.strip().rsplit("/", 1)[-1]
    run(box, "use-board.py", "hold", number, "--holders", "probe-worker")
    return box, number


def run(box, script, *argv):
    return box.python(SCRIPTS / script, *map(str, argv))


def commits(box):
    return int(box.git("rev-list", "--count", "refs/teamwork-blackboard"))


def body(box, number):
    return box.git("show", f"refs/teamwork-blackboard:{number}/body.md")


def owner_says(box, number, wish):
    done = run(box, "use-board.py", "decide", number, "--decision", wish, "--text", replay_probe.write_text(box.work, "owner.md", f"> {wish}\n"), "--by", "owner")
    if done.returncode:
        raise SystemExit(replay_probe.fail(f"exit {done.returncode}: {(done.stdout + done.stderr).strip()[-300:]}"))
    return done.stdout.strip().splitlines()[-1]


def body_file(box, new):
    """The file of NEW, the body an edit hands over."""
    return replay_probe.write_text(box.work, "edit.md", new)


def sha_of(box, script, number):
    found = run(box, script, *(["read"] if script == "use-board.py" else []), number).stdout
    return next(line.split("body sha: ")[1].strip() for line in found.splitlines() if "body sha: " in line)


def check(box, ok, why):
    if box.gh_calls():
        raise SystemExit(replay_probe.fail(f"a task step called gh: {box.gh_calls()[0][:200]}"))
    if not ok:
        raise SystemExit(replay_probe.fail(why))


def case_path(work, box, number):
    first = sha_of(box, "use-board.py", number)
    url = owner_says(box, number, ADDED[0])
    listed = run(box, LISTER, number)
    check(box, listed.returncode == 0 and url in listed.stdout and "not in the body: 1" in listed.stdout and sha_of(box, LISTER, number) == first and body(box, number) == BODY,
          f"a recorded addition must leave the body alone and be listed once, got {listed.stdout!r}")
    folded = BODY.replace("Do it.", f"Do it; the owner said: {ADDED[0]}.")
    done = run(box, "use-board.py", "edit", number, "--body", body_file(box, folded), "--reason", f"folds {url}", "--base", first)
    check(box, done.returncode == 0 and body(box, number) == folded and "not in the body: 0" in run(box, LISTER, number).stdout,
          f"the worker's fold must apply and leave nothing unfolded: {done.stderr.strip()[-200:]}")
    before = commits(box)
    stale = run(box, "use-board.py", "edit", number, "--body", body_file(box, BODY), "--reason", "put back the old body", "--base", first)
    check(box, stale.returncode != 0 and commits(box) == before and body(box, number) == folded,
          f"an edit based on the old body must be refused with nothing written: exit {stale.returncode}, {commits(box) - before} commits added")


def case_prefix(work, box, number):
    urls = [owner_says(box, number, f"wish {k}") for k in range(20)]
    sha = sha_of(box, LISTER, number)
    folded = BODY.replace("Do it.", "Do it; wish 19.")
    done = run(box, "use-board.py", "edit", number, "--body", body_file(box, folded), "--reason", f"folds {urls[-1]}", "--base", sha)
    listed = run(box, LISTER, number).stdout
    check(box, done.returncode == 0 and "not in the body: 19" in listed and all(url in listed for url in urls[:-1]) and urls[-1] not in listed,
          f"folding the last of twenty must leave the other nineteen listed, got {listed[:300]!r}")


def precheck(box, number):
    return run(box, "use-board.py", "comment", number, "--reported", "criteria at the head pass")


def case_writes(work, box, number):
    old_start = commits(box)
    text = BODY
    for wish in ADDED:  # one decision, one manager edit, one worker edit and one precheck comment per addition
        url = owner_says(box, number, wish)
        for who in ("manager", "worker"):
            text_new = text.replace("Do it", f"Do it ({who} {wish})", 1)
            done = run(box, "use-board.py", "edit", number, "--body", body_file(box, text_new), "--reason", f"{who} folds {url}", "--base", sha_of(box, "use-board.py", number))
            check(box, done.returncode == 0, f"edit: {done.stderr.strip()[-200:]}")
            text = text_new
        precheck(box, number)
    old = commits(box) - old_start
    other_box, other = setup(work / "other")
    start = commits(other_box)
    urls = [owner_says(other_box, other, wish) for wish in ADDED]
    listed = run(other_box, LISTER, other)
    sha = sha_of(other_box, LISTER, other)
    folded = BODY.replace("Do it.", "Do it; " + "; ".join(ADDED) + ".")
    done = run(other_box, "use-board.py", "edit", other, "--body", body_file(other_box, folded), "--reason", f"folds {' '.join(urls)}", "--base", sha)
    precheck(other_box, other)
    new = commits(other_box) - start
    check(other_box, listed.returncode == 0 and done.returncode == 0 and "not in the body: 0" in run(other_box, LISTER, other).stdout,
          f"the new path must fold all three: {done.stderr.strip()[-200:]}")
    check(box, new < old, f"the new path took {new} board writes, the old {old}")
    print(f"three additions: {old} board writes by one edit and one precheck each, {new} by one fold")


CASES = {"path": case_path, "prefix": case_prefix, "writes": case_writes}


def main(args):
    if not args:
        return replay_probe.run_every(__file__, "--case", CASES)
    if len(args) != 2 or args[0] != "--case" or args[1] not in CASES:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("additions-") as work:
        CASES[args[1]](work, *setup(work / "first"))
    return replay_probe.Cases().finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
