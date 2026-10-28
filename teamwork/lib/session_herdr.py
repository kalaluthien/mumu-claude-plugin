"""herdr as the session port's adapter: each session is a herdr agent in a pane, shown by a tab, and a team's tabs share one workspace."""
import json
import os
import subprocess
import time

from json_command import run

LOOK = "herdr agent read {}"
EMPTY = "herdr lists no agent; run it inside herdr."
NEEDS = ("herdr",)
POLL = 1.0


def sessions(session_id=None):
    """Every live agent, and this session's own: the one herdr lists with its session id, since herdr may move a pane and the shell's
    HERDR_PANE_ID stays as it started; else its pane's, unless the pane runs another session, as a worker's child does."""
    listed = (run("herdr", "agent", "list") or {}).get("result", {}).get("agents", [])
    session_id = session_id or os.environ.get("CLAUDE_CODE_SESSION_ID")
    by_id = next((live for live in listed if session_id and (live.get("agent_session") or {}).get("value") == session_id), None)
    if by_id:
        return listed, by_id
    me = next((live for live in listed if live.get("pane_id") == os.environ.get("HERDR_PANE_ID")), {})
    own = not session_id or (me.get("agent_session") or {}).get("value") in (None, "", session_id)
    return listed, me if own else {}


def agent(name):
    return next((live for live in sessions()[0] if live.get("name") == name), None)


def screen(pane):
    return subprocess.run(["herdr", "agent", "read", pane, "--source", "visible"], capture_output=True, text=True).stdout


def tabs(workspace):
    return (run("herdr", "tab", "list", "--workspace", workspace) or {}).get("result", {}).get("tabs", [])


def herdr(*argv):
    out = run("herdr", *argv)
    if out is None:
        raise RuntimeError(f"herdr {' '.join(argv[:2])} failed")
    return out["result"]


def open_tab(workspace, cwd, label):
    return herdr("tab", "create", "--workspace", workspace, "--cwd", cwd, "--label", label, "--no-focus")["root_pane"]


def open_workspace(cwd, label):
    return herdr("workspace", "create", "--cwd", cwd, "--label", label, "--no-focus")["root_pane"]


def rename(place, name):
    run("herdr", "tab", "rename", place["tab_id"], name)
    run("herdr", "pane", "rename", place["pane_id"], name)


def start(name, pane, kind, argv, timeout):
    deadline = time.time() + timeout
    while True:
        process = subprocess.run(["herdr", "agent", "start", name, "--kind", kind, "--pane", pane, "--", *argv], capture_output=True, text=True)
        out = process.stdout + process.stderr
        if not process.returncode or '"agent_not_ready"' in out:  # not ready: the trust dialog holds it
            return
        if '"agent_pane_busy"' not in out or time.time() >= deadline:  # busy: the shell is still starting
            raise RuntimeError(f"herdr agent start: {(process.stderr or process.stdout).strip()}")
        time.sleep(POLL)


def prompt(pane, text):
    """None once herdr took the text, else its error code, such as `agent_blocked` for a session at a tool prompt."""
    process = subprocess.run(["herdr", "agent", "prompt", pane, text], capture_output=True, text=True)
    if not process.returncode:
        return None
    try:
        return json.loads(process.stdout)["error"]["code"]
    except (ValueError, KeyError, TypeError):
        return (process.stderr or process.stdout).strip() or f"exit {process.returncode}"


def send_keys(pane, *keys):
    run("herdr", "agent", "send-keys", pane, *keys)


def answer(pane, choice):
    herdr("pane", "send-text", pane, choice)  # send-keys Enter leaves the prompt open


def wait_idle(name, timeout):
    # a session that finished a turn is `done`, for which `--until idle` alone never returns
    argv = ["herdr", "agent", "wait", name, "--until", "idle", "--until", "done", "--timeout", str(int(timeout * 1000))]
    return subprocess.run(argv, capture_output=True).returncode == 0


def close(session):
    last = len(tabs(session["workspace_id"])) <= 1
    run("herdr", *(("workspace", "close", session["workspace_id"]) if last else ("tab", "close", session["tab_id"])))
    return "workspace" if last else "tab"
