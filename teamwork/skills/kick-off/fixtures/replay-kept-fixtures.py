#!/usr/bin/env python3
"""Run the repository check and every scenario that teamwork keeps, and print `PASS` as the last line when all pass, else `FAIL <command>` for each that fails.

usage: replay-kept-fixtures.py

The scenarios run at once, each in its own temporary folder, so the whole run takes as long as the slowest. A scenario that starts a real Claude Code session, such as probe-tell-session.py, is left out since it needs a live herdr."""
import concurrent.futures
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
SKILL = "teamwork/skills/kick-off/fixtures/"
HOOKS = "teamwork/hooks/fixtures/"
LANDING_CASES = ("pushes", "push-refused", "no-gh", "no-origin", "dirty-base")
COMMANDS = [
    ["python3", ".github/check-repository.py"],
    *[["python3", SKILL + name, *args] for name, args in [
        ("replay-board-scenario.py", []), ("replay-board-travel.py", []), ("replay-data-folder.py", []), ("replay-git-board.py", []),
        ("replay-input-form.py", []), ("replay-landing-scenario.py", []), ("replay-local-task.py", []),
        ("replay-remote-push.py", []), ("replay-team-scenarios.py", []), ("replay-heartbeat-lines.py", []),
        ("compare-session-calls.py", []),
        ("replay-task-decisions.py", ["--board", "git"]), ("replay-task-decisions.py", ["--board", "nodes"]),
        ("replay-task-graph.py", ["--board", "git"]), ("replay-task-graph.py", ["--board", "nodes"]),
        ("replay-board-writers.py", ["--case", "concurrent"]), ("replay-board-writers.py", ["--case", "unguarded"]),
        ("replay-heartbeat-tie.py", []), ("replay-heartbeat-tie.py", ["--mutant"]),
        *[("replay-additions.py", ["--case", case]) for case in ("path", "prefix", "writes")],
        *[("replay-body-diff.py", ["--case", case]) for case in ("newline", "exact", "mismatch", "misordered")],
        *[("replay-goal-path.py", ["--case", case]) for case in ("refuse", "teach", "old")],
        *[("replay-goal-write.py", ["--case", case]) for case in ("task", "shared", "other")],
        *[("replay-criterion-names.py", ["--case", case]) for case in ("gate", "open")],
        *[("replay-local-landing.py", ["--case", case]) for case in LANDING_CASES],
    ]],
    *[["python3", HOOKS + "replay-cd-refusal.py", "--case", case] for case in ("git", "path", "subshell")],
    *[["bun", HOOKS + "render-task-pane.ts", SKILL + "deep-" + kind + "-nodes.json"] for kind in ("task", "decision")],
    ["bun", HOOKS + "render-empty-pane.ts"],
]


def run(command):
    done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    return None if done.returncode == 0 else "FAIL " + " ".join(command)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        failures = [line for line in pool.map(run, COMMANDS) if line]
    print("\n".join(failures + ["FAIL" if failures else "PASS"]))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
