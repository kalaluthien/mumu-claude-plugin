#!/usr/bin/env python3
"""Replay the team in varied scenarios, each in a scratch repository with a git board and the fake herdr, each run under a stand-in `claude` started
as the session its pane holds; print `ok <scenario>` or `fail <scenario>: <the output that failed>` per scenario, then `PASS` or `FAIL`, and exit 1
on any failure.

usage: replay-team-scenarios.py [--only <scenario>,...] [--verbose]
`--verbose` also prints each run's output."""
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402
import usage_parser  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "kick-off" / "scripts"
ADAPTERS = ROOT / "skills" / "kick-off" / "references" / "adapters"
TELL = ADAPTERS / "message-herdr" / "scripts" / "tell-session.py"
RENAME = ADAPTERS / "session-herdr" / "scripts" / "rename-session.py"
agent = replay_probe.agent
VERBOSE = False


def run(box, argv, pane=None, seconds=120, **options):
    """(exit code, stdout and stderr) of ARGV run in BOX from PANE; None for a run past SECONDS."""
    done = box.run(argv, pane, timeout=seconds, **options)
    if VERBOSE:
        print(f"$ {' '.join(map(str, argv))}\n{done.stdout}{done.stderr}", file=sys.stderr)
    return done.returncode, done.stdout + done.stderr


def hook(box, pane, event, **options):
    code, out = run(box, [replay_probe.ROUTER], pane, input=json.dumps(event), **options)
    try:
        output = json.loads(out)
    except ValueError:
        return out
    return (output.get("hookSpecificOutput") or {}).get("additionalContext") or (output.get("hookSpecificOutput") or {}).get("permissionDecisionReason") \
        or output.get("reason") or out


def heartbeat(box, pane):
    """The lines the monitor prints in PANE over two polls."""
    return run(box, [ROOT / "monitors" / "print-team-gaps.py", "--polls", "2"], pane, seconds=60, TEAMWORK_MONITOR_POLL="0.2")[1]


def tell(box, name, note=None):
    return run(box, [TELL, name, note or replay_probe.write_text(box.work, "note.md", "hi")], TEAMWORK_TELL_SESSION_TIMEOUT="5")


def start(box, pane, name, args, *flags):
    return run(box, [SCRIPTS / "start-session.py", name, box.repository, args, "--model", "haiku", "--effort", "low", *flags], pane, seconds=30)


def listed(box, name):
    return next((each for each in box.herdr_state()["agents"] if each["name"] == name), {})


def workspaces(box):
    return {tab["workspace_id"] for tab in box.herdr_state()["tabs"]}


def tabs(box):
    return len(box.herdr_state()["tabs"])


def lines_about(text, name):
    return [line for line in text.splitlines() if re.search(rf"(^|\s){re.escape(name)}(:|\s)", line)]


TEAM = (agent("teamwork-manager", 1, "idle"), agent("protocol-split-worker", 2, "idle"), agent("fixture-asking-worker", 3, "idle"))


def git_team(box):
    """A manager with two workers on a git board: its start and heartbeat name the idle worker once, with what it holds, and the asking one by its `answer` line; a worker with an open goal is stopped once."""
    box.herdr(TEAM)

    def use(*argv):
        return box.python(SCRIPTS / "use-board.py", *argv, pane="w1:p1").stdout.strip()

    def filed(title):
        return int(use("file", "--title", title, "--body", replay_probe.write_text(box.work, "body.md", "Probe the team.\n")).rsplit("/", 1)[1])

    first, asked, held_one, held_two = (filed(f"Probe the team's {word} task") for word in ("first", "asked", "held", "other"))
    for number, name in ((asked, "fixture-asking-worker"), (held_one, "protocol-split-worker"), (held_two, "protocol-split-worker")):
        use("hold", number, "--holders", name)
    use("comment", asked, "--blocked", "may the probe run")
    began = hook(box, "w1:p1", {"hook_event_name": "SessionStart", "session_id": ""})
    stop = hook(box, "w1:p2", {"hook_event_name": "Stop", "stop_hook_active": False, "transcript_path": ""})
    beat = heartbeat(box, "w1:p1")
    held = f"holds #{held_two} #{held_one}"
    for out in (began, beat):
        # the asking worker waits on its manager, so its line is the manager's `answer`, not an `idle`
        if [line.split(":")[0] for line in lines_about(out, "protocol-split-worker")] != ["idle protocol-split-worker"] or held not in out \
                or lines_about(out, "idle fixture-asking-worker") or not any(line.startswith(f"answer #{asked}:") for line in out.splitlines()):
            return False, out
    return "Your goal still waits on you" in stop and f"#{held_one}" in stop, "\n".join([began, stop, beat])


def herdr_receiver(box, status_now, expect_code, expect):
    """A non-Claude receiver in STATUS_NOW told by tell-session.py."""
    box.herdr([agent("protocol-split-worker", 1, "working"), agent("receiver-codex", 2, status_now)])
    code, out = tell(box, "receiver-codex")
    return code == expect_code and re.search(expect, out) is not None, out


def tell_claude(box):
    """A Claude receiver, idle or working, told by tell-session.py with a text file or with a second argument that is no file: refused within 2 s, naming SendMessage, and never prompted."""
    box.herdr([agent("protocol-split-worker", 1, "working"), agent("idle-worker", 2, "idle"), agent("busy-worker", 3, "working")])
    outs = []
    for name, before in (("idle-worker", "idle"), ("busy-worker", "working")):
        for note in (None, "not a file"):
            started = time.time()
            code, out = tell(box, name, note)
            outs.append(out)
            if code != 1 or time.time() - started > 2 or "SendMessage" not in out or listed(box, name)["agent_status"] != before:
                return False, "\n".join(outs)
    return True, "\n".join(outs)


def send_failed(box):
    """A send herdr refuses says why, and nothing reaches the receiver."""
    box.herdr([agent("protocol-split-worker", 1, "working"), agent("refuse-codex", 2, "idle")])
    code, out = tell(box, "refuse-codex")
    return code == 1 and "not delivered to refuse-codex: agent_pane_closed" in out and listed(box, "refuse-codex")["agent_status"] == "idle", out


def monitor_restart(box):
    """The heartbeat stopped and started again names each gap it named before, none lost and none twice."""
    box.herdr(TEAM)
    first, second = (heartbeat(box, "w1:p1").splitlines() for _ in range(2))
    return bool(first) and sorted(first) == sorted(second) and len(set(first)) == len(first), "\n".join(first + ["-- restart --"] + second)


def two_managers(box):
    """Two managers of two projects in one workspace: neither is told to close the other, each is told to move to a workspace of its own,
    and a successor misnamed is refused."""
    box.herdr([*TEAM, agent("other-manager", 4, "idle"), agent("other-task-worker", 5, "idle")])
    outs = {pane: hook(box, pane, {"hook_event_name": "SessionStart", "session_id": ""}) for pane in ("w1:p1", "w1:p4")}
    ok = all([line.split(":")[0] for line in lines_about(output, other)] == ["shared workspace"] and f"`start` `{me}-next` with `succeed {me}`" in output for output, me, other in
             ((outs["w1:p1"], "teamwork-manager", "other-manager"), (outs["w1:p4"], "other-manager", "teamwork-manager")))
    code, out = start(box, "w1:p1", "third-manager", "succeed teamwork-manager")
    return ok and code == 1 and "not named teamwork-manager-next" in out, "\n".join([*outs.values(), out])


def worker_placement(box):
    """A worker and a sentinel started from a pane in another workspace land in their manager's; one naming a manager not live
    is refused with nothing opened, and no placement flag is taken."""
    box.herdr([*TEAM, agent("other-task-worker", 1, "idle", "w2")])
    before = workspaces(box)
    outs = [start(box, "w2:p1", "place-task-worker", "worker place-task-worker manager teamwork-manager x"),
            start(box, "w2:p1", "place-duty-sentinel", "sentinel place-duty-sentinel manager teamwork-manager x")]
    tabs_before = tabs(box)
    refused = [start(box, "w1:p1", "lost-task-worker", "worker lost-task-worker manager gone-manager x"),
               *(start(box, "w1:p1", "flag-task-worker", "worker flag-task-worker manager teamwork-manager x", *flags)
                 for flags in (["--team"], ["--beside", "teamwork-manager"]))]
    ok = all(code == 0 for code, _ in outs) and listed(box, "place-task-worker").get("workspace_id") == listed(box, "place-duty-sentinel").get("workspace_id") == "w1" \
        and workspaces(box) == before and tabs(box) == tabs_before \
        and refused[0][0] == 1 and "gone-manager is not live" in refused[0][1] and all(code == 2 for code, _ in refused[1:])
    return ok, "\n".join(out for _, out in outs + refused)


def worker_workspace(box):
    """A name ending in one role whose kick-off arguments name another is refused with nothing opened, since a worker or sentinel
    read as a manager would get a workspace of its own outside its team."""
    box.herdr(TEAM)
    before, tabs_before = workspaces(box), tabs(box)
    refused = [start(box, "w1:p1", "stray-task-worker", "manager stray-task-worker"),
               start(box, "w1:p1", "stray-duty-sentinel", "teamwork-manager"),
               start(box, "w1:p1", "stray-other-manager", "worker stray-other-manager manager teamwork-manager x")]
    ok = all(code == 2 and "kick-off arguments start a" in out for code, out in refused) and workspaces(box) == before and tabs(box) == tabs_before
    return ok, "\n".join(out for _, out in refused)


def role_names(box):
    """A session starts only under a name ending in a role suffix, however long its stem; any other name is refused with the allowed forms
    named and nothing opened, since the heartbeat lists a session by that suffix."""
    box.herdr(TEAM)
    long_stem = "x" * 40
    allowed = [start(box, "w1:p1", f"{long_stem}-worker", f"worker {long_stem}-worker manager teamwork-manager x"),
               start(box, "w1:p1", "duty-sentinel", "sentinel duty-sentinel manager teamwork-manager x"),
               start(box, "w1:p1", "odd-manager", "odd"),
               start(box, "w1:p1", "teamwork-manager-next", "succeed teamwork-manager")]
    tabs_before = tabs(box)
    refused = [start(box, "w1:p1", "bare-task", "worker bare-task manager teamwork-manager x"),
               start(box, "w1:p1", "bare-lead", "bare")]
    ok = all(code == 0 for code, _ in allowed) and all(code == 2 and "<task>-worker" in out and "<manager>-next" in out for code, out in refused) \
        and tabs(box) == tabs_before
    return ok, "\n".join(out for _, out in allowed + refused)


def manager_placement(box):
    """A manager opens a workspace of its own; a successor joins its predecessor's workspace, or opens its own when another project's
    manager shares that workspace."""
    box.herdr([*TEAM, agent("crowded-manager", 1, "idle", "w3"), agent("other-manager", 2, "idle", "w3")])
    outs = [start(box, "w1:p2", "fresh-manager", "fresh"),
            start(box, "w1:p2", "teamwork-manager-next", "succeed teamwork-manager"),
            start(box, "w1:p2", "crowded-manager-next", "succeed crowded-manager")]
    placed = [listed(box, name).get("workspace_id") for name in ("fresh-manager", "teamwork-manager-next", "crowded-manager-next")]
    labels = {tab["workspace_id"]: tab["label"] for tab in box.herdr_state()["tabs"]}
    ok = all(code == 0 for code, _ in outs) and placed[0] not in ("w1", "w3", None) and placed[1] == "w1" \
        and placed[2] not in ("w1", "w3", None, placed[0]) and labels.get(placed[0]) == "fresh-manager"
    return ok, "\n".join(out for _, out in outs) + f"\nplaced {placed}"


def moved_me(box):
    """A session whose pane moved, its shell's HERDR_PANE_ID left naming another session's pane, still finds itself by its session id."""
    (box.repository / "teamwork").mkdir()
    me = [SCRIPTS.parent / "references/manager/scripts" / "print-scope-folder.py", "--me"]
    box.herdr([agent("teamwork-manager", 15, "idle", "w4", agent_session={"value": "moved-id"}), agent("other-manager", 1, "idle", "w9")])
    code, out = run(box, me, "w9:p1", claude=["--name", "teamwork-manager"], CLAUDE_CODE_SESSION_ID="moved-id")
    # with no session id listed, as for an agent herdr gives none, the pane it started in still finds it
    box.herdr([agent("teamwork-manager", 15, "idle", "w4"), agent("other-manager", 1, "idle", "w9")])
    code_pane, out_pane = run(box, me, "w4:p15", CLAUDE_CODE_SESSION_ID="moved-id")
    return code == code_pane == 0 and out.strip() == out_pane.strip() == "teamwork", out + out_pane


def moved_close(box):
    """A session whose pane moves while it is closed still gets its dialog answered at its new pane, and closes."""
    stuck = agent("moving-worker", 1, "blocked", "w9", screen="Background work is running", move="w4:p15", move_after=2)  # after the own check and the first read
    box.herdr([*TEAM, stuck])
    code, out = run(box, [SCRIPTS / "close-session.py", "moving-worker"], "w1:p1", seconds=30, TEAMWORK_CLOSE_SESSION_TIMEOUT="5")
    return code == 0 and "moving-worker exited" in out, out


def moved_tell(box):
    """A receiver whose pane moved after the read that found it still gets the text."""
    box.herdr([*TEAM, agent("moving-receiver-codex", 1, "idle", "w9", move="w4:p15")])
    code, out = tell(box, "moving-receiver-codex")
    return code == 0 and out.strip() == "delivered to moving-receiver-codex", out


def moved_answer(box):
    """A tool prompt whose pane moved after the read that found it is still read and answered."""
    screen = "Bash command\n\nDo you want to proceed?\n❯ 1. Yes\n  2. No"
    box.herdr([*TEAM, agent("moving-asker-worker", 1, "blocked", "w9", screen=screen, move="w4:p15")])
    code, out = run(box, [SCRIPTS / "answer-prompt.py", "moving-asker-worker", "1"], "w1:p1")
    return code == 0 and listed(box, "moving-asker-worker").get("answered") == "1", out


BOX = "─" * 20 + " teamwork-manager ─\n❯ {draft}\n" + "─" * 40 + "\n  -- INSERT --"


def rename(box, session_id, seconds=60, **more):
    """rename-session.py run by the manager in w9:p1, whose /rename the fake herdr records in the sandbox's transcript, as Claude Code does."""
    box.herdr([agent("teamwork-manager", 1, "idle", "w9", agent_session={"value": session_id}, **more)])
    return run(box, [RENAME, "renamed-manager"], "w9:p1", seconds=seconds, CLAUDE_CODE_SESSION_ID=session_id)


def hinted_rename(box):
    """A box showing only Claude Code's dim hint, `Press up to edit queued messages`, is empty, so the session is renamed."""
    code, out = rename(box, "hint-id", screen=BOX.format(draft="\x1b[2mPress up to edit queued messages\x1b[0m"))
    return code == 0 and out.strip() == "renamed to renamed-manager", out


def kept_draft(box):
    """A session whose prompt box holds an unsent draft is sent no `/rename`: the script says why it did not rename, and the draft stays."""
    code, out = rename(box, "draft-id", seconds=90, screen=BOX.format(draft="half a sentence"))
    typed = (box.config / "projects").exists()  # the fake herdr writes a transcript only for a typed `/rename`
    return code == 1 and out.startswith("not renamed to renamed-manager: the prompt box holds an unsent draft") and not typed, out


def moved_rename(box):
    """A session whose pane moved after the read that found it is still renamed in herdr and in Claude Code."""
    code, out = rename(box, "moved-id", move="w4:p15", screen=BOX.format(draft=""))
    return code == 0 and out.strip() == "renamed to renamed-manager" and listed(box, "renamed-manager").get("workspace_id") == "w4", out


def moved_start(box):
    """A started session whose pane moves before its kick-off is typed still takes its kick-off."""
    box.herdr(TEAM)
    code, out = run(box, [SCRIPTS / "start-session.py", "moving-slow-worker", box.repository, "worker moving-slow-worker manager teamwork-manager x",
                          "--model", "haiku", "--effort", "low"], "w1:p1", seconds=60, TEAMWORK_START_SESSION_TIMEOUT="10")
    return code == 0 and "took its kick-off" in out and listed(box, "moving-slow-worker").get("agent_status") == "working", out


SCENARIOS = {
    "git-team": git_team,
    "herdr-idle": lambda box: herdr_receiver(box, "idle", 0, r"^delivered to receiver-codex$"),
    "herdr-busy": lambda box: herdr_receiver(box, "working", 0, r"^delivered to receiver-codex after its turn$"),
    "herdr-prompt": lambda box: herdr_receiver(box, "blocked", 1, r"^not delivered to receiver-codex: blocked at a tool prompt"),
    "tell-claude": tell_claude,
    "send-failed": send_failed,
    "monitor-restart": monitor_restart,
    "two-managers": two_managers,
    "worker-placement": worker_placement,
    "worker-workspace": worker_workspace,
    "role-names": role_names,
    "manager-placement": manager_placement,
    "moved-me": moved_me,
    "moved-close": moved_close,
    "moved-tell": moved_tell,
    "moved-answer": moved_answer,
    "moved-rename": moved_rename,
    "kept-draft": kept_draft,
    "hinted-rename": hinted_rename,
    "moved-start": moved_start,
}


def main(args):
    global VERBOSE
    parser = usage_parser.parser(__doc__)
    parser.add_argument("--only", default="")
    parser.add_argument("--verbose", action="store_true")
    options = parser.parse_args(args)
    VERBOSE = options.verbose
    cases = replay_probe.Cases(only=[name for name in options.only.split(",") if name])
    with replay_probe.scratch("team-scenarios-") as work:
        for name, scenario in SCENARIOS.items():
            if cases.wanted(name):
                ok, out = scenario(replay_probe.Sandbox(work / name))
                cases.step(name, ok, out)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
