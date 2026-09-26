"""Every `herdr` command mumu-team runs: its agents, panes and tabs, and a Claude session started in a pane.

Each call raises `RuntimeError` when herdr fails or prints what cannot be read.
"""
import json
import time

from command import run

TRUST = "Yes, I trust this folder"  # the folder-trust dialog, which defaults to "No, exit"


def _result(*argv):
    try:
        return json.loads(run("herdr", *argv))["result"]
    except (ValueError, KeyError, TypeError) as e:
        raise RuntimeError(f"herdr {' '.join(argv[:2])}: unreadable output ({e})") from e


def agents():
    """herdr's agents: the one reader of `herdr agent list`."""
    return _result("agent", "list")["agents"]


def agent(name):
    """herdr's entry for the agent `name`, or None."""
    return next((a for a in agents() if a.get("name") == name), None)


def panes():
    return _result("pane", "list")["panes"]


def tabs():
    return _result("tab", "list")["tabs"]


def open_tab(cwd, label, *flags):
    """The root pane of a new tab labelled `label` at `cwd`, with herdr's `flags` (`--env`, `--no-focus`)."""
    return _result("tab", "create", "--cwd", str(cwd), "--label", label, *flags)["root_pane"]["pane_id"]


def close_tab(tab):
    run("herdr", "tab", "close", tab)


def screen(pane, lines=40):
    return run("herdr", "agent", "read", pane, "--lines", str(lines))


def keys(pane, *names):
    run("herdr", "agent", "send-keys", pane, *names)


def prompt(pane, text):
    run("herdr", "agent", "prompt", pane, text)


def launch(name, pane, claude_args, timeout, poll):
    """Start Claude as the agent `name` in `pane`, answer the trust dialog, and return once it is ready for a prompt.

    `agent start` is retried while the new tab's shell is busy (`agent_pane_busy`);
    `agent_not_ready` means the trust dialog, answered `down enter`; any other error raises.
    """
    deadline = time.time() + timeout
    while True:
        try:
            run("herdr", "agent", "start", name, "--kind", "claude", "--pane", pane, "--", *claude_args)
            break
        except RuntimeError as e:
            if '"agent_not_ready"' in str(e):
                break
            if '"agent_pane_busy"' not in str(e) or time.time() >= deadline:
                raise RuntimeError(f"herdr agent start {name}: {e}") from e
        time.sleep(poll)
    while time.time() < deadline:
        a = agent(name)
        if a and a.get("interactive_ready") and a.get("agent_status") != "blocked":
            return
        if TRUST in screen(pane):
            keys(pane, "down", "enter")
        time.sleep(poll)
    raise RuntimeError(f"{name} not ready after {timeout:g}s; see `herdr agent read {pane}`")
