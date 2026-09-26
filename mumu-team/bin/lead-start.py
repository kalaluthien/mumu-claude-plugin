#!/usr/bin/env python3
"""Start a project's lead in one call: its tab, its Claude session as `--agent mumu-team:lead`, the folder-trust dialog and its kickoff prompt.

usage: lead-start.py <checkout> [<goal-url> | --succeed <pane>] [-- <claude flags>]

The lead's name is `lib/names.py`'s `lead` of the name `gh repo view` gives in
`<checkout>`, short enough that `<repo>-lead-next` fits herdr's 32;
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
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import herdr  # noqa: E402
import names  # noqa: E402
from gh import repo as repo_view  # noqa: E402

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
        repo = names.checkout(argv[0])
        lead = names.lead(repo_view("name", repo))
        if not succeed and herdr.agent(lead):
            raise RuntimeError(f"{lead} is already live; prompt it instead")
        name = lead + "-next" if succeed else lead
        prompt = "/mumu-team:kickoff" + (f" succeed {succeed}" if succeed else f" see {argv[1]}" if len(argv) == 2 else "")
        pane = herdr.open_tab(repo, name)
        timeout, poll = float(os.environ.get("LEAD_START_TIMEOUT", 600)), float(os.environ.get("LEAD_START_POLL", 1))
        herdr.launch(name, pane, ["--name", lead, "--agent", "mumu-team:lead"] + (flags or ["--model", "opus", "--effort", "medium"]), timeout, poll)
        herdr.prompt(pane, prompt)
    except RuntimeError as e:
        print(f"lead-start.py: {e}", file=sys.stderr)
        return 1
    print(f"{name}@{pane}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
