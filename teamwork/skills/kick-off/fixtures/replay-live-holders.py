#!/usr/bin/env python3
"""Run the holder and close paths on the git board in a temporary repository, with the fake herdr beside this file, and print `PASS` as the last
line when every case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-live-holders.py [--case <name>]
- stale-holder: a task held by a session herdr no longer lists reads `holders:  (was <name>)` and waits on `no holder`, and the pane row shows no holder;
  with herdr giving no list, `read` and the pane show the recorded holder
- close-waiting: `close-session.py` of a worker whose task holds an unanswered `BLOCKED:` exits 2, prints the task url and the question and leaves
  the worker live; once a `DECIDED:` answers it the close goes through; `--force` closes a worker whose question is still open
- close-shared-tab: `close-session.py` of a worker whose pane shares the one tab of its workspace with its manager's closes only the worker's pane,
  so the manager stays live
With no case, every case runs."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = HERE.parent / "scripts"
HOOKS = HERE.parents[2] / "hooks"
sh = replay_probe.sh


def setup():
    work = pathlib.Path(tempfile.mkdtemp(prefix="live-holders-"))
    replay_probe.write_git_config(work)
    kept = {key: value for key, value in os.environ.items() if not key.startswith(("TEAMWORK_", "HERDR_", "CLAUDE_CODE_SESSION"))}
    environment = {**kept, "PATH": f"{replay_probe.stub_gh(work)}:{HERE / 'fake-herdr'}:{os.environ['PATH']}", "HOME": str(work),
                   "CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_GLOBAL": str(work / "gitconfig"),
                   "TEAMWORK_FAKE_HERDR_STATE": str(work / "herdr.json"), "TEAMWORK_CLOSE_SESSION_TIMEOUT": "20"}
    repository = work / "repo"
    sh("git", "init", "-q", "-b", "main", repository, cwd=work, environment=environment)
    sh("git", "commit", "-q", "--allow-empty", "-m", "base", cwd=repository, environment=environment)
    return work, repository, environment


def team(work, *names):
    agents = [{"name": name, "pane_id": f"w1:p{number}", "tab_id": f"w1:t{number}", "workspace_id": "w1", "agent": "claude", "agent_status": "idle", "interactive_ready": True}
              for number, name in enumerate(names, 1)]
    (work / "herdr.json").write_text(json.dumps({"n": 10, "agents": agents, "tabs": [{"tab_id": each["tab_id"], "workspace_id": "w1", "label": each["name"]} for each in agents]}))


def live(work):
    return [agent["name"] for agent in json.loads((work / "herdr.json").read_text())["agents"]]


def use(environment, repository, *argv, check=True):
    return sh(sys.executable, SCRIPTS / "use-board.py", *argv, cwd=repository, environment=environment, check=check)


def held_task(work, repository, environment, title, holder):
    url = use(environment, repository, "file", "--title", title, "--body", replay_probe.write_text(work, "body.md", f"{title}.\n")).stdout.strip()
    use(environment, repository, "hold", url, "--holders", holder)
    return url


def shown(environment, repository, number):
    read = use(environment, repository, "read", number).stdout.splitlines()
    pane = sh(sys.executable, HOOKS / "list-task-board.py", "probe", "--json", cwd=repository, environment=environment)
    return read[1], read[2], next(row["holder"] for row in json.loads(pane.stdout) if row["number"] == int(number))


def case_stale_holder(work, repository, environment):
    held_task(work, repository, environment, "Probe the stale holder", "probe-gone")
    team(work, "probe-manager")
    got = shown(environment, repository, "1")
    if got != ("state: OPEN, no holder", "holders:  (was probe-gone)", ""):
        return replay_probe.fail(f"a dead holder shows as {got}")
    got = shown({**environment, "TEAMWORK_FAKE_HERDR_STATE": str(work / "missing.json")}, repository, "1")
    if got != ("state: OPEN, held", "holders: probe-gone", "probe-gone"):
        return replay_probe.fail(f"with herdr giving no list the holder shows as {got}")
    return 0


def case_close_waiting(work, repository, environment):
    url = held_task(work, repository, environment, "Probe the waiting worker", "probe-worker")
    other = held_task(work, repository, environment, "Probe the forced close", "probe-other")
    team(work, "probe-manager", "probe-worker", "probe-other")
    asked = use(environment, repository, "comment", url, "--blocked", "Which branch should the probe use now?").stdout.strip()
    use(environment, repository, "comment", other, "--blocked", "Which folder should the probe use now?")
    close = [sys.executable, SCRIPTS / "close-session.py"]
    refused = sh(*close, "probe-worker", cwd=repository, environment=environment, check=False)
    if refused.returncode != 2 or url not in refused.stdout or "Which branch should the probe use now?" not in refused.stdout or "probe-worker" not in live(work):
        return replay_probe.fail(f"a waiting worker's close exited {refused.returncode}, live {live(work)}: {refused.stdout[-300:]} {refused.stderr[-300:]}")
    use(environment, repository, "decide", url, "--decision", "Use the main branch for the probe.", "--by", "probe-manager", "--answers", asked)
    closed = sh(*close, "probe-worker", cwd=repository, environment=environment, check=False)
    if closed.returncode or "probe-worker" in live(work):
        return replay_probe.fail(f"an answered worker's close exited {closed.returncode}, live {live(work)}: {closed.stdout[-300:]} {closed.stderr[-300:]}")
    forced = sh(*close, "probe-other", "--force", cwd=repository, environment=environment, check=False)
    if forced.returncode or "probe-other" in live(work):
        return replay_probe.fail(f"a forced close exited {forced.returncode}, live {live(work)}: {forced.stdout[-300:]} {forced.stderr[-300:]}")
    return 0


def case_close_shared_tab(work, repository, environment):
    team(work, "probe-manager", "probe-worker")
    state = json.loads((work / "herdr.json").read_text())
    state["agents"][1]["tab_id"], state["tabs"] = "w1:t1", state["tabs"][:1]
    (work / "herdr.json").write_text(json.dumps(state))
    closed = sh(sys.executable, SCRIPTS / "close-session.py", "probe-worker", cwd=repository, environment=environment, check=False)
    if closed.returncode or live(work) != ["probe-manager"]:
        return replay_probe.fail(f"closing a worker that shares its manager's tab exited {closed.returncode}, live {live(work)}: {closed.stdout[-300:]} {closed.stderr[-300:]}")
    return 0


CASES = {"stale-holder": case_stale_holder, "close-waiting": case_close_waiting, "close-shared-tab": case_close_shared_tab}


def main(args):
    if args not in ([], *(["--case", name] for name in CASES)):
        print(__doc__, file=sys.stderr)
        return 2
    for name in [args[1]] if args else CASES:
        try:
            if CASES[name](*setup()):
                return 1
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            return replay_probe.fail(f"{name}: {str(e)[-400:]}")
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
