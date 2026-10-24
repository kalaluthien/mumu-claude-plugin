#!/usr/bin/env python3
"""usage: probe-tell-session.py

Tell sessions by tell-session.py and print each case's outcome, comma-joined, or `failed: <case>` with what it printed.
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
ROOT = HERE.parents[2]
TELL, CLOSE = HERE.parent / "scripts" / "tell-session.py", HERE.parent / "scripts" / "close-session.py"
sys.path.insert(0, str(ROOT / "lib"))
import agent  # noqa: E402
import session  # noqa: E402

NAME = f"probe-tell-{os.getpid()}"
results = []


def tell(name, text, env=None, timeout=60):
    note = pathlib.Path(tempfile.mkstemp(suffix=".md")[1])
    note.write_text(text)
    p = subprocess.run([str(TELL), name, str(note)], env={**os.environ, "TELL_SESSION_TIMEOUT": str(timeout), **(env or {})}, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def case(label, outcome, expect_code, expect_text):
    code, out = outcome
    if code != expect_code or expect_text not in out:
        sys.exit(f"failed: {label}: exit {code}: {out}")
    results.append(label)


def until(test, seconds, what):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if test():
            return
        time.sleep(1)
    screen = [l for l in session.screen(session.agent(NAME)["pane_id"]).splitlines() if l.strip()][-8:] if session.agent(NAME) else []
    raise RuntimeError(f"{NAME} {what} after {seconds}s; its screen ended: {' | '.join(screen)}")


def live():
    folder = tempfile.mkdtemp(prefix="probe-tell-")
    place = session.open_tab(None, folder, NAME)
    session.rename(place, NAME)
    pane = place["pane_id"]
    try:
        session.start(NAME, pane, agent.KIND, ["--name", NAME, "--model", "haiku", "--effort", "low", "--permission-mode", "default", "--allowedTools", "Bash(sleep *)"], 60)
        trust, accept = agent.TRUST
        until(lambda: (trust in session.screen(pane) and session.send_keys(pane, *accept)) or ((session.agent(NAME) or {}).get("interactive_ready")
                      and (session.agent(NAME) or {}).get("agent_status") == "idle"), 90, "never became idle")
        case("idle delivered", tell(NAME, "Reply with the single word ONE."), 0, f"delivered to {NAME}")
        until(lambda: (session.agent(NAME) or {}).get("agent_status") in ("idle", "done"), 120, "never finished its first reply")
        session.prompt(pane, "Run the Bash command `sleep 25`, then reply with the single word TWO.")
        until(lambda: (session.agent(NAME) or {}).get("agent_status") == "working", 30, "never started its sleep")
        case("busy delivered after its turn", tell(NAME, "Reply with the single word THREE.", timeout=180), 0, "after its turn")
        until(lambda: (session.agent(NAME) or {}).get("agent_status") in ("idle", "done"), 120, "never finished its third reply")
        session.prompt(pane, f"Run the Bash command `touch {folder}/blocked`.")
        until(lambda: (session.agent(NAME) or {}).get("agent_status") == "blocked", 60, "never stopped at the tool prompt")
        case("blocked not delivered", tell(NAME, "Reply with the single word FOUR.", timeout=8), 1, "blocked at a tool prompt")
        session.send_keys(pane, "esc")
    finally:
        subprocess.run([str(CLOSE), NAME], env={**os.environ, "CLOSE_SESSION_TIMEOUT": "120"}, capture_output=True)


def fake():
    state = pathlib.Path(tempfile.mkstemp(prefix="fake-herdr-", suffix=".json")[1])
    agents = [{"name": n, "pane_id": f"w1:p{i}", "tab_id": f"w1:t{i}", "workspace_id": "w1", "agent": "codex", "agent_status": s, "interactive_ready": True}
              for i, (n, s) in enumerate((("done-codex", "done"), ("unblock-codex", "idle"), ("unseen-codex", "idle")), 1)]
    state.write_text(json.dumps({"n": 10, "tabs": [], "agents": agents}))
    env = {"PATH": f"{HERE / 'fake-herdr'}:{os.environ['PATH']}", "FAKE_HERDR_STATE": str(state)}
    case("done delivered", tell("done-codex", "hi", env, 5), 0, "delivered to done-codex")
    case("unblocked delivered after a retry", tell("unblock-codex", "hi", env, 5), 0, "after 1 retry")
    case("unseen not delivered", tell("unseen-codex", "hi", env, 5), 1, "never showed it")
    case("empty not delivered", tell("done-codex", " \n", env, 5), 1, "the text is empty")
    results.pop()  # a guard, not one of the receivers the printed line names


try:
    live()
except RuntimeError as e:
    sys.exit(f"failed: {e}")
fake()
print(", ".join(results))
