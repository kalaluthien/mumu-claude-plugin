#!/usr/bin/env python3
"""Close this Dreamer's own herdr tab once its turn ends, and print what happened.

usage: close-dreamer.py

Run as the last step of a dream. It reads this pane from HERDR_PANE_ID and closes the tab only when a herdr agent named
`*-dreamer` holds that pane; any other pane, or no herdr, closes nothing and says so. The close runs detached and waits
until the agent stops working, so the Dreamer's final report reaches the owner first. CLOSE_DREAMER_TIMEOUT (default
3600) bounds that wait in seconds.
"""
import json
import os
import subprocess
import sys
import time

TIMEOUT = float(os.environ.get("CLOSE_DREAMER_TIMEOUT", 3600))


def herdr(*words):
    """herdr's `result` object for these words, {} when herdr cannot run or replies with no object."""
    try:
        result = subprocess.run(["herdr", *words], capture_output=True, text=True, errors="replace", timeout=60)
        reply = json.loads(result.stdout)
    except (OSError, ValueError, RecursionError, subprocess.SubprocessError):
        return {}
    value = reply.get("result") if isinstance(reply, dict) else None
    return value if isinstance(value, dict) else {}


def own_dreamer(pane):
    """The herdr agent named `*-dreamer` that holds this pane, else None."""
    for agent in herdr("agent", "list").get("agents") or []:
        if isinstance(agent, dict) and agent.get("pane_id") == pane and str(agent.get("name") or "").endswith("-dreamer"):
            return agent
    return None


def close_when_idle(pane):
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        agent = own_dreamer(pane)
        if not agent:
            return
        if agent.get("agent_status") != "working" and agent.get("tab_id"):
            herdr("tab", "close", agent["tab_id"])
            return
        time.sleep(1)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    pane = os.environ.get("HERDR_PANE_ID")
    agent = own_dreamer(pane) if pane else None
    if not agent:
        print("closed nothing: this pane is not a herdr agent named *-dreamer")
        return 0
    if os.environ.get("CLOSE_DREAMER_DETACHED"):
        close_when_idle(pane)
    else:  # detached, so the wait outlives the Bash call that asked for it
        subprocess.Popen([sys.executable, __file__], env={**os.environ, "CLOSE_DREAMER_DETACHED": "1"}, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        print(f"{agent['name']} closes its tab once this turn ends")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
