#!/usr/bin/env python3
"""Replay the team in varied scenarios on the sandbox board kalaluthien/teamwork-board-sandbox as the tape of recorded-gh/gh beside
this file holds it, while no judge or worker writes that board (else rerun a failure once alone), a temporary files board and the fake herdr beside this file, and print `<scenario> pass`, or `<scenario> fail` with the output that failed.

usage: replay-team-scenarios.py [--only <scenario>,...] [-v]
`-v` also prints each run's output. FAKE_HERDR_BREAK=accept makes the fake herdr take every prompt and wait, so the scenarios that
prove a send can fail must then fail."""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPTS = HERE.parent / "scripts"
SANDBOX = "kalaluthien/teamwork-board-sandbox"
TURNS = pathlib.Path(tempfile.mkdtemp(prefix="recorded-gh-"))  # each scenario's turns on its tape, so `--only` replays as the full run does


def agent(name, pane, status, workspace="w1"):
    return {"name": name, "pane_id": f"{workspace}:p{pane}", "tab_id": f"{workspace}:t{pane}", "workspace_id": workspace,
            "agent": "codex" if name.endswith("codex") else "claude", "agent_status": status, "interactive_ready": True}


def herdr(*agents):
    """A fake herdr state file holding AGENTS, each with its tab."""
    state = pathlib.Path(tempfile.mkstemp(prefix="fake-herdr-", suffix=".json")[1])
    state.write_text(json.dumps({"n": 10, "agents": list(agents),
                                 "tabs": [{"tab_id": a["tab_id"], "workspace_id": a["workspace_id"], "label": a["name"]} for a in agents]}))
    return state


def run(argv, state, pane=None, event=None, seconds=120, **env):
    env = {**os.environ, "GH_REPO": SANDBOX, "PATH": f"{HERE / 'recorded-gh'}:{HERE / 'fake-herdr'}:{os.environ['PATH']}", "FAKE_HERDR_STATE": str(state),
           "GH_TAPE": f"replay-team-scenarios-{SCENARIO}", "GH_TAPE_STATE": str(TURNS / f"{SCENARIO}.json"),
           "MONITOR_POLL": "1000", **({"HERDR_PANE_ID": pane} if pane else {}), **env}
    try:
        p = subprocess.run([str(a) for a in argv], env=env, input=event and json.dumps(event), capture_output=True, text=True, timeout=seconds)
        out, code = p.stdout + p.stderr, p.returncode
    except subprocess.TimeoutExpired as e:  # the heartbeat runs until killed
        out, code = (e.stdout or b"").decode() + (e.stderr or b"").decode(), None
    if VERBOSE:
        print(f"$ {' '.join(map(str, argv))}\n{out}", file=sys.stderr)
    return code, out


def hook(state, pane, event):
    code, out = run([ROOT / "hooks" / "route-event.py"], state, pane, event)
    try:
        o = json.loads(out)
    except ValueError:
        return out
    return (o.get("hookSpecificOutput") or {}).get("additionalContext") or (o.get("hookSpecificOutput") or {}).get("permissionDecisionReason") \
        or o.get("reason") or out


def heartbeat(state, pane, seconds=40):
    return run([ROOT / "monitors" / "print-team-gaps.py"], state, pane, seconds=seconds)[1]


def tell(state, name, text="hi"):
    note = pathlib.Path(tempfile.mkstemp(suffix=".md")[1])
    note.write_text(text)
    return run([SCRIPTS / "tell-session.py", name, note], state, TELL_SESSION_TIMEOUT="5")


def status(state, name):
    return next(a["agent_status"] for a in json.loads(pathlib.Path(state).read_text())["agents"] if a["name"] == name)


def lines_about(text, name):
    return [l for l in text.splitlines() if re.search(rf"(^|\s){re.escape(name)}(:|\s)", l)]


TEAM = (agent("teamwork-manager", 1, "idle"), agent("protocol-split-worker", 2, "idle"), agent("fixture-asking-worker", 3, "idle"))


def github_team():
    """A manager with two workers on the GitHub board: its start and heartbeat name each worker once, with what it holds."""
    state = herdr(*TEAM)
    start = hook(state, "w1:p1", {"hook_event_name": "SessionStart", "session_id": ""})
    stop = hook(state, "w1:p2", {"hook_event_name": "Stop", "stop_hook_active": False, "transcript_path": ""})
    beat = heartbeat(state, "w1:p1")
    for out in (start, beat):
        for n, held in (("protocol-split-worker", "#4 #3"), ("fixture-asking-worker", "#2")):
            if [l.split(":")[0] for l in lines_about(out, n)] != [f"idle {n}"] or f"holds {held}" not in out:
                return False, out
    return "Your goal still waits on you" in stop and "#3" in stop, "\n".join([start, stop, beat])


def files_board():
    """The same protocol on a files board: an issue filed, nested, ordered, held, asked, answered, edited, resolved and reopened reads back as written."""
    code, out = run([HERE / "replay-board-scenario.py", "--board", "files"], herdr(*TEAM))
    steps = dict(re.findall(r"^step (\S+)\n((?:(?!step ).*\n?)*)", out, re.M))
    ok = code == 0 and "holders=['probe-worker']" in steps.get("hold", "") and "parent=backlog" in steps.get("nest", "") \
        and "waits=blocked by #task" in steps.get("order", "") and "task: CLOSED" in steps.get("resolve-task", "") \
        and "backlog: CLOSED" in steps.get("resolve-backlog", "") and "backlog: OPEN" in steps.get("reopen", "") \
        and "follow-up: OPEN labels=[] parent=backlog" in steps.get("nest-again", "")
    return ok, out


def git_landing():
    """Two workers' changes landed in a repository with no remote: every step of replay-landing-scenario.py is ok."""
    code, out = run([HERE / "replay-landing-scenario.py"], herdr(*TEAM))
    return code == 0 and "fail" not in out, out


def herdr_receiver(status_now, expect_code, expect):
    """A non-Claude receiver in STATUS_NOW told by tell-session.py."""
    state = herdr(agent("protocol-split-worker", 1, "working"), agent("receiver-codex", 2, status_now))
    code, out = tell(state, "receiver-codex")
    return code == expect_code and re.search(expect, out) is not None, out


def tell_claude():
    """A Claude receiver, idle or working, told by tell-session.py: refused within 2 s, naming SendMessage, and never prompted."""
    state = herdr(agent("protocol-split-worker", 1, "working"), agent("idle-worker", 2, "idle"), agent("busy-worker", 3, "working"))
    outs = []
    for name, before in (("idle-worker", "idle"), ("busy-worker", "working")):
        started = time.time()
        code, out = tell(state, name)
        outs.append(out)
        if code != 1 or time.time() - started > 2 or "SendMessage" not in out or status(state, name) != before:
            return False, "\n".join(outs)
    return True, "\n".join(outs)


def send_failed():
    """A send herdr refuses and a board write the hook denies: each says why, and nothing reaches the receiver or runs."""
    state = herdr(agent("protocol-split-worker", 1, "working"), agent("refuse-codex", 2, "idle"))
    code, out = tell(state, "refuse-codex")
    denied = hook(state, "w1:p1", {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "gh issue comment 1 --body hi"}, "cwd": "."})
    ok = code == 1 and "not delivered to refuse-codex: agent_pane_closed" in out and status(state, "refuse-codex") == "idle" and "--body-file" in denied
    return ok, f"{out}\n{denied}"


def monitor_restart():
    """The heartbeat stopped and started again names each gap it named before, none lost and none twice."""
    state = herdr(*TEAM)
    first, second = (heartbeat(state, "w1:p1").splitlines() for _ in range(2))
    return bool(first) and sorted(first) == sorted(second) and len(set(first)) == len(first), "\n".join(first + ["-- restart --"] + second)


def two_managers():
    """Two managers of two projects in one workspace: neither is told to close the other, each is told to move to a workspace of its own,
    and a successor misnamed is refused."""
    state = herdr(*TEAM, agent("other-manager", 4, "idle"), agent("other-task-worker", 5, "idle"))
    outs = {pane: hook(state, pane, {"hook_event_name": "SessionStart", "session_id": ""}) for pane in ("w1:p1", "w1:p4")}
    ok = all([l.split(":")[0] for l in lines_about(o, other)] == ["shared workspace"] and f"`start` `{me}-next` with `succeed {me}`" in o for o, me, other in
             ((outs["w1:p1"], "teamwork-manager", "other-manager"), (outs["w1:p4"], "other-manager", "teamwork-manager")))
    code, out = start(state, "w1:p1", "third-manager", "succeed teamwork-manager")
    return ok and code == 1 and "not named teamwork-manager-next" in out, "\n".join([*outs.values(), out])


def start(state, pane, name, args, *flags):
    return run([SCRIPTS / "start-session.py", name, "/tmp", args, "--model", "haiku", "--effort", "low", *flags], state, pane, seconds=30)


def workspace_of(state, name):
    return next((a["workspace_id"] for a in json.loads(pathlib.Path(state).read_text())["agents"] if a["name"] == name), None)


def workspaces(state):
    return {t["workspace_id"] for t in json.loads(pathlib.Path(state).read_text())["tabs"]}


def worker_placement():
    """A worker and a sentinel started from a pane in another workspace land in their manager's; one naming a manager not live
    is refused with nothing opened, and no placement flag is taken."""
    state = herdr(*TEAM, agent("other-task-worker", 1, "idle", "w2"))
    before = workspaces(state)
    outs = [start(state, "w2:p1", "place-task-worker", "worker place-task-worker manager teamwork-manager x"),
            start(state, "w2:p1", "place-duty-sentinel", "sentinel place-duty-sentinel manager teamwork-manager x")]
    tabs_before = len(json.loads(state.read_text())["tabs"])
    refused = [start(state, "w1:p1", "lost-task-worker", "worker lost-task-worker manager gone-manager x"),
               *(start(state, "w1:p1", "flag-task-worker", "worker flag-task-worker manager teamwork-manager x", *flags)
                 for flags in (["--team"], ["--beside", "teamwork-manager"]))]
    ok = all(code == 0 for code, _ in outs) and workspace_of(state, "place-task-worker") == workspace_of(state, "place-duty-sentinel") == "w1" \
        and workspaces(state) == before and len(json.loads(state.read_text())["tabs"]) == tabs_before \
        and refused[0][0] == 1 and "gone-manager is not live" in refused[0][1] and all(code == 2 for code, _ in refused[1:])
    return ok, "\n".join(out for _, out in outs + refused)


def manager_placement():
    """A manager opens a workspace of its own; a successor joins its predecessor's workspace, or opens its own when another project's
    manager shares that workspace."""
    state = herdr(*TEAM, agent("crowded-manager", 1, "idle", "w3"), agent("other-manager", 2, "idle", "w3"))
    outs = [start(state, "w1:p2", "fresh-manager", "fresh"),
            start(state, "w1:p2", "teamwork-manager-next", "succeed teamwork-manager"),
            start(state, "w1:p2", "crowded-manager-next", "succeed crowded-manager")]
    placed = [workspace_of(state, n) for n in ("fresh-manager", "teamwork-manager-next", "crowded-manager-next")]
    labels = {t["workspace_id"]: t["label"] for t in json.loads(state.read_text())["tabs"]}
    ok = all(code == 0 for code, _ in outs) and placed[0] not in ("w1", "w3", None) and placed[1] == "w1" \
        and placed[2] not in ("w1", "w3", None, placed[0]) and labels.get(placed[0]) == "fresh-manager"
    return ok, "\n".join(out for _, out in outs) + f"\nplaced {placed}"


def moved_me():
    """A session whose pane moved, its shell's HERDR_PANE_ID left naming another session's pane, still finds itself by its session id."""
    state = herdr(dict(agent("teamwork-manager", 15, "idle", "w4"), agent_session={"value": "moved-id"}), agent("other-manager", 1, "idle", "w9"))
    code, out = run([SCRIPTS / "print-scope-label.py", "--me"], state, "w9:p1", CLAUDE_CODE_SESSION_ID="moved-id")
    # with no session id listed, as for an agent herdr gives none, the pane it started in still finds it
    unlisted = herdr(agent("teamwork-manager", 15, "idle", "w4"), agent("other-manager", 1, "idle", "w9"))
    code_pane, out_pane = run([SCRIPTS / "print-scope-label.py", "--me"], unlisted, "w4:p15", CLAUDE_CODE_SESSION_ID="moved-id")
    return code == code_pane == 0 and out.strip() == out_pane.strip() == "scope:teamwork", out + out_pane


def moved_close():
    """A session whose pane moves while it is closed still gets its dialog answered at its new pane, and closes."""
    stuck = dict(agent("moving-worker", 1, "blocked", "w9"), screen="Background work is running", move="w4:p15", move_after=2)  # after the own check and the first read
    state = herdr(*TEAM, stuck)
    code, out = run([SCRIPTS / "close-session.py", "moving-worker"], state, "w1:p1", seconds=30, CLOSE_SESSION_TIMEOUT="5")
    return code == 0 and "moving-worker exited" in out, out


def moved_tell():
    """A receiver whose pane moved after the read that found it still gets the text."""
    state = herdr(*TEAM, dict(agent("moving-receiver-codex", 1, "idle", "w9"), move="w4:p15"))
    code, out = tell(state, "moving-receiver-codex")
    return code == 0 and out.strip() == "delivered to moving-receiver-codex", out


def moved_answer():
    """A tool prompt whose pane moved after the read that found it is still read and answered."""
    screen = "Bash command\n\nDo you want to proceed?\n❯ 1. Yes\n  2. No"
    state = herdr(*TEAM, dict(agent("moving-asker-worker", 1, "blocked", "w9"), screen=screen, move="w4:p15"))
    code, out = run([SCRIPTS / "answer-prompt.py", "moving-asker-worker", "1"], state, "w1:p1")
    answered = next(a.get("answered") for a in json.loads(state.read_text())["agents"] if a["name"] == "moving-asker-worker")
    return code == 0 and answered == "1", out


def moved_rename():
    """A session whose pane moved after the read that found it is still renamed in herdr and in Claude Code."""
    home = tempfile.mkdtemp(prefix="fake-home-")
    state = herdr(dict(agent("teamwork-manager", 1, "idle", "w9"), agent_session={"value": "moved-id"}, move="w4:p15"))
    code, out = run([SCRIPTS / "rename-session.py", "renamed-manager"], state, "w9:p1", seconds=60,
                    CLAUDE_CODE_SESSION_ID="moved-id", FAKE_HERDR_HOME=home, HOME=home)
    return code == 0 and out.strip() == "renamed to renamed-manager" and workspace_of(state, "renamed-manager") == "w4", out


def moved_start():
    """A started session whose pane moves before its kick-off is typed still takes its kick-off."""
    state = herdr(*TEAM)
    code, out = run([SCRIPTS / "start-session.py", "moving-slow-worker", "/tmp", "worker moving-slow-worker manager teamwork-manager x",
                     "--model", "haiku", "--effort", "low"], state, "w1:p1", seconds=60, START_SESSION_TIMEOUT="10")
    return code == 0 and "took its kick-off" in out and status(state, "moving-slow-worker") == "working", out


SCENARIOS = {
    "github-team": github_team,
    "files-board": files_board,
    "git-landing": git_landing,
    "herdr-idle": lambda: herdr_receiver("idle", 0, r"^delivered to receiver-codex$"),
    "herdr-busy": lambda: herdr_receiver("working", 0, r"^delivered to receiver-codex after its turn$"),
    "herdr-prompt": lambda: herdr_receiver("blocked", 1, r"^not delivered to receiver-codex: blocked at a tool prompt"),
    "tell-claude": tell_claude,
    "send-failed": send_failed,
    "monitor-restart": monitor_restart,
    "two-managers": two_managers,
    "worker-placement": worker_placement,
    "manager-placement": manager_placement,
    "moved-me": moved_me,
    "moved-close": moved_close,
    "moved-tell": moved_tell,
    "moved-answer": moved_answer,
    "moved-rename": moved_rename,
    "moved-start": moved_start,
}
def main(args):
    global VERBOSE, SCENARIO
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="")
    parser.add_argument("-v", action="store_true")
    a = parser.parse_args(args)
    VERBOSE = a.v
    for name, scenario in SCENARIOS.items():
        if a.only and name not in a.only.split(","):
            continue
        SCENARIO = name
        ok, out = scenario()
        print(f"{name} pass" if ok else f"{out.strip()}\n{name} fail", flush=True)
    shutil.rmtree(TURNS)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
