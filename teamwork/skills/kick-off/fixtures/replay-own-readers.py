#!/usr/bin/env python3
"""Run each script that names the session it runs in, `list-sessions.py --me`, `rename-session.py` and the heartbeat monitor `print-team-gaps.py`, in a pane that
herdr records as the worker's, under a stand-in `claude` started as the worker, as a session renamed to the worker and as a bare `claude -p`, on a temporary
repository with a git board and the fake herdr beside this file. Print `ok <case>` or `fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `list-started`, `list-renamed`, `list-child`: `--me` prints the worker's name for the first two and nothing for the child;
- `monitor-started`, `monitor-child`: the monitor prints the worker's `answered` line for the started worker and nothing for the child;
- `rename-child`, `rename-started`: the child is refused as owning no session, while the started worker gets past that refusal.

usage: replay-own-readers.py"""
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import agent  # noqa: E402
import replay_probe  # noqa: E402

SCRIPTS = ROOT / "skills" / "kick-off" / "scripts"
RENAME = ROOT / "skills" / "kick-off" / "references" / "adapters" / "session-herdr" / "scripts" / "rename-session.py"
MONITOR = ROOT / "monitors" / "print-team-gaps.py"
NAME = "c-worker"
SESSION = "00000000-0000-4000-8000-000000000003"
QUIET_SECONDS = 3
RENAME_SECONDS = 5  # a rename that got past the refusal goes on to wait for a prompt box, which the fake herdr never shows
# each way a session runs: the stand-in's options, whether the transcript holds the worker's title
STARTED = (agent.command(NAME, "plugin", "opus", "high", []), False)
RENAMED = (["--model", "opus"], True)
CHILD = (["-p", "probe", "--model", "haiku"], False)
results = {}


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[:900]}", flush=True)
    results[name] = ok


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="own-readers-"))
    repository, state = work / "repo", work / "herdr.json"
    config = work / "claude" / "projects" / "folder"
    config.mkdir(parents=True)
    environment = {**os.environ, **replay_probe.IDENTITY, "CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_GLOBAL": str(work / "gitconfig"),
                   "TEAMWORK_FAKE_HERDR_STATE": str(state), "PATH": f"{HERE / 'fake-herdr'}:{os.environ['PATH']}", "TEAMWORK_MONITOR_POLL": "0.3",
                   "CLAUDE_CODE_SESSION_ID": SESSION}
    board_environment = {key: value for key, value in environment.items() if key != "CLAUDE_CODE_SESSION_ID"}
    replay_probe.write_git_config(work)
    repository.mkdir()
    for argv in (["init", "-q", "-b", "main"], ["commit", "-q", "--allow-empty", "-m", "start"]):
        subprocess.run(["git", *argv], cwd=repository, check=True, env=environment, capture_output=True)
    agents = [{"name": name, "pane_id": f"w1:p{pane}", "tab_id": f"w1:t{pane}", "workspace_id": "w1", "agent": "claude", "agent_status": "working", "interactive_ready": True,
               **({"agent_session": {"value": SESSION}} if name == NAME else {})} for name, pane in (("c-manager", 1), (NAME, 2))]
    state.write_text(json.dumps({"n": 20, "agents": agents, "tabs": [{"tab_id": each["tab_id"], "workspace_id": "w1", "label": each["name"]} for each in agents]}))
    transcript = config / f"{SESSION}.jsonl"

    def command(script, argv, options, titled):
        transcript.unlink(missing_ok=True)
        if titled:
            transcript.write_text(json.dumps({"type": "custom-title", "customTitle": NAME, "sessionId": SESSION}, separators=(",", ":")) + "\n")
        pane_environment = {**environment, "HERDR_PANE_ID": "w1:p2"}
        return replay_probe.as_claude([sys.executable, script, *argv], options, work / "stand-in"), pane_environment

    def run(script, argv, options_titled, seconds=60):
        argv, pane_environment = command(script, argv, *options_titled)
        try:
            done = subprocess.run(argv, cwd=repository, env=pane_environment, capture_output=True, text=True, timeout=seconds)
            return done.returncode, done.stdout + done.stderr
        except subprocess.TimeoutExpired as late:
            return None, (late.stdout or b"").decode() + (late.stderr or b"").decode()

    def heartbeat(options_titled):
        argv, pane_environment = command(MONITOR, [], *options_titled)
        with (work / "monitor.log").open("w") as log:
            live = subprocess.Popen(argv, cwd=repository, env=pane_environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            time.sleep(QUIET_SECONDS)
            os.killpg(live.pid, signal.SIGKILL)
            live.wait()
        return (work / "monitor.log").read_text()

    def use(pane, *argv):
        pane_environment = {**board_environment, "HERDR_PANE_ID": pane}  # the board's writers are found by pane, the session id being the worker's alone
        done = subprocess.run(replay_probe.as_pane([SCRIPTS / "use-board.py", *argv], pane, pane_environment, work / "board-stand-in"), cwd=repository, env=pane_environment,
                              capture_output=True, text=True)
        return done.stdout.strip()

    number = use("w1:p1", "file", "--title", "Answer a held task", "--body", str(replay_probe.write_text(work, "body.md", "Answer a held task.\n")), "--label", "scope:x").rsplit("/", 1)[-1].removesuffix(".json")
    use("w1:p1", "decide", number, "--decision", f"{NAME} holds this.", "--holders", NAME)
    asked = use("w1:p2", "comment", number, "--blocked", "which way")
    use("w1:p1", "decide", number, "--decision", "take the first way.", "--by", "c-manager", "--answers", asked)

    code, out = run(SCRIPTS / "list-sessions.py", ["--me"], STARTED)
    step("list-started", out.strip() == NAME, (code, out))
    code, out = run(SCRIPTS / "list-sessions.py", ["--me"], RENAMED)
    step("list-renamed", out.strip() == NAME, (code, out))
    code, out = run(SCRIPTS / "list-sessions.py", ["--me"], CHILD)
    step("list-child", out.strip() == "", (code, out))
    saw = heartbeat(STARTED)
    step("monitor-started", f"answered #{number}" in saw, saw)
    saw = heartbeat(CHILD)
    step("monitor-child", saw.strip() == "", saw)
    # the fake herdr keeps a rename, so the renames come last
    code, out = run(RENAME, ["c-worker2"], CHILD)
    step("rename-child", code == 1 and "no herdr session owns this pane" in out, (code, out))
    code, out = run(RENAME, ["c-worker2"], STARTED, seconds=RENAME_SECONDS)
    step("rename-started", "no herdr session owns this pane" not in out, (code, out))
    print("PASS" if all(results.values()) else "FAIL")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
