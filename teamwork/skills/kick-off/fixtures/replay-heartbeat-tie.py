#!/usr/bin/env python3
"""Replay a manager's team losing its last worker and starting one again, on a temporary repository with a git board and the fake herdr beside this file, with the real heartbeat monitor running throughout, and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`.

Each cycle files an open task nobody holds while the manager has no worker (the second cycle with a sentinel alone), which the heartbeat must not print, then starts a worker, after which it must print that task's `route` line and again the first task's. A last case has the worker report on a root and leave at once, which the heartbeat must still feed to the manager.

usage: replay-heartbeat-tie.py [--only off | --only on | --mutant] [--verbose]
`--only off` judges the quiet cases alone; `--only on` judges the resuming cases, which count only after the quiet ones passed, since a monitor that never stopped has nothing to resume; with neither, all cases are judged.
`--mutant` runs the monitor with its tie to live workers cut out, and prints `PASS` only when the cases fail on that copy and pass on the real one, which shows the cases fail when the tie is removed."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

MONITOR = ROOT / "monitors" / "print-team-gaps.py"
TIE = "team_names.watching(me, listed)"  # the gate the mutant replaces
POLL = "0.3"
QUIET_SECONDS = 4  # about 13 polls, in which a monitor that still watched would print the task
RESUME_SECONDS = 30
VERBOSE = False


def agent(name, pane, status="idle"):
    return {"name": name, "pane_id": f"w1:p{pane}", "tab_id": f"w1:t{pane}", "workspace_id": "w1", "agent": "claude", "agent_status": status, "interactive_ready": True}


def trial(monitor):
    """The cases of one run of MONITOR as {case: (passed, what it saw)}."""
    work = pathlib.Path(tempfile.mkdtemp(prefix="heartbeat-tie-"))
    repository, state, log = work / "repo", work / "herdr.json", work / "monitor.log"
    environment = {**os.environ, **replay_probe.IDENTITY, "CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_GLOBAL": str(work / "gitconfig"),
                   "TEAMWORK_FAKE_HERDR_STATE": str(state), "PATH": f"{HERE / 'fake-herdr'}:{os.environ['PATH']}", "HERDR_PANE_ID": "w1:p1", "TEAMWORK_MONITOR_POLL": POLL}
    replay_probe.write_git_config(work)
    repository.mkdir()
    for argv in (["init", "-q", "-b", "main"], ["commit", "-q", "--allow-empty", "-m", "start"]):
        subprocess.run(["git", *argv], cwd=repository, check=True, env=environment, capture_output=True)

    def team(*agents):
        state.write_text(json.dumps({"n": 20, "agents": list(agents), "tabs": [{"tab_id": each["tab_id"], "workspace_id": "w1", "label": each["name"]} for each in agents]}))

    def file(title):
        body = replay_probe.write_text(work, "body.md", f"{title}.\n")
        done = subprocess.run([str(ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"), "file", title, str(body), "scope:x"], cwd=repository, env=environment, capture_output=True, text=True)
        if VERBOSE:
            print(f"$ use-board.py file {title}\n{done.stdout}{done.stderr}", file=sys.stderr)
        return done.stdout.strip().rsplit("/", 1)[-1].removesuffix(".json")

    def printed(number):
        return f"route #{number} " in log.read_text()

    def wait_for(number, seconds, again=None):
        """Whether the task's `route` line shows within SECONDS, and with AGAIN, a task printed before, that task's line shows more often than the count AGAIN holds."""
        deadline = time.time() + seconds
        done = lambda: printed(number) and (again is None or log.read_text().count(f"route #{again[0]} ") > again[1])
        while time.time() < deadline and not done():
            time.sleep(0.2)
        return done()

    manager = agent("x-manager", 1, "working")
    cases = {}
    team(manager, agent("t-worker", 2))
    first = file("Tie a first task")
    live = subprocess.Popen([sys.executable, str(monitor)], cwd=repository, env=environment, stdout=log.open("w"), stderr=subprocess.STDOUT)
    try:
        cases["start"] = (wait_for(first, RESUME_SECONDS), log.read_text())
        for cycle, others in ((1, []), (2, [agent("t-sentinel", 3)])):  # a sentinel is no worker, so it keeps the heartbeat off too
            before = log.read_text().count(f"route #{first} ")
            team(manager, *others)  # the last worker is gone
            time.sleep(1)  # more than a poll, so the monitor has seen the empty team
            number = file(f"Tie task {cycle}")
            time.sleep(QUIET_SECONDS)
            cases[f"off-{cycle}"] = (not printed(number), log.read_text())
            team(manager, *others, agent("t-worker", 2))  # a worker starts
            cases[f"on-{cycle}"] = (wait_for(number, RESUME_SECONDS, (first, before)), log.read_text())  # a gap printed before the stop prints again
        # the worker reports on a root and is gone before the next poll, which the one last read still feeds
        report = replay_probe.write_text(work, "report.md", "REPORTED: the tie root landed.\n")
        subprocess.run([str(ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"), "comment", first, str(report)], cwd=repository, env={**environment, "HERDR_PANE_ID": "w1:p2"}, capture_output=True)
        team(manager)
        deadline = time.time() + RESUME_SECONDS
        while time.time() < deadline and f"feed #{first} " not in log.read_text():
            time.sleep(0.2)
        cases["off-last-feed"] = (f"feed #{first} " in log.read_text(), log.read_text())
    finally:
        live.kill()
        live.wait()
    return cases


def verdict(cases, only):
    chosen = {name: result for name, result in cases.items() if only is None or name == "start" or name.startswith(only)}
    if only == "on":  # a monitor that never stopped passes every resuming case
        chosen |= {name: result for name, result in cases.items() if name.startswith("off")}
    return chosen


def show(cases):
    for name, (passed, saw) in cases.items():
        print(f"ok {name}" if passed else f"fail {name}: {saw.strip()}", flush=True)


def mutant_monitor():
    """A copy of the monitor with the tie replaced by a constant true, beside a link to the plugin's lib, which the monitor finds by its own path."""
    source = MONITOR.read_text()
    if TIE not in source:
        return None
    folder = pathlib.Path(tempfile.mkdtemp(prefix="heartbeat-mutant-"))
    (folder / "monitors").mkdir()
    (folder / "lib").symlink_to(ROOT / "lib")
    copy = folder / "monitors" / MONITOR.name
    copy.write_text(source.replace(TIE, "True"))
    return copy


def main(args):
    global VERBOSE
    flags = list(args)
    VERBOSE = "--verbose" in flags
    only = None
    if "--only" in flags:
        at = flags.index("--only")
        only = flags[at + 1] if at + 1 < len(flags) else None
        del flags[at:at + 2]
    flags = [flag for flag in flags if flag != "--verbose"]
    if only not in (None, "off", "on") or flags not in ([], ["--mutant"]) or flags and only:
        print(__doc__, file=sys.stderr)
        return 2
    if flags:
        copy = mutant_monitor()
        if copy is None:
            print(f"fail mutant: {MONITOR.name} holds no {TIE}, so nothing can be cut out")
            print("FAIL")
            return 1
        real, cut = trial(MONITOR), trial(copy)
        show(cut)
        ok = all(passed for passed, _ in real.values()) and not all(passed for passed, _ in cut.values())
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1
    chosen = verdict(trial(MONITOR), only)
    show(chosen)
    ok = all(passed for passed, _ in chosen.values())
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
