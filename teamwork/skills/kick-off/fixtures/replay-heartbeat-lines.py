#!/usr/bin/env python3
"""Replay the lines a manager's heartbeat once printed to no purpose, on a temporary repository with a files board, git landing and the fake herdr
beside this file, and print `ok <case>` or `fail <case>: <what it saw>` per case; exit 1 on any fail. Each case is a class of line found in
past managers' transcripts (#1202):
- flap-once: an idle worker whose status flips at every poll is named once by the running monitor (teamwork-manager's transcript
  6a7e0b9a, `idle work-model-worker` 32 times in 2 h); flap-fuzz: for random presences a line prints again only after 5 polls without it
- probe-quiet: a session with no `-worker` or `-sentinel` name, such as a worker's `probe-end-manager-49609`, gets no `idle` or `blocked` line
- blocked-prompt, blocked-empty: a blocked pane names its prompt's choices; one showing an empty input under a banner gets no line
- merged-later: a merged change is named once its worker holds nothing open, and then without an `idle` line beside it
- idle-waits: no `idle` line for a worker whose tasks wait on an open task or on an answer, whose `answer` line is its line
- idle-background: no `idle` line while the worker's transcript shows a background command still running
- answer-stale: no `answer` line for a question the board already answers, though the kept read predates the answer
- feed-steps: no `feed` line for a worker's `REPORTED: criteria at` or `REPORTED: task filed`
- feed-own: no `feed` line for a report this manager posted through use-board.py

usage: replay-heartbeat-lines.py [--verbose] [--verdict | --cited]
`--verdict` prints only `PASS` when all 12 cases ran and passed, else `FAIL`; `--cited` prints only `PASS` when each of the 12 names a transcript or an issue it came from, else `FAIL`."""
import json
import os
import pathlib
import random
import re
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPTS = HERE.parent / "scripts"
work = pathlib.Path(tempfile.mkdtemp(prefix="heartbeat-lines-"))
repo = work / "repo"
STATE = work / "herdr.json"
os.environ.update({"TEAMWORK_BOARD": "files", "TEAMWORK_BOARD_DIR": str(work / "board"), "TEAMWORK_LANDING": "git", "CLAUDE_CONFIG_DIR": str(work / "claude"),
                   "GIT_CONFIG_GLOBAL": str(work / "gitconfig"), "GIT_AUTHOR_NAME": "probe", "GIT_AUTHOR_EMAIL": "probe@example.com",
                   "GIT_COMMITTER_NAME": "probe", "GIT_COMMITTER_EMAIL": "probe@example.com", "FAKE_HERDR_STATE": str(STATE),
                   "PATH": f"{HERE / 'fake-herdr'}:{os.environ['PATH']}", "HERDR_PANE_ID": "w1:p1"})
sys.path.insert(0, str(ROOT / "lib"))
failed = []
passed = []
QUIET = False
VERBOSE = False
# where each case was found: a manager's transcript under ~/.claude/projects/-Users-hyungmokim-workspace-plugins/ by its first 8 characters, or an issue
SOURCES = {"flap-once": "transcript 6a7e0b9a, idle work-model-worker 32 times", "flap-fuzz": "transcript 6a7e0b9a, answer #1187 12 times in 2 h",
           "probe-quiet": "transcripts 6a7e0b9a probe-end-manager-49609 and 43a6f00e probe-panes-1792244756", "blocked-empty": "issue #1202 body, an empty input under a banner",
           "blocked-prompt": "transcript 84bfcb25, a prompt cut to a row of dashes", "merged-later": "transcript 6a7e0b9a, merged #1190 13 times while its worker held open tasks",
           "merged-nothing-open": "transcript 6a7e0b9a, merged #1197", "idle-waits": "transcript 6a7e0b9a, idle work-model-worker while #1187 waited on the owner",
           "idle-background": "issue #1202 body, a background harness and a subagent", "answer-stale": "issue #1202 body, answer after decide; transcript 6a7e0b9a answer #1187",
           "feed-steps": "transcript 6a7e0b9a, feed #1199 REPORTED: criteria at", "feed-own": "transcript 6a7e0b9a, feed #1196 of the manager's own report"}


def step(name, ok, detail=""):
    if not QUIET:
        print(f"ok {name} <- {SOURCES[name]}" if ok else f"fail {name}: {str(detail).strip()}", flush=True)
    (passed if ok else failed).append(name)


def agent(name, pane, status, **more):
    return {"name": name, "pane_id": f"w1:p{pane}", "tab_id": f"w1:t{pane}", "workspace_id": "w1", "agent": "claude", "agent_status": status,
            "interactive_ready": True, **more}


def herdr(*agents):
    STATE.write_text(json.dumps({"n": 20, "agents": list(agents), "tabs": [{"tab_id": a["tab_id"], "workspace_id": "w1", "label": a["name"]} for a in agents]}))
    return list(agents)


def use(*args, pane="w1:p1"):
    process = subprocess.run([str(SCRIPTS / "use-board.py"), *map(str, args)], cwd=repo, capture_output=True, text=True, env={**os.environ, "HERDR_PANE_ID": pane})
    if VERBOSE:
        print(f"$ use-board.py {' '.join(map(str, args))}\n{process.stdout}{process.stderr}", file=sys.stderr)
    return process.stdout.strip()


def text(name, body):
    path = work / name
    path.write_text(body)
    return path


def file(title, body="", holder=None):
    number = use("file", title, text("body.md", f"{body}\n"), "scope:x").rsplit("/", 1)[-1].removesuffix(".json")
    if holder:
        use("decide", number, text("hold.md", f"DECIDED: {holder} holds this.\n\n```teamwork\nholders: {holder}\n```\n"))
    return int(number)


def lines(listed, issues, pulls=(), feed=(), fed=None):
    import board
    import team_gaps
    fresh = [board.fresh(number) for number in issues]
    data = {"found": fresh, "everything": fresh, "prs": list(pulls), "outside": [], "feed": list(feed), "links": []}
    return team_gaps.manager_actions({"name": "x-manager", "workspace_id": "w1"}, listed, data, set() if fed is None else fed)


def about(output, name):
    return [line for line in output if name in line]


def run_monitor(seconds):
    log = work / "monitor.log"
    live = subprocess.Popen([str(ROOT / "monitors" / "print-team-gaps.py")], cwd=repo, env={**os.environ, "MONITOR_POLL": "0.3"}, stdout=log.open("w"), stderr=subprocess.STDOUT)
    time.sleep(seconds)
    live.kill()
    live.wait()
    return log.read_text().splitlines()


def flap_cases():
    prompt = "Do you want to proceed?\n❯ 1. Yes\n  2. No\nEsc to cancel"
    herdr(agent("x-manager", 1, "working"), agent("flap-worker", 2, "idle", flip=True), agent("probe-end-manager-1", 3, "idle"),
          agent("probe-prompt", 4, "blocked", screen=prompt), agent("empty-worker", 5, "blocked", screen="❯ \n\n  Update installed · restart to apply"),
          agent("prompt-worker", 6, "blocked", screen=prompt))
    file("Probe a held task", holder="flap-worker")
    out = run_monitor(7)
    step("flap-once", len(about(out, "idle flap-worker")) == 1, "\n".join(out))
    step("probe-quiet", not about(out, "probe-"), "\n".join(about(out, "probe-")))
    step("blocked-empty", not about(out, "empty-worker"), "\n".join(about(out, "empty-worker")))
    step("blocked-prompt", any("blocked prompt-worker" in line and "1. Yes" in line and "Esc to cancel" in line for line in out), "\n".join(out))


def fuzz_case():
    import new_lines
    random.seed(1202)
    bad = []
    for _ in range(300):
        names = ["a", "b", "c"]
        polls = [[n for n in names if random.random() < 0.5] for _ in range(40)]
        quiet, printed = new_lines.NewLines(), {n: 0 for n in names}
        for present in polls:
            for line in quiet.update(present):
                printed[line] += 1
        for n in names:
            gap, expected = new_lines.FORGET_POLLS, 0  # a first sight prints, as does one after FORGET_POLLS polls without it
            absent = gap
            for present in polls:
                if n in present:
                    expected += absent >= gap
                    absent = 0
                else:
                    absent += 1
            if printed[n] != expected:
                bad.append((n, polls, printed[n], expected))
    step("flap-fuzz", not bad, bad[:1])


def line_cases():
    import team_gaps
    team_gaps.tabs = lambda workspace: []
    busy = file("Probe a free task", holder="m-worker")
    pulls = [{"number": 5, "headRefName": "m-worker", "mergedAt": "2026-11-04T00:00:00Z"}]
    listed = herdr(agent("x-manager", 1, "working"), agent("m-worker", 2, "idle"))
    out = lines(listed, [busy], pulls)
    step("merged-later", not about(out, "merged") and len(about(out, "idle m-worker")) == 1, "\n".join(out))
    out = lines(listed, [], pulls)
    step("merged-nothing-open", len(about(out, "merged #5 by m-worker: it holds nothing open")) == 1 and not about(out, "idle m-worker"), "\n".join(out))

    first = file("Probe a task others wait on", holder="o-worker")
    waits = file("Probe a waiting task", f"```teamwork\ndepends on: #{first}\n```", holder="w-worker")
    asks = file("Probe an asking task", holder="a-worker")
    use("comment", asks, text("ask.md", "BLOCKED: which way?\n"))
    listed = herdr(agent("x-manager", 1, "working"), agent("w-worker", 2, "idle"), agent("a-worker", 3, "idle"), agent("o-worker", 4, "working"))
    out = lines(listed, [first, waits, asks])
    step("idle-waits", not about(out, "idle w-worker") and not about(out, "idle a-worker") and about(out, f"answer #{asks}"), "\n".join(out))

    stale = [__import__("board").fresh(asks)]
    asked = stale[0]["comments"][-1]["url"]
    use("decide", asks, text("answer.md", f"DECIDED: this way\n\n```decision\ndecision: this way\ndecided by: x-manager\ndoor: two-way\nanswers: {asked}\n```\n"))
    import board
    kept = board.fresh
    data = {"found": stale, "everything": stale, "prs": [], "outside": [], "feed": [], "links": []}
    out = team_gaps.manager_actions({"name": "x-manager", "workspace_id": "w1"}, listed, data, set())
    step("answer-stale", not about(out, f"answer #{asks}"), "\n".join(out))
    board.fresh = kept

    transcript = pathlib.Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects" / "p" / "sess1.jsonl"
    transcript.parent.mkdir(parents=True)
    started = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]}},
               {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "Command running in background with ID: abc"}]}}]
    transcript.write_text("".join(json.dumps(record) + "\n" for record in started))
    free = file("Probe a task a harness runs", holder="b-worker")
    listed = herdr(agent("x-manager", 1, "working"), agent("b-worker", 2, "idle", agent_session={"value": "sess1"}))
    running = lines(listed, [free])
    transcript.write_text(transcript.read_text() + json.dumps({"type": "queue-operation", "content": "<task-id>abc</task-id><status>completed</status>"}) + "\n")
    ended = lines(listed, [free])
    step("idle-background", not about(running, "idle b-worker") and len(about(ended, "idle b-worker")) == 1, "\n".join(running + ["--"] + ended))


def feed_cases():
    import board
    import team_gaps
    root = file("Probe a root the worker reports on", holder="r-worker")
    herdr(agent("x-manager", 1, "working"), agent("r-worker", 9, "working"))
    for body in ("REPORTED: criteria at 0123abc\n", "REPORTED: task filed\n", "REPORTED: landed in the probe change\n"):
        use("comment", root, text("report.md", body), pane="w1:p9")
    posted = team_gaps.feed_read("x-manager", "1970-01-01T00:00:00Z") or []
    step("feed-steps", [comment["body"].strip() for _, comment in posted] == ["REPORTED: landed in the probe change"], posted)

    mine = use("comment", root, text("mine.md", "REPORTED: the manager's own note\n"))
    posted = team_gaps.feed_read("x-manager", "1970-01-01T00:00:00Z") or []
    listed = herdr(agent("x-manager", 1, "working"))
    out = lines(listed, [root], feed=posted, fed=set())
    fed = [line for line in out if line.startswith("feed ")]
    step("feed-own", len(fed) == 1 and "landed in the probe change" in fed[0] and "own note" not in fed[0] and mine, "\n".join(out))
    board.fresh(root)


def main(args):
    global VERBOSE, QUIET
    flags = [argument for argument in args if argument.startswith("--")]
    if any(argument not in ("--verbose", "--verdict", "--cited") for argument in args) or "--verdict" in args and "--cited" in args:
        print(__doc__, file=sys.stderr)
        return 2
    VERBOSE = "--verbose" in flags
    QUIET = "--verdict" in flags or "--cited" in flags
    repo.mkdir()
    for argv in (["init", "-q", "-b", "main"], ["commit", "-q", "--allow-empty", "-m", "start"]):
        subprocess.run(["git", *argv], cwd=repo, check=True)
    os.chdir(repo)
    flap_cases()
    fuzz_case()
    line_cases()
    feed_cases()
    if "--cited" in flags:
        cited = len(passed) == len(SOURCES) == 12 and all(re.match(r"(transcripts? [0-9a-f]{8}|issue #\d+)", SOURCES[name]) for name in passed)
        print("PASS" if cited else "FAIL")
    elif "--verdict" in flags:
        print("PASS" if len(passed) == len(SOURCES) == 12 and not failed else "FAIL")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
