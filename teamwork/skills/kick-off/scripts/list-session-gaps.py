#!/usr/bin/env python3
"""usage: list-session-gaps.py [--from-dir <projects folder>] [--json] <name>...

Print per name and project folder its sessions, restarts (a further session of the same name in that folder), the hours
each restart cost and, apart,
its idle gaps over 30 minutes inside a session (a wait for the owner, not a restart). A name with no transcript
prints "no session record". The default folder is ~/.claude/projects; `--json` prints the rows for the estimator."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import session_gaps  # noqa: E402


def main(argv):
    root, as_json = pathlib.Path.home() / ".claude" / "projects", False
    while argv and argv[0].startswith("--"):
        if argv[0] == "--from-dir" and len(argv) > 1:
            root, argv = pathlib.Path(argv[1]), argv[2:]
        elif argv[0] == "--json":
            as_json, argv = True, argv[1:]
        else:
            sys.exit(__doc__)
    if not argv:
        sys.exit(__doc__)
    rows = session_gaps.summaries(root, argv)
    if as_json:
        print(json.dumps(rows))
        return
    print("worker\tproject\tsessions\trestarts\trestart hours\tidle gaps")
    for name in argv:
        for r in [r for r in rows if r["worker"] == name] or [None]:
            if r is None:
                print(f"{name}\tno session record")
            else:
                hours = ",".join(f"{h:.1f}" for h in r["restart_hours"]) or "-"
                print(f"{name}\t{r['project']}\t{r['sessions']}\t{r['restarts']}\t{hours}\t{r['idle_gaps']}")


if __name__ == "__main__":
    main(sys.argv[1:])
