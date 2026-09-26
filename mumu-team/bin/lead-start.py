#!/usr/bin/env python3
"""Start a project's lead: its tab at the checkout's root, Claude as `--agent mumu-team:lead`, and its kickoff prompt.

usage: lead-start.py <checkout> [<goal-url> | --succeed <pane>] [-- <claude flags>]

A successor runs as `<repo>-lead-next` until it renames itself; otherwise it fails
while `<repo>-lead` is live. Prints `<name>@<pane>`.
"""
import argparse
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import herdr  # noqa: E402
import names  # noqa: E402
from gh import repo as repo_view  # noqa: E402

def main(argv):
    flags = []
    if "--" in argv:
        argv, flags = argv[:argv.index("--")], argv[argv.index("--") + 1:]
    parser = argparse.ArgumentParser(prog="lead-start.py", allow_abbrev=False)
    parser.add_argument("checkout")
    parser.add_argument("goal", nargs="?")
    parser.add_argument("--succeed")
    a = parser.parse_args(argv)
    if a.goal and a.succeed:
        parser.error("a goal url or --succeed, not both")
    succeed = a.succeed
    try:
        repo = names.checkout(a.checkout)
        lead = names.lead(repo_view("name", repo))
        if not succeed and herdr.agent(lead):
            raise RuntimeError(f"{lead} is already live; prompt it instead")
        name = lead + "-next" if succeed else lead
        prompt = "/mumu-team:kickoff" + (f" succeed {succeed}" if succeed else f" see {a.goal}" if a.goal else "")
        pane = herdr.open_tab(repo, name)
        timeout, poll = float(os.environ.get("LEAD_START_TIMEOUT", 600)), float(os.environ.get("LEAD_START_POLL", 1))
        herdr.launch(name, pane, ["--name", lead, "--agent", "mumu-team:lead"] + (flags or ["--model", "opus", "--effort", "medium"]), timeout, poll)
        herdr.prompt(pane, prompt)
    except RuntimeError as e:
        sys.exit(f"lead-start.py: {e}")
    print(f"{name}@{pane}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
