#!/usr/bin/env python3
"""Check that the watch follows held work, on a temporary git board and the fake herdr beside this file. Print `ok <case>` or `fail <case>: <detail>` per case,
then `PASS` or `FAIL`, and exit 1 on any failure:
- `warned`: `start-session.py` of a worker whose manager has no heartbeat process under its session id warns that the heartbeat is not running;
- `quiet`: the same start with a heartbeat process listed under that id prints no such warning;
- `part-held`: a part its parent's holder names in the parent's Definition of done is held by that holder;
- `part-other`: a part the manager, who does not hold the parent, names in it stays unheld.

usage: replay-watch-held.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = ROOT / "skills" / "kick-off" / "scripts"
MANAGER_SESSION = "sess-manager"
BODY = ("Hold the parts.\n\n## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints ok; meets: the caller's need.\n\n"
        "## Definition of done\n\nLast line.\n")
results = {}


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[-900:]}", flush=True)
    results[name] = ok


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="watch-held-"))
    repository, state = work / "repo", work / "herdr.json"
    repository.mkdir()
    (work / "ps").mkdir()
    listed = work / "heartbeat.txt"
    stand_in_ps = work / "ps" / "ps"
    stand_in_ps.write_text(f'#!/bin/sh\ncase "$*" in *-E*) cat "{listed}";; *) exec /bin/ps "$@";; esac\n')
    stand_in_ps.chmod(0o755)
    environment = {**os.environ, **replay_probe.IDENTITY, "CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_GLOBAL": str(work / "gitconfig"),
                   "TEAMWORK_FAKE_HERDR_STATE": str(state), "TEAMWORK_FAKE_HERDR_LOG": str(work / "log"), "TEAMWORK_START_SESSION_TIMEOUT": "3",
                   "PATH": f"{work / 'ps'}:{HERE / 'fake-herdr'}:{os.environ['PATH']}"}
    environment.pop("CLAUDE_CODE_SESSION_ID", None)
    replay_probe.write_git_config(work)
    for argv in (["init", "-q", "-b", "main"], ["commit", "-q", "--allow-empty", "-m", "start"]):
        subprocess.run(["git", *argv], cwd=repository, check=True, env=environment, capture_output=True)
    agents = [{"name": name, "pane_id": f"w1:p{pane}", "tab_id": f"w1:t{pane}", "workspace_id": "w1", "agent": "claude", "agent_status": "working", "interactive_ready": True,
               **({"agent_session": {"value": MANAGER_SESSION}} if name == "w-manager" else {})} for name, pane in (("w-manager", 1), ("w-worker", 2))]
    state.write_text(json.dumps({"n": 20, "agents": agents, "tabs": [{"tab_id": each["tab_id"], "workspace_id": "w1", "label": each["name"]} for each in agents]}))

    def start(name):
        argv = [sys.executable, str(SCRIPTS / "start-session.py"), name, str(work), f"worker {name} manager w-manager https://example.com/1", "--model", "haiku", "--effort", "medium"]
        return subprocess.run(argv, cwd=work, env=environment, capture_output=True, text=True).stderr

    listed.write_text("")
    step("warned", "heartbeat of the manager" in start("w-new-worker"), "no warning")
    listed.write_text(f"123 python3 /x/monitors/print-team-gaps.py CLAUDE_CODE_SESSION_ID={MANAGER_SESSION} HOME=/x\n")
    step("quiet", "heartbeat of the manager" not in start("w-third-worker"), "warned")

    def use(pane, *argv):
        pane_environment = {**environment, "HERDR_PANE_ID": pane}
        done = subprocess.run(replay_probe.as_pane([SCRIPTS / "use-board.py", *argv], pane, pane_environment, work / "stand-in"), cwd=repository, env=pane_environment,
                              capture_output=True, text=True)
        return done.stdout.strip() + done.stderr

    def filed(title):
        return use("w1:p1", "file", "--title", title, "--body", str(replay_probe.write_text(work, "body.md", BODY)), "--label", "scope:x").rsplit("/", 1)[-1].removesuffix(".json")

    def holders(number):
        return use("w1:p1", "read", number).split("holders:")[1].splitlines()[0].strip()

    for case, pane, label in (("part-held", "w1:p2", "held"), ("part-other", "w1:p1", "other")):
        parent, part = filed(f"Split the {label} task"), filed(f"Do a {label} part")
        use("w1:p1", "decide", parent, "--decision", "w-worker holds this.", "--holders", "w-worker")
        body = use("w1:p1", "read", parent, "--body")
        sha = use("w1:p1", "read", parent).split("body sha:")[1].split()[0]
        edited = replay_probe.write_text(work, f"{label}.md", body.rstrip("\n") + f"\n2. [task] #{part} Do a {label} part\n")
        edit = use(pane, "edit", parent, "--body", str(edited), "--reason", "name a part", "--base", sha)
        found = holders(part)
        step(case, found == ("w-worker" if label == "held" else ""), (found, edit))
    print("PASS" if all(results.values()) else "FAIL")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
