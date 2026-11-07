#!/usr/bin/env python3
"""Start the Dreamer, the interactive Claude Code session a Workflow-off dream hands over to, in a new herdr tab of this
pane's workspace, with this same plugin, and print what happened.

usage: start-dreamer.py <data> <config> <home> <memory count> <memory limit> [<note>]

Its name is `<topic>-dreamer`, `<topic>` joining, in this order, `memory` when the memory count reached its limit,
`repeats` when <data>/dejavu is due and `habit` when <data>/habit is due. It starts none when none holds, outside herdr,
while a dreaming workflow runs on <data> (its lock, homework/lib/stamp.py), as when one of its own agents calls this, or
when a herdr session named `*-dreamer` is working or blocked, since its dream still runs; a finished one, idle or
done, gets the new dream under the new name instead, asking again what the owner left unanswered, since an unanswered
question is never recorded. <note> goes into the Dreamer's prompt.
"""
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import stamp  # noqa: E402

PLUGIN = pathlib.Path(__file__).resolve().parents[3]
CAUSES = (("repeats", "dejavu"), ("habit", "habit"))


def herdr(*words):
    result = subprocess.run(["herdr", *words], capture_output=True, text=True, timeout=180)
    try:
        return json.loads(result.stdout).get("result", {})
    except ValueError:
        return {"error": (result.stdout + result.stderr).strip()}


def main(args):
    if len(args) not in (5, 6) or not args[3].isdigit() or not args[4].isdigit():
        print(__doc__, file=sys.stderr)
        return 2
    data, config, home = (pathlib.Path(arg) for arg in args[:3])
    words = ["memory"] if int(args[3]) >= int(args[4]) else []
    words += [word for word, folder in CAUSES if stamp.due(data / folder)]
    if not words:
        print("not due: no dream to start")
        return 0
    name = "-".join(words) + "-dreamer"
    if stamp.running(data):
        print(f"held by a dreaming workflow running on {data} (its dream.lock is under {stamp.LOCK_HOURS} hours old); started none")
        return 0
    pane = os.environ.get("HERDR_PANE_ID")
    if not pane:
        print(f"no herdr here: started none; tell the owner to start {name} with this plugin")
        return 0
    dreamers = [agent for agent in herdr("agent", "list").get("agents", [])
                if str(agent.get("name") or "").endswith("-dreamer")]
    busy = [agent["name"] for agent in dreamers if agent.get("agent_status") in ("working", "blocked")]
    if busy:
        print(f"held by {busy[0]}: its dream still runs or waits at a prompt; started none")
        return 0
    if dreamers:
        new_pane, done = dreamers[0]["pane_id"], f"gave the dream to the finished {dreamers[0]['name']}, renamed {name},"
        herdr("agent", "rename", new_pane, name)
    else:
        workspace = herdr("pane", "get", pane).get("pane", {}).get("workspace_id")
        if not workspace:
            print(f"failed to start {name}: herdr knows no workspace of pane {pane}")
            return 1
        tab = herdr("tab", "create", "--workspace", workspace, "--cwd", os.getcwd(), "--label", name, "--no-focus")
        new_pane, done = tab.get("root_pane", {}).get("pane_id"), f"started {name}"
        started = herdr("agent", "start", name, "--kind", "claude", "--pane", new_pane, "--timeout", "120000", "--",
                        "--name", name, "--plugin-dir", str(PLUGIN)) if new_pane else {}
        if not started.get("agent"):
            print(f"failed to start {name}: {tab.get('error') or started.get('error') or started}")
            return 1
    prompt = (f"You are the Dreamer {name}. Use the homework:wrap-up skill: run its dream playbook, "
              f"{PLUGIN}/skills/wrap-up/references/dream.md, with <data> {data}, <config> {config} and <home> {home}. "
              + (args[5] if len(args) == 6 else ""))
    herdr("agent", "prompt", new_pane, prompt)
    print(f"{done} in pane {new_pane}; it runs the dream and asks the owner there")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
