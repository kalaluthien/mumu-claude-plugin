#!/usr/bin/env python3
"""Start a project's lead in one call: its tab, its Claude session as `--agent mumu-team:lead`, the folder-trust dialog and its kickoff prompt.

usage: lead-start.py <checkout> [<goal-url> | --succeed <pane>] [-- <claude flags>]

The lead's name is `<repo>-lead`, `<repo>` the name `gh repo view` gives in
`<checkout>`, lowercased, each run of other than letters, digits, `-` and `_`
made one `-`, and cut to 22 characters, so `<repo>-lead-next` fits herdr's 32;
`<checkout>` is the checkout's root, made absolute, where its tab opens; any other path fails with 1. It is prompted
`/mumu-team:kickoff see <goal-url>` with a goal, `/mumu-team:kickoff` without
one (resume), and `/mumu-team:kickoff succeed <pane>` with `--succeed`, whose
tab and herdr agent are `<repo>-lead-next` until the successor renames itself.
Without `--succeed` it fails with 1 when `<repo>-lead` is already live, so a
project never gets a second lead. Claude runs with `--name <repo>-lead --agent
mumu-team:lead` and the flags after `--`, else `--model opus --effort medium`.
The tab opens focused, so the owner sees any start-up dialog it waits on.
Prints `<name>@<pane>`. `LEAD_START_TIMEOUT` (600) and `LEAD_START_POLL` (1)
are seconds.
"""
import importlib
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
ws = importlib.import_module("worker-start")

USAGE = "usage: lead-start.py <checkout> [<goal-url> | --succeed <pane>] [-- <claude flags>]"


def main(argv):
    flags = []
    if "--" in argv:
        argv, flags = argv[:argv.index("--")], argv[argv.index("--") + 1:]
    succeed = None
    if argv[1:2] == ["--succeed"]:
        if len(argv) != 3:
            print(USAGE, file=sys.stderr)
            return 2
        succeed = argv[2]
    elif not 1 <= len(argv) <= 2 or argv[1:] and argv[1].startswith("-"):
        print(USAGE, file=sys.stderr)
        return 2
    try:
        repo = ws.root(argv[0])
        name = ws.run("gh", "repo", "view", "--json", "name", "-q", ".name", cwd=repo).strip()
        lead = re.sub(r"[^a-z0-9_-]+", "-", name.lower())[:22].strip("-") + "-lead"
        if not succeed and ws.agent(lead):
            raise RuntimeError(f"{lead} is already live; prompt it instead")
        name = lead + "-next" if succeed else lead
        prompt = "/mumu-team:kickoff" + (f" succeed {succeed}" if succeed else f" see {argv[1]}" if len(argv) == 2 else "")
        pane = json.loads(ws.run("herdr", "tab", "create", "--cwd", repo, "--label", name))["result"]["root_pane"]["pane_id"]
        timeout, poll = float(os.environ.get("LEAD_START_TIMEOUT", 600)), float(os.environ.get("LEAD_START_POLL", 1))
        ws.start(name, pane, ["--name", lead, "--agent", "mumu-team:lead"] + (flags or ["--model", "opus", "--effort", "medium"]), timeout, poll)
        ws.await_ready(name, pane, timeout, poll)
        ws.run("herdr", "agent", "prompt", pane, prompt)
    except RuntimeError as e:
        print(f"lead-start.py: {e}", file=sys.stderr)
        return 1
    print(f"{name}@{pane}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
