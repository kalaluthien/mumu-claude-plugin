#!/usr/bin/env python3
"""Check that check-criteria.py refuses a Goal that names no flow of its changed part and teaches the fix, and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-goal-path.py --case <name>
- refuse: a Goal that names only its changed part, an empty `Path:` line, `Path: none`, a sentence naming no labeled party, labels naming nobody, values that say nobody is affected or are unknown, blank values and a form blank left beside a filled item are refused with a `goal:` line, and a Goal with a `Path:` line holding a labeled caller, step or reader passes, as a bare line, a bullet or a bold label
- teach: the refusal cites Scope the path, and the `Path:` form it prints, with its placeholders filled by words, makes the refused Goal pass
- old: a Goal with no path passes under a task number below the Goal cut-off and is refused at it
- count: print how many of this repository's open Goals the check would refuse, as `would refuse <n> of <m> open Goals`, then `PASS`"""
import json
import pathlib
import re
import subprocess
import sys

CHECK = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check-criteria.py"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import issue_state  # noqa: E402

CRITERION = "1. [check] **The probe prints PASS when it runs**: `python3 probe.py` prints `PASS`; on base `FAIL`.\n"
PART_ONLY = "## Goal\n\nChange the heartbeat hook so it lists each worker's open task.\n\n## Definition of done\n\n" + CRITERION
NEWER = 99999


def lint(body, *flags):
    return subprocess.run([sys.executable, str(CHECK), *flags, "-"], input=body, capture_output=True, text=True)


def with_path(line):
    return PART_ONLY.replace("task.\n", "task.\n\n" + line + "\n", 1)


def case_refuse():
    refused = {"part only": PART_ONLY, "empty Path": with_path("Path:"), "Path: none": with_path("Path: none"),
               "a bare part name": with_path("Path: the heartbeat hook"),
               "the unfilled form": with_path("Path: caller: <caller>; before: <step before>; after: <step after>; meets: <who sees the result>"),
               "a sentence of the part's own work": with_path("Path: a.py runs faster after the change to imports"),
               "no flow said": with_path("Path: none, the user sees no result of it"),
               "labels naming nobody": with_path("Path: caller: none; meets: no one"),
               "values that say nobody is affected": with_path("Path: caller: nothing calls it; before: no step; after: none yet; meets: no one reads it"),
               "unknown parties": with_path("Path: caller: unknown; meets: TBD"),
               "blank values": with_path("Path: caller: ; meets: "),
               "a blank left beside a filled item": with_path("Path: caller: git; before: <step before>; meets: the agent")}
    for name, body in refused.items():
        done = lint(body)
        if done.returncode != 1 or not done.stdout.startswith("goal: "):
            return f"a Goal with {name} was not refused by a goal line: exit {done.returncode}, {done.stdout!r}"
    for line in ("Path: caller: the session start; after: the board write; meets: the owner in the pane",
                 "- Path: caller: the manager session; after: the release script; meets: maintainers on GitHub",
                 "- **Path**: before: each route of the manager",
                 "Path: caller: none; after: the nightly job, feeding the report builder",
                 "Path: caller: nobody calls it directly but cron; meets: native client",
                 "Path: caller: no-code scheduler; after: navigation pane"):
        done = lint(with_path(line))
        if done.returncode or done.stdout:
            return f"a Goal with `{line}` was refused: exit {done.returncode}, {done.stdout!r}"
    return None


def case_teach():
    done = lint(PART_ONLY)
    if done.returncode != 1 or "Scope the path" not in done.stdout:
        return f"the refusal does not cite Scope the path: exit {done.returncode}, {done.stdout!r}"
    form = re.search(r"`(Path: [^`]*)`", done.stdout)
    if not form:
        return f"the refusal prints no `Path:` form: {done.stdout!r}"
    words = iter(["the session start", "the board write", "the pane draw", "the owner"])
    fixed = re.sub(r"<[^>]*>", lambda _: next(words, "the reader"), form.group(1))
    again = lint(with_path(fixed))
    if again.returncode or again.stdout:
        return f"the Goal fixed by `{fixed}` was still refused: exit {again.returncode}, {again.stdout!r}"
    return None


def open_goals():
    common = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=True).stdout.strip()
    git = ["git", f"--git-dir={common}"]
    tree = subprocess.run([*git, "ls-tree", "--name-only", "-r", "refs/teamwork-blackboard"], capture_output=True, text=True, check=True).stdout.split()
    show = lambda path: subprocess.run([*git, "show", f"refs/teamwork-blackboard:{path}"], capture_output=True, text=True).stdout
    for path in tree:
        if path.endswith("issue.json") and str(json.loads(show(path)).get("state", "")).lower() == "open":
            body = show(path.replace("issue.json", "body.md"))
            if issue_state.sections(body).get("goal") is not None:
                yield body


def case_old():
    if lint(PART_ONLY, "--task", "1").returncode:
        return "a Goal with no path was refused under task 1, below the cut-off"
    if lint(PART_ONLY, "--task", str(NEWER)).returncode != 1:
        return f"a Goal with no path passed under task {NEWER}, above the cut-off"
    return None


def case_count():
    bodies = list(open_goals())
    refused = sum(any(line.startswith("goal: ") for line in lint(body).stdout.splitlines()) for body in bodies)
    print(f"would refuse {refused} of {len(bodies)} open Goals")
    return None


CASES = {"refuse": case_refuse, "teach": case_teach, "old": case_old, "count": case_count}


def main(args):
    if len(args) != 2 or args[0] != "--case" or args[1] not in CASES:
        print(__doc__, file=sys.stderr)
        return 2
    why = CASES[args[1]]()
    if why:
        print(f"FAIL: {why}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
