#!/usr/bin/env python3
"""Replay the lines a manager's heartbeat once printed to no purpose, on a scratch repository with a git board and landing and the fake herdr, with the real heartbeat
monitor run as the manager for a set number of polls, and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`; exit 1 on any fail.
Each case is a class of line found in past managers' transcripts (#1202):
- idle-again, blocked-again: a worker that goes back to idle, or to the same prompt, after working is named again, since each return is news to the manager; a countdown or a footer hint that comes and goes in the prompt does not make it a new line
- probe-quiet: a session with no `-worker` or `-sentinel` name, such as a worker's `probe-end-manager-49609`, gets no `idle` or `blocked` line
- blocked-prompt, blocked-empty: a blocked pane names its prompt's choices; one showing an empty input under a banner gets no line
- merged-later: a merged change is not named while its worker holds an open task, and the worker's `idle` line is named once
- merged-nothing-open: a merged change is named once its worker holds nothing open, and then without an `idle` line beside it, on a blocked pane with no prompt too
- idle-waits: no `idle` line for a worker whose tasks wait on an open task or on an answer, whose `answer` line is its line
- idle-background: no `idle` line while the worker's transcript shows a background command still running
- answer-stale: no `answer` line for a question answered while the heartbeat makes its lines, after its read of the board
- feed-steps: no `feed` line for a worker's `REPORTED: criteria at` or `REPORTED: task filed`
- feed-own: no `feed` line for a report this manager posted through use-board.py

usage: replay-heartbeat-lines.py [--verbose]
`--verbose` prints each use-board.py call and its output on stderr."""
import json
import pathlib
import shlex
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = ROOT / "skills" / "kick-off" / "scripts"
USE_LANDING = SCRIPTS.parent / "references" / "adapters" / "landing-git" / "scripts" / "use-landing.py"
PROMPT = "Do you want to proceed?\n❯ 1. Yes\n  2. No\nEsc to cancel"
# a prompt whose countdown and footer change at each read, as Claude Code's own does
COUNTDOWN = ("│ Dangerous rm operation in `rm $M/$f.md`\n⚠ Claude Code will automatically deny this request in {left}, to avoid blocking\nDo you want to proceed?\n"
             "❯ 1. Yes\n  2. No\n{hint}")
HINTS = (("1:35", "Esc to cancel"), ("0:35", "Esc to cancel · Tab to amend · ctrl+x ctrl+k twice to stop background agents"))
POLLS = 12  # a flipping agent returns about every four polls, so twelve show each return twice
VERBOSE = False
manager = replay_probe.agent("x-manager", 1, "working")


class Team:
    def __init__(self, work):
        self.work, self.sandbox = work, replay_probe.Sandbox(work, [manager])

    def use(self, *argv, pane="w1:p1"):
        done = self.sandbox.python(SCRIPTS / "use-board.py", *argv, pane=pane)
        if VERBOSE:
            print(f"$ use-board.py {' '.join(map(str, argv))}\n{done.stdout}{done.stderr}", file=sys.stderr)
        return done.stdout.strip()

    def file(self, title, holder=None, depends=()):
        body = replay_probe.write_text(self.work, "body.md", "Probe the heartbeat.\n")
        number = self.use("file", "--title", title, "--body", body, "--label", "scope:x", "--depends", " ".join(depends)).rsplit("/", 1)[-1].removesuffix(".json")
        if holder:
            self.use("hold", number, "--holders", holder)
        return number

    def herdr(self, read=""):
        """A herdr that runs READ, a shell line, before it passes each call to the fake herdr, which checks and answers it."""
        replay_probe.write_text(self.sandbox.bin, "herdr", f'#!/bin/sh\n{read}\nexec "{replay_probe.FAKE_HERDR / "herdr"}" "$@"\n').chmod(0o755)

    def heartbeat(self, *agents, polls=3):
        """The lines the manager's monitor printed in POLLS polls with AGENTS live beside it, and its exit when not 0."""
        self.sandbox.herdr([manager, *agents])
        done = self.sandbox.python(replay_probe.MONITOR, "--polls", polls, pane="w1:p1", timeout=120, TEAMWORK_MONITOR_POLL="0.1")
        return done.stdout.splitlines() + ([] if done.returncode == 0 else [f"exit {done.returncode}: {done.stderr}"])


def about(output, name):
    return [line for line in output if name in line]


def monitor_cases(team, cases):
    count = team.work / "reads"
    # each read of the counting pane shows the next countdown and footer, through the fake herdr, which still checks the call
    team.herdr(f'if [ "$1 $2 $3" = "agent read w1:p8" ]; then\n  "{replay_probe.FAKE_HERDR / "herdr"}" "$@" > /dev/null || exit 1\n  echo x >> "{count}"\n'
               + "".join(f'  [ $(( $(wc -l < "{count}") % 2 )) = {at % 2} ] && printf %s {shlex.quote(COUNTDOWN.format(left=left, hint=hint))} && exit 0\n'
                         for at, (left, hint) in enumerate(HINTS, 1)) + "fi")
    team.file("Probe a held task", holder="flap-worker")
    out = team.heartbeat(replay_probe.agent("flap-worker", 2, "idle", flip=True, period=4), replay_probe.agent("again-worker", 7, "blocked", screen=PROMPT, flip="blocked", period=4),
                         replay_probe.agent("probe-end-manager-1", 3, "idle"), replay_probe.agent("probe-prompt", 4, "blocked", screen=PROMPT),
                         replay_probe.agent("empty-worker", 5, "blocked", screen="❯ \n\n  Update installed · restart to apply"),
                         replay_probe.agent("prompt-worker", 6, "blocked", screen=PROMPT), replay_probe.agent("count-worker", 8, "blocked", screen=PROMPT), polls=POLLS)
    (team.sandbox.bin / "herdr").unlink()
    cases.step("idle-again", len(about(out, "idle flap-worker")) >= 2, "\n".join(out))
    counted = about(out, "blocked count-worker")
    cases.step("blocked-again", len(about(out, "blocked again-worker")) >= 2 and len(counted) == 1 and "1. Yes" in counted[0] and "in …" in counted[0]
               and count.read_text().count("x") >= 2, "\n".join(out))
    cases.step("probe-quiet", not about(out, "probe-"), "\n".join(about(out, "probe-")))
    cases.step("blocked-empty", not about(out, "empty-worker"), "\n".join(about(out, "empty-worker")))
    cases.step("blocked-prompt", any("blocked prompt-worker" in line and "1. Yes" in line and "Esc to cancel" in line for line in out), "\n".join(out))


def line_cases(team, cases):
    sandbox = team.sandbox
    busy = team.file("Probe a free task", holder="m-worker")
    sandbox.git("switch", "-q", "-c", "m-worker")
    sandbox.git("commit", "-q", "--allow-empty", "-m", "the probe change")
    sandbox.git("switch", "-q", "main")
    change = sandbox.python(USE_LANDING, "change", "m-worker", "Probe a change", replay_probe.write_text(team.work, "change.md", "Probe it.\n")).stdout.strip().rsplit("/", 1)[-1].removesuffix(".json")
    merged = sandbox.python(USE_LANDING, "merge", change, sandbox.git("rev-parse", "m-worker").strip())
    out = team.heartbeat(replay_probe.agent("m-worker", 2, "idle"))
    cases.step("merged-later", not about(out, "merged") and len(about(out, "idle m-worker")) == 1, "\n".join([merged.stdout + merged.stderr] + out))
    team.use("hold", busy, "--holders", "")  # the worker's task is done
    out = team.heartbeat(replay_probe.agent("m-worker", 2, "idle"))
    stuck = team.heartbeat(replay_probe.agent("m-worker", 2, "blocked", screen="❯ \n\n  Update installed"))  # no prompt on a blocked pane hides nothing
    cases.step("merged-nothing-open", len(about(out, f"merged #{change} by m-worker: it holds nothing open")) == 1 and not about(out, "idle m-worker")
               and len(about(stuck, f"merged #{change}")) == 1, "\n".join(out + ["--"] + stuck))

    first = team.file("Probe a task others wait on", holder="o-worker")
    waits = team.file("Probe a waiting task", holder="w-worker", depends=[first])
    asks = team.file("Probe an asking task", holder="a-worker")
    asked = team.use("comment", asks, "--blocked", "which way?", pane="w1:p3")
    waiting = [replay_probe.agent("w-worker", 2, "idle"), replay_probe.agent("a-worker", 3, "idle"), replay_probe.agent("o-worker", 4, "working")]
    out = team.heartbeat(*waiting)
    cases.step("idle-waits", not about(out, "idle w-worker") and not about(out, "idle a-worker") and about(out, f"answer #{asks}") and waits, "\n".join(out))

    # the manager answers while its heartbeat makes its lines, after the poll's read of the board, as the tabs are listed
    answer = f"{sys.executable} {SCRIPTS / 'use-board.py'} decide {asks} --decision 'this way' --answers '{asked}'"
    team.herdr(f'if [ "$1 $2" = "tab list" ] && [ ! -e "{team.work / "answered"}" ]; then\n  touch "{team.work / "answered"}"\n  {answer} > "{team.work / "answered"}" 2>&1\nfi')
    out = team.heartbeat(*waiting, polls=1)
    (sandbox.bin / "herdr").unlink()
    cases.step("answer-stale", not about(out, f"answer #{asks}") and "/" in (team.work / "answered").read_text(), "\n".join(out + [(team.work / "answered").read_text()]))

    transcript = sandbox.config / "projects" / "p" / "sess1.jsonl"
    transcript.parent.mkdir(parents=True)
    started = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]}},
               {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "Command running in background with ID: abc"}]}}]
    transcript.write_text("".join(json.dumps(record) + "\n" for record in started))
    team.file("Probe a task a harness runs", holder="b-worker")
    background = replay_probe.agent("b-worker", 2, "idle", agent_session={"value": "sess1"})
    running = team.heartbeat(background)
    replayed = {"type": "api-request-blob", "message": {"content": started[0]["message"]["content"] + started[1]["message"]["content"]}}  # a request blob repeats old tool results
    with transcript.open("a") as out:
        out.write(json.dumps({"type": "queue-operation", "content": "<task-id>abc</task-id><status>completed</status>"}) + "\n" + json.dumps(replayed) + "\n")
    ended = team.heartbeat(background)
    cases.step("idle-background", not about(running, "idle b-worker") and len(about(ended, "idle b-worker")) == 1, "\n".join(running + ["--"] + ended))


def feed_cases(team, cases):
    sandbox = team.sandbox
    root = team.file("Probe a root the worker reports on", holder="r-worker")
    sandbox.herdr([manager, replay_probe.agent("r-worker", 9, "working")])
    with sandbox.monitor("w1:p1", 20, team.work / "feed.log") as live:
        # a first read feeds nothing old, and a manager's poll lists the sessions once, and once more before a line, so a third list opens its second poll at the latest
        live.until(lambda: live.lists() >= 3)
        for line in ("criteria at 0123abc", "task filed", "landed in the probe change"):
            team.use("comment", root, "--reported", line, pane="w1:p9")
        mine = team.use("comment", root, "--reported", "the manager's own note")
        code = live.end(timeout=120)
    fed = [line for line in live.text().splitlines() if line.startswith("feed ")]
    said = " ".join(fed) + ("" if code == 0 else f" exit {code}")
    cases.step("feed-steps", "landed in the probe change" in said and "criteria at" not in said and "task filed" not in said and code == 0, live.text())
    cases.step("feed-own", fed and all(line.startswith(f"feed #{root} ") for line in fed) and "own note" not in said and mine, live.text())


def main(args):
    global VERBOSE
    if any(argument != "--verbose" for argument in args):
        print(__doc__, file=sys.stderr)
        return 2
    VERBOSE = bool(args)
    cases = replay_probe.Cases()
    with replay_probe.scratch("heartbeat-lines-") as work:
        team = Team(work)
        monitor_cases(team, cases)
        line_cases(team, cases)
        feed_cases(team, cases)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
