#!/usr/bin/env python3
"""usage: list-session-gaps.py [--from-dir <projects folder>] [--json] <name>...

Print per name and project folder its sessions, restarts (a further session of the same name in that folder), the hours
each restart cost and, apart,
its idle gaps over 30 minutes inside a session (a wait for the owner, not a restart). A name with no transcript
prints "no session record". The default folder is the Claude config folder's projects; `--json` prints the rows for the estimator."""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import claude_config  # noqa: E402
import session_gaps  # noqa: E402


def main(argv):
    parser = argparse.ArgumentParser(usage=argparse.SUPPRESS, description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-dir", type=pathlib.Path, default=claude_config.folder() / "projects")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("names", nargs="+")
    opt = parser.parse_args(argv)
    rows = session_gaps.summaries(opt.from_dir, opt.names)
    if opt.json:
        print(json.dumps(rows))
        return
    print("worker\tproject\tsessions\trestarts\trestart hours\tidle gaps")
    for name in opt.names:
        for r in [r for r in rows if r["worker"] == name] or [None]:
            if r is None:
                print(f"{name}\tno session record")
            else:
                hours = ",".join(f"{h:.1f}" for h in r["restart_hours"]) or "-"
                print(f"{name}\t{r['project']}\t{r['sessions']}\t{r['restarts']}\t{hours}\t{r['idle_gaps']}")


if __name__ == "__main__":
    main(sys.argv[1:])
