#!/usr/bin/env python3
"""usage: list-session-gaps.py [--from-dir <projects folder>] [--json] <worker-name>...

Print per worker its sessions, restarts (a further session of the same name), the hours each restart cost and, apart,
its idle gaps over 30 minutes inside a session (a wait for the owner, not a restart). A worker with no transcript
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
    rows = {name: session_gaps.summary(root, name) for name in argv}
    if as_json:
        print(json.dumps([r for r in rows.values() if r]))
        return
    print("worker\tsessions\trestarts\trestart hours\tidle gaps")
    for name, r in rows.items():
        if r is None:
            print(f"{name}\tno session record")
        else:
            hours = ",".join(f"{h:.1f}" for h in r["restart_hours"]) or "-"
            print(f"{name}\t{r['sessions']}\t{r['restarts']}\t{hours}\t{r['idle_gaps']}")


if __name__ == "__main__":
    main(sys.argv[1:])
