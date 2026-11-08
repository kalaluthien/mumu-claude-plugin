#!/usr/bin/env python3
"""Open two scratch herdr tabs, one a fake `*-dreamer` agent and one not, run close-dreamer.py from each, and print `PASS`
when only the Dreamer's tab is gone, else `FAIL` with the reason.

usage: probe-close-dreamer.py"""
import json
import os
import pathlib
import subprocess
import sys
import time

CLOSE = str(pathlib.Path(__file__).resolve().parent.parent / "scripts/close-dreamer.py")


def herdr(*words):
    result = subprocess.run(["herdr", *words], capture_output=True, text=True)
    return json.loads(result.stdout)["result"] if result.stdout.strip() else {}


def scratch_tab(workspace, label):
    root = herdr("tab", "create", "--workspace", workspace, "--label", label, "--no-focus")["root_pane"]
    herdr("pane", "report-agent", "--source", "probe", "--agent", "claude", "--state", "idle", root["pane_id"])
    herdr("agent", "rename", root["pane_id"], label)
    return root["pane_id"], root["tab_id"]


def tabs():
    return {tab["tab_id"] for tab in herdr("tab", "list")["tabs"]}


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    workspace = herdr("pane", "get", os.environ["HERDR_PANE_ID"])["pane"]["workspace_id"]
    dreamer_pane, dreamer_tab = scratch_tab(workspace, "probe-dreamer")
    other_pane, other_tab = scratch_tab(workspace, "probe-helper")
    try:
        said = subprocess.run([sys.executable, CLOSE], env={**os.environ, "HERDR_PANE_ID": other_pane}, capture_output=True, text=True).stdout
        subprocess.run([sys.executable, CLOSE], env={**os.environ, "HERDR_PANE_ID": dreamer_pane}, capture_output=True, text=True)
        time.sleep(4)
        left = tabs()
        if "closed nothing" not in said or other_tab not in left:
            print(f"FAIL: a pane not named *-dreamer was closed or did not say it closed nothing: {said!r}")
        elif dreamer_tab in left:
            print("FAIL: the Dreamer's tab is still open")
        else:
            print("PASS")
    finally:
        for tab in (dreamer_tab, other_tab):
            if tab in tabs():
                herdr("tab", "close", tab)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
