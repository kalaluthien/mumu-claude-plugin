#!/usr/bin/env python3
"""Run each script that names the session it runs in, `list-sessions.py --me`, route-event.py's SessionStart, `rename-session.py` and the heartbeat
monitor `print-team-gaps.py`, in a pane that herdr records as the worker's, under a stand-in `claude` started as start-session.py starts the worker,
as a session renamed to the worker and as a bare `claude -p`, on a scratch repository with a git board and the fake herdr. Print `ok <case>` or
`fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `list-started`, `list-renamed`, `list-child`: `--me` prints the worker's name for the first two and nothing for the child;
- `role-started`, `role-renamed`, `role-child`: SessionStart in the worker's worktree tells the first two the worker role and not the child;
- `monitor-started`, `monitor-child`: the monitor prints the worker's `answered` line for the started worker and nothing for the child;
- `rename-child`, `rename-started`: the child is refused as owning no session, while the started worker gets past that refusal;
- `rename-role`: the started worker's rename to a manager's name is refused as changing its role, nothing renamed, while a worker started as its `-next` successor gets past that refusal;
- `parse`: team_names.parse reads a worker's, a sentinel's, a manager's and a `-next` successor's name, and raises ValueError on a name of no role suffix;
- `rename-config`: the started worker, its prompt box empty, is renamed, the name Claude Code records being read from CLAUDE_CONFIG_DIR, which lies outside HOME.

usage: replay-own-readers.py"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = ROOT / "skills" / "kick-off" / "scripts"
RENAME = ROOT / "skills" / "kick-off" / "references" / "adapters" / "session-herdr" / "scripts" / "rename-session.py"
MONITOR = ROOT / "monitors" / "print-team-gaps.py"
NAME = "c-worker"
SESSION = "00000000-0000-4000-8000-000000000003"
ROLE_LINE = f"You are {NAME}, a teamwork worker"
BOX = "─" * 20 + f" {NAME} ─\n❯ \n" + "─" * 40 + "\n  -- INSERT --"  # an empty prompt box as Claude Code draws it
RENAME_SECONDS = 5  # a rename that got past the refusal goes on to wait for a prompt box, which the fake herdr never shows
# each way a session runs: the stand-in's options, as agent.command builds a worker's, and whether the transcript holds the worker's title
STARTED = (["--name", NAME, "--plugin-dir", "plugin", "--model", "opus", "--effort", "high", "--settings", '{"autoCompactWindow": 400000}'], False)
RENAMED = (["--model", "opus"], True)
CHILD = (["-p", "probe", "--model", "haiku"], False)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("own-readers-") as work:
        box = replay_probe.Sandbox(work, [replay_probe.agent("c-manager", 1, "working"),
                                          replay_probe.agent(NAME, 2, "working", agent_session={"value": SESSION})])
        box.environment["TEAMWORK_MONITOR_POLL"] = "0.2"
        transcript = box.config / "projects" / "folder" / f"{SESSION}.jsonl"
        transcript.parent.mkdir(parents=True)
        worktree = box.work / "live" / ".claude" / "worktrees" / NAME
        worktree.mkdir(parents=True)

        def as_worker(way):
            """The options and variables of a run in the worker's pane as WAY, its transcript titled or not."""
            options, titled = way
            transcript.unlink(missing_ok=True)
            if titled:
                transcript.write_text(json.dumps({"type": "custom-title", "customTitle": NAME, "sessionId": SESSION}, separators=(",", ":")) + "\n")
            return {"pane": "w1:p2", "claude": options, "CLAUDE_CODE_SESSION_ID": SESSION}

        def run(script, argv, way, seconds=60):
            done = box.python(script, *argv, timeout=seconds, **as_worker(way))
            return done.returncode, done.stdout + done.stderr

        def told(way):
            event = {"hook_event_name": "SessionStart", "source": "startup", "session_id": SESSION, "cwd": str(worktree), "transcript_path": str(transcript)}
            answer = box.route(event, **as_worker(way))
            return ROLE_LINE in json.dumps(answer), answer

        def use(pane, *argv):
            return box.python(SCRIPTS / "use-board.py", *argv, pane=pane).stdout.strip()  # the board's writers are found by pane, the session id being the worker's alone

        number = use("w1:p1", "file", "--title", "Answer a held task", "--body", replay_probe.write_text(work, "body.md", "Answer a held task.\n"),
                     "--label", "scope:x").rsplit("/", 1)[-1].removesuffix(".json")
        use("w1:p1", "decide", number, "--decision", f"{NAME} holds this.", "--holders", NAME)
        asked = use("w1:p2", "comment", number, "--blocked", "which way")
        use("w1:p1", "decide", number, "--decision", "take the first way.", "--answers", asked)

        parsed = box.evaluate("""import json, team_names
def parsed(name):
    try:
        return list(team_names.parse(name))
    except ValueError as e:
        return str(e)
print(json.dumps([parsed(name) for name in ("c-worker", "ops-sentinel", "my-app-manager", "my-app-manager-next", "c-worker4", "Bad")]))""")
        cases.step("parse", parsed[:4] == [["worker", "c", False], ["sentinel", "ops", False], ["manager", "my-app", False], ["manager", "my-app", True]]
                   and all("is no session name" in said for said in parsed[4:]), parsed)
        for case, way, expected in (("list-started", STARTED, NAME), ("list-renamed", RENAMED, NAME), ("list-child", CHILD, "")):
            code, out = run(SCRIPTS / "list-sessions.py", ["--me"], way)
            cases.step(case, out.strip() == expected, (code, out))
        for case, way, expected in (("role-started", STARTED, True), ("role-renamed", RENAMED, True), ("role-child", CHILD, False)):
            got, answer = told(way)
            cases.step(case, got == expected, answer)
        code, saw = run(MONITOR, ["--polls", "3"], STARTED)
        cases.step("monitor-started", code == 0 and f"answered #{number}" in saw, (code, saw))
        code, saw = run(MONITOR, ["--polls", "3"], CHILD)
        cases.step("monitor-child", code == 0 and saw.strip() == "", (code, saw))
        # the fake herdr keeps a rename, so the renames come last
        code, out = run(RENAME, ["c2-worker"], CHILD)
        cases.step("rename-child", code == 1 and "no herdr session owns this pane" in out, (code, out))
        code, out = run(RENAME, ["c2-worker"], STARTED, seconds=RENAME_SECONDS)
        cases.step("rename-started", "no herdr session owns this pane" not in out, (code, out))
        before = len(box.herdr_calls())
        code, out = run(RENAME, ["c-manager"], STARTED)
        refused = code == 1 and "keeps the role it started with" in out and not any("rename" in call for call in box.herdr_calls()[before:])
        code, successor = run(RENAME, ["c4-worker"], ([NAME + "-next" if word == NAME else word for word in STARTED[0]], False), seconds=RENAME_SECONDS)
        cases.step("rename-role", refused and "keeps the role" not in successor and "no herdr session" not in successor, (out, successor))
        box.herdr([replay_probe.agent(NAME, 2, "idle", agent_session={"value": SESSION}, screen=BOX)])
        code, out = run(RENAME, ["c3-worker"], STARTED)
        cases.step("rename-config", code == 0 and out.strip() == "renamed to c3-worker", (code, out))
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
