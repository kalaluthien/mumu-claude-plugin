#!/usr/bin/env python3
"""Start a project's lead: its tab at the checkout's root, Claude as `--agent mumu-team:lead`, and its kickoff prompt."""
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
    one = parser.add_mutually_exclusive_group()  # a goal url or --succeed, not both
    one.add_argument("goal", nargs="?")
    one.add_argument("--succeed")
    a = parser.parse_args(argv)
    try:
        repo = names.checkout(a.checkout)
        lead = a.succeed and (herdr.agent(a.succeed, "pane_id") or {}).get("name") or names.lead(repo_view("name", repo))  # a folder lead keeps its name
        if not a.succeed and herdr.agent(lead):
            raise RuntimeError(f"{lead} is already live; prompt it instead")
        name = lead + "-next" if a.succeed else lead
        prompt = "/mumu-team:kickoff" + (f" succeed {a.succeed}" if a.succeed else f" see {a.goal}" if a.goal else "")
        pane = herdr.open_tab(repo, name)
        timeout, poll = float(os.environ.get("LEAD_START_TIMEOUT", 600)), float(os.environ.get("LEAD_START_POLL", 1))
        herdr.launch(name, pane, ["--name", lead, "--agent", "mumu-team:lead"] + (flags or ["--model", "opus", "--effort", "medium"]), timeout, poll)
        herdr.prompt(pane, prompt)
    except RuntimeError as e:
        sys.exit(f"lead-start.py: {e}")
    print(f"{name}@{pane}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
