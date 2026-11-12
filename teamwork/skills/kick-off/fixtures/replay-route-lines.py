#!/usr/bin/env python3
"""Replay a manager's `route` line for a held task whose worker started after the poll read the sessions, on a temporary repository with a git board and the fake herdr
beside this file, and print `ok <case>` or `fail <case>: <what it saw>` per case; exit 1 on any fail. Cases:
- started-late: no `route` line for a task held by a worker that started after the poll's first read, since the sessions are read again when the lines are made (#1365)
- read-failed: no `route` line when the read now lists no session at all, since the host failed to answer
- limit-dropped: the heartbeat has no `limit` line kind, which no playbook acts on
- idle-held: no `idle` line that says the worker holds nothing when a read now shows a task held
- idle-moved, blocked-moved, merged-held, holds-held, rebase-clean: no `idle`, `blocked`, `merged`, `holds nothing` or `rebase` line when a read now shows the worker working, the task held or the change clean, and the line when it does not
- unheld: a `route` line for a task no live worker holds, so the guard hides no real gap

usage: replay-route-lines.py
It prints `PASS` last when every case passed, else `FAIL`."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPTS = HERE.parent / "scripts"
work = pathlib.Path(tempfile.mkdtemp(prefix="route-lines-"))
repository = work / "repo"
STATE = work / "herdr.json"
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

os.environ.update({"CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_GLOBAL": str(work / "gitconfig"), **replay_probe.IDENTITY,
                   "TEAMWORK_FAKE_HERDR_STATE": str(STATE), "PATH": f"{HERE / 'fake-herdr'}:{os.environ['PATH']}", "HERDR_PANE_ID": "w1:p1"})
failed = []


def agent(name, pane, status):
    return {"name": name, "pane_id": f"w1:p{pane}", "tab_id": f"w1:t{pane}", "workspace_id": "w1", "agent": "claude", "agent_status": status, "interactive_ready": True}


def herdr(*agents):
    STATE.write_text(json.dumps({"n": 20, "agents": list(agents), "tabs": []}))
    return list(agents)


def use(*args):
    return subprocess.run([str(SCRIPTS / "use-board.py"), *map(str, args)], cwd=repository, capture_output=True, text=True).stdout.strip()


def file(title, holder=None):
    body = work / "body.md"
    body.write_text("Probe the route line.\n")
    number = use("file", title, body, "scope:x").rsplit("/", 1)[-1].removesuffix(".json")
    if holder:
        use("hold", number, holder)
    return int(number)


def manager_lines(kept, found=(), everything=(), prs=(), kind="route"):
    import board
    import team_gaps
    found, everything = [board.fresh(number) for number in found], [board.fresh(number) for number in everything]
    data = {"found": found, "everything": everything, "prs": list(prs), "outside": [], "feed": [], "links": [], "blockers": {}}
    out = team_gaps.manager_actions({"name": "x-manager", "workspace_id": "w1"}, kept, data, set())
    return [line for line in out or [] if line.startswith(kind)]


def route_lines(number, kept):
    return manager_lines(kept, [number], [number])


def step(name, ok, detail):
    print(f"ok {name}" if ok else f"fail {name}: {detail}", flush=True)
    if not ok:
        failed.append(name)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    repository.mkdir()
    for argv in (["init", "-q", "-b", "main"], ["commit", "-q", "--allow-empty", "-m", "start"]):
        subprocess.run(["git", *argv], cwd=repository, check=True)
    os.chdir(repository)
    import team_gaps
    team_gaps.tabs = lambda workspace: []
    manager = agent("x-manager", 1, "working")
    held = file("Probe a late worker", holder="late-worker")
    herdr(manager, agent("late-worker", 2, "working"))
    out = route_lines(held, [manager])
    step("started-late", not out, out)
    herdr()
    out = route_lines(held, [])
    step("read-failed", not out, out)
    free = file("Probe a free task")
    herdr(manager, agent("other-worker", 3, "working"))
    out = route_lines(free, [manager])
    step("unheld", len(out) == 1, out)
    prompt = "Do you want to proceed?\n\u276f 1. Yes\n  2. No\nEsc to cancel"
    for status, kind, screen in (("idle", "idle", ""), ("blocked", "blocked", prompt)):
        listed = [manager, {**agent("w-worker", 2, status), "screen": screen}]
        now = {**agent("w-worker", 2, status), "screen": screen}
        herdr(manager, now)
        shown = manager_lines(listed, kind=kind)
        herdr(manager, {**now, "agent_status": "working"})
        hidden = manager_lines(listed, kind=kind)
        step(f"{kind}-moved", len(shown) == 1 and not hidden, shown + hidden)
    herdr(manager, agent("i-worker", 4, "idle"))
    shown = manager_lines([manager, agent("i-worker", 4, "idle")], kind="idle")
    use("hold", file("Probe a task taken after the poll"), "i-worker")
    step("idle-held", len(shown) == 1 and not manager_lines([manager, agent("i-worker", 4, "idle")], kind="idle"), shown)
    pull = [{"number": 5, "headRefName": "m-worker", "mergedAt": "2026-11-04T00:00:00Z"}]
    listed = herdr(manager, agent("m-worker", 3, "working"))
    seen = manager_lines(listed, prs=pull, kind="merged")
    use("hold", file("Probe a task taken late"), "m-worker")
    step("merged-held", len(seen) == 1 and not manager_lines(listed, prs=pull, kind="merged"), seen)
    me = {"name": "h-worker"}
    data = {"found": [], "prs": [], "blockers": {}}
    first = team_gaps.worker_actions(me, set(), {}, data)
    use("hold", file("Probe a task for h-worker"), "h-worker")
    step("holds-held", len(first) == 1 and not team_gaps.worker_actions(me, set(), {}, data), first)
    pulls = {"found": [], "prs": [{"number": 6, "headRefName": "h-worker", "mergeable": "CONFLICTING"}], "blockers": {}}
    real, team_gaps.landing.conflicts = team_gaps.landing.conflicts, lambda number: True
    shown = [line for line in team_gaps.worker_actions(me, set(), {}, pulls) if line.startswith("rebase")]
    team_gaps.landing.conflicts = lambda number: False
    hidden = [line for line in team_gaps.worker_actions(me, set(), {}, pulls) if line.startswith("rebase")]
    team_gaps.landing.conflicts = real
    step("rebase-clean", len(shown) == 1 and not hidden, shown + hidden)
    step("limit-dropped", not hasattr(team_gaps, "limited"), "team_gaps.limited still exists")
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
