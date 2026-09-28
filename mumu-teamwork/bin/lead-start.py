#!/usr/bin/env python3
"""Start a project's lead: its tab at the checkout's root, Claude as `--agent mumu-teamwork:lead`, and its kickoff prompt.

`--replace` makes the calling session the one replaced: once the lead is live, a detached `worker-close.py --pane`
closes the caller's session and tab after the caller's turn ends."""
import argparse
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import herdr  # noqa: E402
import names  # noqa: E402
from github import repo as repo_view, run  # noqa: E402

DROPPED = {"--continue": 0, "-c": 0, "--resume": 1, "-r": 1, "--name": 1, "-n": 1, "--agent": 1}


def inherited(args):
    """The flags of the command line `args` a successor keeps: all but the program, `--continue`, `--resume`, `--name` and `--agent`."""
    words, kept = args.split()[1:], []
    while words:
        word = words.pop(0)
        flag = word.split("=", 1)[0]
        if flag in DROPPED:
            del words[:DROPPED[flag] if "=" not in word else 0]
        else:
            kept.append(word)
    return kept


def main(argv):
    flags = []
    if "--" in argv:
        argv, flags = argv[:argv.index("--")], argv[argv.index("--") + 1:]
    parser = argparse.ArgumentParser(prog="lead-start.py", allow_abbrev=False)
    parser.add_argument("checkout")
    one = parser.add_mutually_exclusive_group()  # a task url or --succeed, not both
    one.add_argument("task", nargs="?")
    one.add_argument("--succeed")
    one.add_argument("--replace", action="store_true")  # close the calling session once its turn ends
    parser.add_argument("--folder")  # a folder lead: `<folder>-lead`, with a task or none
    a = parser.parse_args(argv)
    if a.folder and a.succeed:
        parser.error("--folder: a successor keeps its original's name")
    caller = os.environ.get("HERDR_PANE_ID")
    if a.replace and not caller:
        parser.error("--replace: run it inside herdr, from the session to replace")
    try:
        repo = names.checkout(a.checkout)
        if a.succeed and not flags and os.environ.get("CLAUDE_PID"):  # the original's own flags, read from its process
            flags = inherited(run("ps", "-o", "args=", "-p", os.environ["CLAUDE_PID"]))
        lead = a.succeed and (herdr.agent(a.succeed, "pane_id") or {}).get("name") or names.lead(a.folder or repo_view("name", repo))  # a successor keeps its name
        if not a.succeed and herdr.agent(lead):
            raise RuntimeError(f"{lead} is already live; prompt it instead")
        name = lead + "-next" if a.succeed else lead
        prompt = "/mumu-teamwork:kickoff" + (f" succeed {a.succeed}" if a.succeed else f" see {a.task}" if a.task else "")
        pane = herdr.open_tab(repo, name)
        timeout, poll = float(os.environ.get("LEAD_START_TIMEOUT", 600)), float(os.environ.get("LEAD_START_POLL", 1))
        herdr.launch(name, pane, ["--name", lead, "--agent", "mumu-teamwork:lead"] + (flags or ["--model", "opus", "--effort", "medium"]), timeout, poll)
        herdr.prompt(pane, prompt)
        if a.replace:  # in its own session, so the Bash tool that ran this call does not reap it
            subprocess.Popen([sys.executable, str(pathlib.Path(__file__).resolve().parent / "worker-close.py"), "--pane", caller],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except RuntimeError as e:
        sys.exit(f"lead-start.py: {e}")
    print(f"{name}@{pane}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
