#!/usr/bin/env python3
"""Tell sessions by tell-session.py and print `ok <case>` for each case, or `fail <case>: <what it printed>` and stop.

usage: probe-tell-session.py
Three cases tell a throwaway Claude Code session in a new tab of this workspace: idle, busy in a turn, and blocked at a
tool prompt; three run on the fake herdr beside this file: a receiver `done`, one that refuses its first prompt, and one
that never shows what herdr took. Each case asserts the exit status, 0 when delivered and 1 with a reason when not."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
TELL, CLOSE = HERE.parent / "scripts" / "tell-session.py", HERE.parent / "scripts" / "close-session.py"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import agent  # noqa: E402
import session  # noqa: E402

NAME = f"probe-tell-{os.getpid()}"


def tell(name, text, env=None, timeout=60):
    note = pathlib.Path(tempfile.mkstemp(suffix=".md")[1])
    note.write_text(text)
    process = subprocess.run([str(TELL), name, str(note)], env={**os.environ, "TELL_SESSION_TIMEOUT": str(timeout), **(env or {})}, capture_output=True, text=True)
    return process.returncode, (process.stdout + process.stderr).strip()


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {detail.strip()}", flush=True)
    if not ok:
        sys.exit(1)


def told(outcome, expect_code, expect_text):
    """(whether a tell exited and printed as expected, what it did), the `ok` and `detail` of a step."""
    code, out = outcome
    return code == expect_code and expect_text in out, f"exit {code}: {out}"


def until(test, seconds, what):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if test():
            return
        time.sleep(1)
    screen = [line for line in session.screen(session.agent(NAME)["pane_id"]).splitlines() if line.strip()][-8:] if session.agent(NAME) else []
    raise RuntimeError(f"{NAME} {what} after {seconds}s; its screen ended: {' | '.join(screen)}")


def live():
    folder = tempfile.mkdtemp(prefix="probe-tell-")
    place = session.open_tab(session.sessions()[1]["workspace_id"], folder, NAME)
    session.rename(place, NAME)
    pane = place["pane_id"]
    try:
        session.start(NAME, pane, agent.KIND, ["--name", NAME, "--model", "haiku", "--effort", "low", "--permission-mode", "default", "--allowedTools", "Bash(sleep *)"], 60)
        trust, accept = agent.TRUST
        until(lambda: (trust in session.screen(pane) and session.send_keys(pane, *accept)) or ((session.agent(NAME) or {}).get("interactive_ready")
                      and (session.agent(NAME) or {}).get("agent_status") == "idle"), 90, "never became idle")
        step("idle delivered", *told(tell(NAME, "Reply with the single word ONE."), 0, f"delivered to {NAME}"))
        until(lambda: (session.agent(NAME) or {}).get("agent_status") in ("idle", "done"), 120, "never finished its first reply")
        session.prompt(pane, "Run the Bash command `sleep 25`, then reply with the single word TWO.")
        until(lambda: (session.agent(NAME) or {}).get("agent_status") == "working", 30, "never started its sleep")
        step("busy delivered after its turn", *told(tell(NAME, "Reply with the single word THREE.", timeout=180), 0, "after its turn"))
        until(lambda: (session.agent(NAME) or {}).get("agent_status") in ("idle", "done"), 120, "never finished its third reply")
        session.prompt(pane, f"Run the Bash command `touch {folder}/blocked`.")
        until(lambda: (session.agent(NAME) or {}).get("agent_status") == "blocked", 60, "never stopped at the tool prompt")
        step("blocked not delivered", *told(tell(NAME, "Reply with the single word FOUR.", timeout=8), 1, "blocked at a tool prompt"))
    finally:
        # close-session.py sends no exit to a blocked session, so the tool prompt is dismissed first
        deadline = time.time() + 30
        while (session.agent(NAME) or {}).get("agent_status") == "blocked" and time.time() < deadline:
            session.send_keys(pane, "esc")
            time.sleep(2)
        process = subprocess.run([str(CLOSE), NAME], env={**os.environ, "CLOSE_SESSION_TIMEOUT": "120"}, capture_output=True, text=True)
        if process.returncode:
            step(f"close {NAME}", False, process.stdout + process.stderr)


def fake():
    state = pathlib.Path(tempfile.mkstemp(prefix="fake-herdr-", suffix=".json")[1])
    agents = [{"name": name, "pane_id": f"w1:p{i}", "tab_id": f"w1:t{i}", "workspace_id": "w1", "agent": "codex", "agent_status": status, "interactive_ready": True}
              for i, (name, status) in enumerate((("done-codex", "done"), ("unblock-codex", "idle"), ("unseen-codex", "idle")), 1)]
    state.write_text(json.dumps({"n": 10, "tabs": [], "agents": agents}))
    env = {"PATH": f"{HERE / 'fake-herdr'}:{os.environ['PATH']}", "FAKE_HERDR_STATE": str(state)}
    step("done delivered", *told(tell("done-codex", "hi", env, 5), 0, "delivered to done-codex"))
    step("unblocked delivered after a retry", *told(tell("unblock-codex", "hi", env, 5), 0, "after 1 retry"))
    step("unseen not delivered", *told(tell("unseen-codex", "hi", env, 5), 1, "never showed it"))
    step("empty not delivered", *told(tell("done-codex", " \n", env, 5), 1, "the text is empty"))


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        live()
    except RuntimeError as e:
        step("live", False, str(e))
    fake()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
