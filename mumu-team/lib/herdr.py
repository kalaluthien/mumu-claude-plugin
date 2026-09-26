"""Every `herdr` command mumu-team runs, each raising `RuntimeError` when herdr fails or prints what cannot be read."""
import json
import time

from gh import run


def _result(*argv):
    try:
        return json.loads(run("herdr", *argv))["result"]
    except (ValueError, KeyError, TypeError) as e:
        raise RuntimeError(f"herdr {' '.join(argv[:2])}: unreadable output ({e})") from e


def listed(kind):
    """herdr's `agent`, `pane` or `tab` list: the one reader of `herdr agent list`."""
    return _result(kind, "list")[kind + "s"]


def agent(name):
    return next((a for a in listed("agent") if a.get("name") == name), None)


def open_tab(cwd, label, *flags):
    """The root pane of a new tab, with herdr's `flags` such as `--env` or `--no-focus`."""
    return _result("tab", "create", "--cwd", str(cwd), "--label", label, *flags)["root_pane"]["pane_id"]


def close_tab(tab):
    run("herdr", "tab", "close", tab)


def screen(pane):
    return run("herdr", "agent", "read", pane, "--lines", "40")


def keys(pane, *names):
    run("herdr", "agent", "send-keys", pane, *names)


def prompt(pane, text):
    run("herdr", "agent", "prompt", pane, text)


def launch(name, pane, claude_args, timeout, poll):
    """Start Claude as agent `name` in `pane`, answering the folder-trust dialog, and return once it is ready for a prompt."""
    deadline = time.time() + timeout
    while True:
        try:
            run("herdr", "agent", "start", name, "--kind", "claude", "--pane", pane, "--", *claude_args)
            break
        except RuntimeError as e:
            if '"agent_not_ready"' in str(e):  # the trust dialog
                break
            if '"agent_pane_busy"' not in str(e) or time.time() >= deadline:
                raise
        time.sleep(poll)
    while time.time() < deadline:
        a = agent(name)
        if a and a.get("interactive_ready") and a.get("agent_status") != "blocked":
            return
        if "Yes, I trust this folder" in screen(pane):
            keys(pane, "down", "enter")
        time.sleep(poll)
    raise RuntimeError(f"{name} not ready after {timeout:g}s; see `herdr agent read {pane}`")
