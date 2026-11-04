#!/usr/bin/env python3
"""Replay the lines a manager's heartbeat once printed to no purpose, on a temporary repository with a files board, git landing and the fake herdr
beside this file, and print `ok <case>` or `fail <case>: <what it saw>` per case; exit 1 on any fail. Each case is a class of line found in
past managers' transcripts (#1202):
- idle-again, blocked-again: a worker that goes back to idle, or to the same prompt, after working is named again, since each return is news to the manager
  (teamwork-manager's transcript 6a7e0b9a, the `idle work-model-worker` line 16 times in 7.5 h; 84bfcb25, one worker's same prompt twice a minute apart)
- probe-quiet: a session with no `-worker` or `-sentinel` name, such as a worker's `probe-end-manager-49609`, gets no `idle` or `blocked` line
- blocked-prompt, blocked-empty: a blocked pane names its prompt's choices; one showing an empty input under a banner gets no line
- merged-later: a merged change is named once its worker holds nothing open, and then without an `idle` line beside it
- idle-waits: no `idle` line for a worker whose tasks wait on an open task or on an answer, whose `answer` line is its line
- idle-background: no `idle` line while the worker's transcript shows a background command still running
- answer-stale: no `answer` line for a question the board already answers, though the kept read predates the answer
- feed-steps: no `feed` line for a worker's `REPORTED: criteria at` or `REPORTED: task filed`
- feed-own: no `feed` line for a report this manager posted through use-board.py

usage: replay-heartbeat-lines.py [--verbose] [--verdict | --cited]
`--verdict` prints only `PASS` when all 12 cases ran and passed, else `FAIL`; `--cited` prints only `PASS` when each of the 12 finds its text in the transcript it names, in at least the stated number of monitor events, else `FAIL`."""
import json
import os
import pathlib
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
# where each case was found: (the transcript under ~/.claude/projects/-Users-hyungmokim-workspace-plugins/ by its first 8 characters, the text it holds,
# how many monitor events carry that text); --cited counts them in the transcript
TRANSCRIPTS = pathlib.Path("~/.claude/projects/-Users-hyungmokim-workspace-plugins").expanduser()
SOURCES = {"idle-again": ("transcript 6a7e0b9a", "idle work-model-worker: holds", 15), "blocked-again": ("transcript 84bfcb25", "once the owner says so: \u254c\u254c\u254c\u254c", 2),
           "probe-quiet": ("transcript 6a7e0b9a", "probe-end-manager-49609", 3), "blocked-empty": ("transcript 6a7e0b9a", "Update installed", 1),
           "blocked-prompt": ("transcript 84bfcb25", "once the owner says so: \u254c\u254c\u254c\u254c", 2), "merged-later": ("transcript 6a7e0b9a", "merged #1190", 6),
           "merged-nothing-open": ("transcript 6a7e0b9a", "merged #1197", 5), "idle-waits": ("transcript 6a7e0b9a", "holds #1188 #1187 #1163", 13),
           "idle-background": ("transcript 6a7e0b9a", "idle work-model-worker: holds", 15), "answer-stale": ("transcript 6a7e0b9a", "answer #1187", 6),
           "feed-steps": ("transcript 6a7e0b9a", "REPORTED: criteria at", 5), "feed-own": ("transcript 6a7e0b9a", "feed #1196", 1)}


def events(prefix, needle):
    """How many monitor events a transcript queued whose text holds NEEDLE; a transcript repeats each event in other records, so only the queued ones count."""
    count = 0
    for path in TRANSCRIPTS.glob(prefix + "*.jsonl"):
        for line in path.read_text().splitlines():
            if '"operation":"enqueue"' in line and needle in line:
                record = json.loads(line)
                count += record.get("type") == "queue-operation" and needle in record.get("content", "")
    return count


def sourced(name):
    """Whether the case's transcript holds its text in at least the stated number of monitor events, since a live transcript only gains events."""
    source, needle, count = SOURCES[name]
    return events(source.split()[1], needle) >= count


def step(name, ok, detail=""):
    if not QUIET:
        print(f"ok {name} <- {SOURCES[name][0]}" if ok else f"fail {name}: {str(detail).strip()}", flush=True)
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


def run_monitor(until):
    log = work / "monitor.log"
    live = subprocess.Popen([str(ROOT / "monitors" / "print-team-gaps.py")], cwd=repo, env={**os.environ, "MONITOR_POLL": "0.3"}, stdout=log.open("w"), stderr=subprocess.STDOUT)
    deadline = time.time() + 30
    while time.time() < deadline and not until(log.read_text()):
        time.sleep(0.2)
    time.sleep(3)  # the monitor goes on polling, so a line wrongly printed again shows
    live.kill()
    live.wait()
    return log.read_text().splitlines()


def monitor_cases():
    prompt = "Do you want to proceed?\n❯ 1. Yes\n  2. No\nEsc to cancel"
    herdr(agent("x-manager", 1, "working"), agent("flap-worker", 2, "idle", flip=True), agent("again-worker", 7, "blocked", screen=prompt, flip="blocked"), agent("probe-end-manager-1", 3, "idle"),
          agent("probe-prompt", 4, "blocked", screen=prompt), agent("empty-worker", 5, "blocked", screen="❯ \n\n  Update installed · restart to apply"),
          agent("prompt-worker", 6, "blocked", screen=prompt))
    file("Probe a held task", holder="flap-worker")
    out = run_monitor(lambda text: text.count("idle flap-worker") >= 2 and text.count("blocked again-worker") >= 2 and "blocked prompt-worker" in text)
    step("idle-again", len(about(out, "idle flap-worker")) >= 2, "\n".join(out))
    step("blocked-again", len(about(out, "blocked again-worker")) >= 2, "\n".join(out))
    step("probe-quiet", not about(out, "probe-"), "\n".join(about(out, "probe-")))
    step("blocked-empty", not about(out, "empty-worker"), "\n".join(about(out, "empty-worker")))
    step("blocked-prompt", any("blocked prompt-worker" in line and "1. Yes" in line and "Esc to cancel" in line for line in out), "\n".join(out))


def line_cases():
    import team_gaps
    team_gaps.tabs = lambda workspace: []
    busy = file("Probe a free task", holder="m-worker")
    pulls = [{"number": 5, "headRefName": "m-worker", "mergedAt": "2026-11-04T00:00:00Z"}]
    listed = herdr(agent("x-manager", 1, "working"), agent("m-worker", 2, "idle"))
    out = lines(listed, [busy], pulls)
    step("merged-later", not about(out, "merged") and len(about(out, "idle m-worker")) == 1, "\n".join(out))
    out = lines(listed, [], pulls)
    stuck = lines(herdr(agent("x-manager", 1, "working"), agent("m-worker", 2, "blocked", screen="\u276f \n\n  Update installed")), [], pulls)  # no prompt on a blocked pane hides nothing
    step("merged-nothing-open", len(about(out, "merged #5 by m-worker: it holds nothing open")) == 1 and not about(out, "idle m-worker") and len(about(stuck, "merged #5")) == 1,
         "\n".join(out + ["--"] + stuck))

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
    monitor_cases()
    line_cases()
    feed_cases()
    if "--cited" in flags:
        cited = len(passed) == len(SOURCES) == 12 and all(sourced(name) for name in passed)
        print("PASS" if cited else "FAIL")
    elif "--verdict" in flags:
        print("PASS" if len(passed) == len(SOURCES) == 12 and not failed else "FAIL")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
