#!/usr/bin/env python3
"""Check that the watch follows held work, on a scratch git board and the fake herdr. Print `ok <case>` or `fail <case>: <detail>` per case,
then `PASS` or `FAIL`, and exit 1 on any failure:
- `warned`: `start-session.py` of a worker whose manager has no heartbeat process under its session id warns that the heartbeat is not running;
- `quiet`: the same start with a heartbeat process listed under that id prints no such warning;
- `part-held`: a part its parent's holder names in the parent's Definition of done is held by that holder;
- `part-taken`: a part another session already holds, named by the parent's holder in the same edit, keeps its holder;
- `part-other`: a part the manager, who does not hold the parent, names in it stays unheld.

usage: replay-watch-held.py"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = ROOT / "skills" / "kick-off" / "scripts"
MANAGER_SESSION = "sess-manager"
BODY = ("Hold the parts.\n\n## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints ok; meets: the caller's need.\n\n"
        "## Definition of done\n\nLast line.\n")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("watch-held-") as work:
        sandbox = replay_probe.Sandbox(work, [replay_probe.agent("w-manager", 1, "working", agent_session={"value": MANAGER_SESSION}),
                                              replay_probe.agent("w-worker", 2, "working")])
        listed = work / "heartbeat.txt"
        # the processes `ps -E` lists, which is how the start looks for the manager's heartbeat
        replay_probe.write_text(sandbox.bin, "ps", f'#!/bin/sh\ncase "$*" in *-E*) cat "{listed}";; *) exec /bin/ps "$@";; esac\n').chmod(0o755)

        def start(name):
            argv = [SCRIPTS / "start-session.py", name, work, f"worker {name} manager w-manager https://example.com/1", "--model", "haiku", "--effort", "medium"]
            return sandbox.python(*argv, cwd=work, TEAMWORK_START_SESSION_TIMEOUT=3).stderr

        listed.write_text("")
        cases.step("warned", "heartbeat of the manager" in start("w-new-worker"), "no warning")
        listed.write_text(f"123 python3 /x/monitors/print-team-gaps.py CLAUDE_CODE_SESSION_ID={MANAGER_SESSION} HOME=/x\n")
        cases.step("quiet", "heartbeat of the manager" not in start("w-third-worker"), "warned")

        def use(pane, *argv):
            done = sandbox.python(SCRIPTS / "use-board.py", *argv, pane=pane)
            return done.stdout.strip() + done.stderr

        def filed(title):
            return use("w1:p1", "file", "--title", title, "--body", replay_probe.write_text(work, "body.md", BODY), "--label", "scope:x").rsplit("/", 1)[-1].removesuffix(".json")

        def holders(number):
            return use("w1:p1", "read", number).split("holders:")[1].splitlines()[0].strip()

        for case, pane, label in (("part-held", "w1:p2", "held"), ("part-other", "w1:p1", "other")):
            parent, part = filed(f"Split the {label} task"), filed(f"Do a {label} part")
            use("w1:p1", "decide", parent, "--decision", "w-worker holds this.", "--holders", "w-worker")
            body = use("w1:p1", "read", parent, "--body")
            sha = use("w1:p1", "read", parent).split("body sha:")[1].split()[0]
            taken = filed(f"Do a taken {label} part")
            use("w1:p1", "decide", taken, "--decision", "w-other holds this.", "--holders", "w-other")
            edited = replay_probe.write_text(work, f"{label}.md", body.rstrip("\n") + f"\n2. [task] #{part} Do a {label} part\n3. [task] #{taken} Do a taken {label} part\n")
            edit = use(pane, "edit", parent, "--body", edited, "--reason", "name a part", "--base", sha)
            found = holders(part)
            cases.step(case, found == ("w-worker" if label == "held" else ""), (found, edit))
            if label == "held":
                cases.step("part-taken", "w-other" in holders(taken) and "w-worker" not in holders(taken), (holders(taken), edit))
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
