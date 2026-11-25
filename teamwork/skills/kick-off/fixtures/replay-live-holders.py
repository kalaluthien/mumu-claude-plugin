#!/usr/bin/env python3
"""Run the holder and close paths on the git board of a sandbox, and print `PASS` as the last
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
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = HERE.parent / "scripts"
HOOKS = HERE.parents[2] / "hooks"


def team(box, *names):
    box.herdr([replay_probe.agent(name, number) for number, name in enumerate(names, 1)])


def live(box):
    return [agent["name"] for agent in box.herdr_state()["agents"]]


def use(box, *argv, check=True, **variables):
    done = box.python(SCRIPTS / "use-board.py", *argv, **variables)
    if check and done.returncode:
        raise RuntimeError(f"use-board.py {' '.join(map(str, argv))}: {done.stdout}{done.stderr}")
    return done


def held_task(box, title, holder):
    url = use(box, "file", "--title", title, "--body", replay_probe.write_text(box.work, "body.md", f"{title}.\n")).stdout.strip()
    use(box, "hold", url, "--holders", holder)
    return url


def shown(box, number, **variables):
    read = use(box, "read", number, **variables).stdout.splitlines()
    pane = box.python(HOOKS / "list-task-board.py", "probe", "--json", **variables)
    return read[1], read[2], next(row["holder"] for row in json.loads(pane.stdout) if row["number"] == int(number))


def case_stale_holder(box):
    held_task(box, "Probe the stale holder", "probe-gone")
    team(box, "probe-manager")
    got = shown(box, "1")
    if got != ("state: OPEN, no holder", "holders:  (was probe-gone)", ""):
        return replay_probe.fail(f"a dead holder shows as {got}")
    got = shown(box, "1", TEAMWORK_FAKE_HERDR_STATE=box.work / "missing.json")
    if got != ("state: OPEN, held", "holders: probe-gone", "probe-gone"):
        return replay_probe.fail(f"with herdr giving no list the holder shows as {got}")
    return 0


def case_close_waiting(box):
    url = held_task(box, "Probe the waiting worker", "probe-worker")
    other = held_task(box, "Probe the forced close", "probe-other")
    team(box, "probe-manager", "probe-worker", "probe-other")
    asked = use(box, "comment", url, "--blocked", "Which branch should the probe use now?").stdout.strip()
    use(box, "comment", other, "--blocked", "Which folder should the probe use now?")
    refused = box.python(SCRIPTS / "close-session.py", "probe-worker")
    if refused.returncode != 2 or url not in refused.stdout or "Which branch should the probe use now?" not in refused.stdout or "probe-worker" not in live(box):
        return replay_probe.fail(f"a waiting worker's close exited {refused.returncode}, live {live(box)}: {refused.stdout[-300:]} {refused.stderr[-300:]}")
    use(box, "decide", url, "--decision", "Use the main branch for the probe.", "--by", "probe-manager", "--answers", asked)
    closed = box.python(SCRIPTS / "close-session.py", "probe-worker")
    if closed.returncode or "probe-worker" in live(box):
        return replay_probe.fail(f"an answered worker's close exited {closed.returncode}, live {live(box)}: {closed.stdout[-300:]} {closed.stderr[-300:]}")
    forced = box.python(SCRIPTS / "close-session.py", "probe-other", "--force")
    if forced.returncode or "probe-other" in live(box):
        return replay_probe.fail(f"a forced close exited {forced.returncode}, live {live(box)}: {forced.stdout[-300:]} {forced.stderr[-300:]}")
    return 0


def case_close_shared_tab(box):
    team(box, "probe-manager", "probe-worker")
    state = box.herdr_state()
    state["agents"][1]["tab_id"], state["tabs"] = "w1:t1", state["tabs"][:1]
    box.state.write_text(json.dumps(state))
    closed = box.python(SCRIPTS / "close-session.py", "probe-worker")
    if closed.returncode or live(box) != ["probe-manager"]:
        return replay_probe.fail(f"closing a worker that shares its manager's tab exited {closed.returncode}, live {live(box)}: {closed.stdout[-300:]} {closed.stderr[-300:]}")
    return 0


CASES = {"stale-holder": case_stale_holder, "close-waiting": case_close_waiting, "close-shared-tab": case_close_shared_tab}


def main(args):
    if args not in ([], *(["--case", name] for name in CASES)):
        print(__doc__, file=sys.stderr)
        return 2
    for name in [args[1]] if args else CASES:
        with replay_probe.scratch("live-holders-") as work:
            box = replay_probe.Sandbox(work)
            box.environment["TEAMWORK_CLOSE_SESSION_TIMEOUT"] = "20"
            try:
                if CASES[name](box):
                    return 1
            except RuntimeError as e:
                return replay_probe.fail(f"{name}: {str(e)[-400:]}")
    return replay_probe.Cases().finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
