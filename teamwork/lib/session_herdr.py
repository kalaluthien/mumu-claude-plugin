"""herdr as the session port's adapter: each session is a herdr agent in a pane, shown by a tab, and a team's tabs share one workspace."""
import json
import os
import subprocess
import time

from json_command import run

LOOK = "herdr pane read {}"
EMPTY = "herdr lists no agent; run it inside herdr."
NEEDS = ("herdr",)
POLL = 1.0
# the shortest and the longest wait, in seconds, `herdr agent start --timeout` takes
START_WAIT = (3.001, 300)


# the latest names herdr listed, which `live_names` reuses for LIVE_SECONDS, since a reader composes every task of a board in one pass
LIVE_SECONDS = 2.0
_latest = {"at": None, "names": None}


def sessions(session_id=None):
    """Every live agent, and this session's own: the one herdr lists with its session id, since herdr may move a pane and the shell's
    HERDR_PANE_ID stays as it started; else its pane's, unless the pane runs another session, as a worker's child does."""
    listed = remember(run("herdr", "agent", "list"))
    session_id = session_id or os.environ.get("CLAUDE_CODE_SESSION_ID")
    by_id = next((live for live in listed if session_id and (live.get("agent_session") or {}).get("value") == session_id), None)
    if by_id:
        return listed, by_id
    me = next((live for live in listed if live.get("pane_id") == os.environ.get("HERDR_PANE_ID")), {})
    own = not session_id or (me.get("agent_session") or {}).get("value") in (None, "", session_id)
    return listed, me if own else {}


def remember(out):
    """The agents of a `herdr agent list` output, its names kept as the latest when herdr gave a list."""
    listed = (out or {}).get("result", {}).get("agents", [])
    if out is not None:
        _latest.update(at=time.monotonic(), names={live["name"] for live in listed if live.get("name")})
    return listed


def live_names():
    """The names of the live agents, from a list at most LIVE_SECONDS old, or None when herdr gave no list, such as outside herdr."""
    if _latest["at"] is None or time.monotonic() - _latest["at"] > LIVE_SECONDS:
        out = run("herdr", "agent", "list")
        remember(out) if out is not None else _latest.update(at=time.monotonic(), names=None)
    return _latest["names"]


def agent(name):
    return next((live for live in sessions()[0] if live.get("name") == name), None)


def screen(pane, styled=False):
    return subprocess.run(["herdr", "agent", "read", pane, "--source", "visible", *(["--ansi"] if styled else [])], capture_output=True, text=True).stdout


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
    limit = str(int(min(max(timeout, START_WAIT[0]), START_WAIT[1]) * 1000))
    while True:
        process = subprocess.run(["herdr", "agent", "start", name, "--kind", kind, "--pane", pane, "--timeout", limit, "--", *argv], capture_output=True, text=True)
        out = process.stdout + process.stderr
        if not process.returncode or '"agent_not_ready"' in out:  # not ready: the trust dialog holds it
            return
        if '"timeout"' in out:  # herdr stopped waiting and named nothing, while the agent may still come up in the pane
            return name_late(name, pane, timeout)
        if '"agent_pane_busy"' not in out or time.time() >= deadline:  # busy: the shell is still starting
            raise RuntimeError(f"herdr agent start: {(process.stderr or process.stdout).strip()}")
        time.sleep(POLL)


def name_late(name, pane, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if any(live.get("pane_id") == pane for live in sessions()[0]):
            herdr("agent", "rename", pane, name)
            return
        time.sleep(POLL)
    raise RuntimeError(f"no agent came up in pane {pane} within {2 * timeout:g}s")


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
    """The session's pane as one fresh `pane list` shows it, found by its name, which the pane keeps after its agent exits: None, closing
    nothing, when no pane bears that name, since another close of the same session already shut it and the ids read before the wait
    would then shut a neighbour, such as the workspace of a manager whose tab is the last one left.
    Only that pane while another pane shares its tab, or herdr lists no panes, since a tab close shuts every pane in it;
    else its tab, or its workspace when no other tab has a pane, judged from that same list."""
    out = run("herdr", "pane", "list")
    if out is None:
        run("herdr", "pane", "close", session["pane_id"])  # pane ids are never reused, so a stale one shuts nothing else
        return "pane"
    panes = out.get("result", {}).get("panes", [])
    named = [pane for pane in panes if pane.get("label") == session.get("name")]
    target = next((pane for pane in named if pane.get("pane_id") == session["pane_id"]), named[0] if named else None)
    if target is None:
        return None
    others = [pane for pane in panes if pane.get("workspace_id") == target["workspace_id"] and pane.get("pane_id") != target["pane_id"]]
    if any(pane.get("tab_id") == target["tab_id"] for pane in others):
        run("herdr", "pane", "close", target["pane_id"])
        return "pane"
    last = not others
    run("herdr", *(("workspace", "close", target["workspace_id"]) if last else ("tab", "close", target["tab_id"])))
    return "workspace" if last else "tab"
