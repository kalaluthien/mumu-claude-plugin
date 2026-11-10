#!/usr/bin/env python3
"""Check that a check starting live sessions replays its saved transcript and stops at its cap, with a stub `claude` that logs each session it starts, and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-live-runs.py [--case <name>]   (no argument: every one in turn)
- replay: a fix to the judging stage starts no new session, a change to a watched file starts one, and a body that runs `claude -p` unwatched or past its first stage is refused by check-criteria.py
- cap: a fifth session with no `live runs` decision starts nothing, and a run past the task's `live runs` count starts no session, fails the check and prints the `BLOCKED due` line"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

LIB = pathlib.Path(__file__).resolve().parents[3] / "lib"
sys.path.insert(0, str(LIB))
import replay_probe  # noqa: E402

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
CRITERION = "`claude -p hello | python3 judge.py` prints `PASS`; watches: app; on base `FAIL`"
BODY = "## Goal\n\nProbe the replay.\nPath: caller: probe-worker; before: filing; after: judging; meets: teamwork-manager\n\n## Definition of done\n\n1. [check] **The stub session earns a verdict from the judge**: " + CRITERION + ".\n"
JUDGE = "import sys\nprint('PASS' if 'verdict' in sys.stdin.read() else 'FAIL')\n"


def setup():
    """(work folder, repository, environment) with a committed `app/` and `judge.py`, and a `claude` that logs one line per session."""
    work = pathlib.Path(tempfile.mkdtemp(prefix="live-runs-"))
    repository = work / "repo"
    (repository / "app").mkdir(parents=True)
    (repository / "app" / "main.txt").write_text("one\n")
    (repository / "judge.py").write_text("import sys\nprint('FAIL')\n")
    bin_folder = work / "bin"
    bin_folder.mkdir()
    stub = replay_probe.write_text(bin_folder, "claude", f'#!/bin/sh\necho started >> {work}/claude.log\necho verdict\n')
    stub.chmod(0o755)
    environment = {**os.environ, **replay_probe.IDENTITY, "PATH": f"{bin_folder}:{os.environ['PATH']}", "HOME": str(work)}
    for argv in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "probe"]):
        replay_probe.sh("git", *argv, cwd=repository, environment=environment)
    (work / "body.md").write_text(BODY)
    return work, repository, environment


def sessions(work):
    log = work / "claude.log"
    return len(log.read_text().split()) if log.exists() else 0


def case_replay():
    work, repository, environment = setup()
    run = lambda: replay_probe.run_python(SCRIPTS / "run-criteria.py", repository, environment, work / "body.md")
    first = run()
    if sessions(work) != 1 or "| fail |" not in first.stdout:
        return replay_probe.fail(f"the first run should start one session and fail on the buggy judge: {sessions(work)} sessions, {first.stdout!r}")
    (repository / "judge.py").write_text(JUDGE)
    second = run()
    if sessions(work) != 1 or "| pass |" not in second.stdout or "1 replayed" not in second.stdout:
        return replay_probe.fail(f"a judge-only fix should replay with no new session: {sessions(work)} sessions, {second.stdout!r}")
    (repository / "app" / "main.txt").write_text("two\n")
    third = run()
    if sessions(work) != 2 or "| pass |" not in third.stdout:
        return replay_probe.fail(f"a watched file's change should start one new session: {sessions(work)} sessions, {third.stdout!r}")
    (work / "body.md").write_text(BODY.replace("hello", "goodbye"))
    fourth = run()
    if sessions(work) != 3 or "| pass |" not in fourth.stdout:
        return replay_probe.fail(f"a change to the first stage should start one new session: {sessions(work)} sessions, {fourth.stdout!r}")
    (work / "body.md").write_text(BODY.replace("watches: app", "watches: appp"))
    typo = run()
    if sessions(work) != 3 or "| fail |" not in typo.stdout or "watched path not found" not in typo.stdout:
        return replay_probe.fail(f"a missing watched path should fail the check unrun: {sessions(work)} sessions, {typo.stdout!r}")
    (work / "body.md").write_text(BODY)
    (work / "bin" / "claude").write_text(f'#!/bin/sh\necho started >> {work}/claude.log\necho "rate limit"\nexit 1\n')
    (repository / "app" / "main.txt").write_text("three\n")
    run()
    if sessions(work) != 4:
        return replay_probe.fail(f"a failed session must not be replayed: {sessions(work)} sessions, want 4")
    (repository / "app" / "main.txt").write_text("four\n")
    fifth = run()
    if sessions(work) != 4 or "BLOCKED due: live runs reached the cap of 4" not in fifth.stdout:
        return replay_probe.fail(f"with no `live runs` decision the fifth session should not start: {sessions(work)} sessions, {fifth.stdout!r}")
    (work / "grep.md").write_text(BODY.replace("`claude -p hello | python3 judge.py`", "`git grep -c 'claude -p' app | cat`"))
    lint = lambda criterion: replay_probe.run_python(SCRIPTS / "check-criteria.py", repository, environment, work / criterion)
    for name, text in (("unwatched.md", BODY.replace("watches: app; ", "")), ("late.md", BODY.replace("claude -p hello | python3 judge.py", "echo x | claude -p hello"))):
        (work / name).write_text(text)
        refused = lint(name)
        if refused.returncode != 1 or "live stage not replayable" not in refused.stdout:
            return replay_probe.fail(f"{name} should be refused: exit {refused.returncode}, {refused.stdout!r}")
    scan = lint("grep.md")
    if "live stage" in scan.stdout:
        return replay_probe.fail(f"a grep for the words claude -p is no session: {scan.stdout!r}")
    accepted = lint("body.md")
    if accepted.returncode:
        return replay_probe.fail(f"a watched first-stage session should pass the lint: {accepted.stdout!r}")
    return 0


def case_cap():
    work, repository, environment = setup()
    (repository / "judge.py").write_text(JUDGE)
    task = {"body": BODY, "trusted": True, "comments": [{"body": "DECIDED: cap it.\n\n```teamwork\nlive runs: 1\n```\n", "trusted": True}]}
    run = lambda: subprocess.run([sys.executable, str(SCRIPTS / "run-criteria.py"), "-"], cwd=repository, env=environment, input=json.dumps(task), capture_output=True, text=True)
    first = run()
    (repository / "app" / "main.txt").write_text("two\n")
    second = run()
    if sessions(work) != 1 or second.returncode != 1 or "BLOCKED due: live runs reached the cap of 1" not in second.stdout:
        return replay_probe.fail(f"a run past the cap should start nothing and report: exit {first.returncode}/{second.returncode}, {sessions(work)} sessions, {second.stdout!r}")
    return 0


CASES = {"replay": case_replay, "cap": case_cap}


def main(args):
    if not args:
        return replay_probe.run_every(__file__, "--case", CASES)
    if len(args) != 2 or args[0] != "--case" or args[1] not in CASES:
        print(__doc__, file=sys.stderr)
        return 2
    if CASES[args[1]]():
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
