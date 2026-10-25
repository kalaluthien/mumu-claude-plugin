#!/usr/bin/env python3
"""Write the board setting into a temporary repository with no remote after the manager's heartbeat started, and print `ok <step>` or
`fail <step>: <what differed>` for each step; exit 1 on any fail. No step reaches GitHub: a `gh` that always fails stands first on PATH.

usage: replay-board-setting.py [-v]
`-v` also prints the heartbeat's output.
- late-setting: the heartbeat, started with no board setting, routes the files board's backlog once `.claude/settings.local.json` names that board
- signal: that change touched the signal file, which wakes the issue pane to read the board again
- worktree: a script run in a worktree of the repository reads the board and landing the main checkout's settings name
- environment-wins: `TEAMWORK_BOARD` in the environment wins over the settings
- failure-names-board: the pane's board read names the board whose read failed"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
USE = HERE.parent / "scripts" / "use-board.py"
work = pathlib.Path(tempfile.mkdtemp(prefix="board-setting-"))
repo = work / "repo"
failed = []


def environment(**more):
    base = {k: v for k, v in os.environ.items() if k not in ("TEAMWORK_BOARD", "TEAMWORK_LANDING")}
    return {**base, "TEAMWORK_BOARD_DIR": str(work / "board"), "CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_GLOBAL": str(work / "gitconfig"),
            "PATH": f"{work / 'bin'}:{HERE / 'fake-herdr'}:{os.environ['PATH']}", "PYTHONPATH": str(ROOT / "lib"), **more}


def run(argv, cwd=repo, **more):
    return subprocess.run([str(a) for a in argv], cwd=cwd, env=environment(**more), capture_output=True, text=True, timeout=60)


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {detail.strip()}", flush=True)
    if not ok:
        failed.append(name)


def printed(log, text, seconds):
    """Whether the running heartbeat's LOG shows TEXT within SECONDS."""
    end = time.time() + seconds
    while time.time() < end and text not in log.read_text():
        time.sleep(0.2)
    return text in log.read_text()


def kinds(cwd, **more):
    return run([sys.executable, "-c", "import board, landing; print(board.kind(), landing.kind())"], cwd, **more).stdout.strip()


def main(args):
    if any(a != "-v" for a in args):
        print(__doc__, file=sys.stderr)
        return 2
    (work / "bin").mkdir()
    (work / "bin" / "gh").write_text("#!/bin/sh\necho 'gh: no remote' >&2\nexit 1\n")
    (work / "bin" / "gh").chmod(0o755)
    repo.mkdir()
    for argv in (["init", "-q", "-b", "main"], ["commit", "-q", "--allow-empty", "-m", "start"]):
        run(["git", *argv], GIT_AUTHOR_NAME="probe", GIT_AUTHOR_EMAIL="probe@example.com", GIT_COMMITTER_NAME="probe", GIT_COMMITTER_EMAIL="probe@example.com")
    (work / "body.md").write_text("Probe the late board setting.\n")
    run([sys.executable, USE, "file", "Probe the late setting", work / "body.md", "backlog"], TEAMWORK_BOARD="files")

    team = [{"name": "probe-manager", "pane_id": "w1:p1", "tab_id": "w1:t1", "workspace_id": "w1", "agent": "claude", "agent_status": "working",
             "interactive_ready": True}]
    (work / "herdr.json").write_text(json.dumps({"n": 10, "agents": team, "tabs": [{"tab_id": "w1:t1", "workspace_id": "w1", "label": "probe-manager"}]}))
    log = work / "heartbeat.log"
    live = subprocess.Popen([str(ROOT / "monitors" / "print-team-gaps.py")], cwd=repo, stdout=log.open("w"), stderr=subprocess.STDOUT,
                            env=environment(FAKE_HERDR_STATE=str(work / "herdr.json"), HERDR_PANE_ID="w1:p1", MONITOR_POLL="1"))
    try:
        time.sleep(3)  # a few polls on the default board, which fails, before the setting exists
        early = "route #1" in log.read_text()
        signal = (work / "claude" / "teamwork" / "issues-changed").stat().st_mtime_ns if (work / "claude" / "teamwork" / "issues-changed").exists() else 0
        (repo / ".claude").mkdir()
        (repo / ".claude" / "settings.local.json").write_text(json.dumps({"env": {"TEAMWORK_BOARD": "files", "TEAMWORK_LANDING": "git"}}))
        step("late-setting", not early and printed(log, "route #1 Probe the late setting", 20), log.read_text())
        mark = work / "claude" / "teamwork" / "issues-changed"
        step("signal", mark.exists() and mark.stat().st_mtime_ns != signal, f"stamp {signal}")
    finally:
        live.kill()
    if "-v" in args:
        print(log.read_text(), file=sys.stderr)

    run(["git", "worktree", "add", "-q", "-b", "probe-worker", str(repo / ".claude" / "worktrees" / "probe-worker")])
    step("worktree", kinds(repo / ".claude" / "worktrees" / "probe-worker") == "files git", kinds(repo / ".claude" / "worktrees" / "probe-worker"))
    step("environment-wins", kinds(repo, TEAMWORK_BOARD="github") == "github git", kinds(repo, TEAMWORK_BOARD="github"))

    (repo / ".claude" / "settings.local.json").unlink()
    read = run([ROOT / "hooks" / "list-issue-board.py", "repo", "--json"])
    step("failure-names-board", read.returncode != 0 and "the github board read failed" in read.stderr, read.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
