#!/usr/bin/env python3
"""Build fixture transcripts and facets in a temporary config folder, run dejavu's two scripts on them, and print one line
per step and `probe: <passed> of <steps> steps pass`; exit 0 only when all pass.

usage: probe-dejavu.py"""
import glob
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
SESSIONS = str(SCRIPTS / "list-sessions.py")
REPEATS = str(SCRIPTS / "list-repeats.py")
NOW = time.time()
DAY = 86400
TMP = tempfile.mkdtemp(prefix="probe-dejavu-")
CONFIG = os.path.join(TMP, "config")
DATA = os.path.join(TMP, "data")
ENV = dict(os.environ, CLAUDE_CONFIG_DIR=CONFIG)
results = []


def step(name, ok, detail=""):
    results.append(bool(ok))
    print(f"ok {name}" if ok else f"fail {name}: {detail.strip()}")


def stamp(seconds):
    return time.strftime("%Y-%m-%dT%H:%M:%S.123Z", time.gmtime(seconds))


def session(project, session_id, seconds, turns, entrypoint="cli"):
    """Write a transcript; turns are ('owner', text) | ('agent', text) | ('fail', tool, error text[, command])
    | ('answer', question, [option labels], the owner's answer)."""
    folder = os.path.join(CONFIG, "projects", project)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{session_id}.jsonl")
    with open(path, "w") as out:
        for k, turn in enumerate(turns):
            base = {"sessionId": session_id, "timestamp": stamp(seconds + k), "entrypoint": entrypoint, "cwd": "/x"}
            if turn[0] == "owner":
                rows = [dict(base, type="user", origin={"kind": "human"}, message={"role": "user", "content": turn[1]})]
            elif turn[0] == "agent":
                rows = [dict(base, type="assistant", message={"role": "assistant",
                                                              "content": [{"type": "text", "text": turn[1]}]})]
            elif turn[0] == "answer":
                use = f"toolu_{session_id[:6]}_{k}"
                asked = {"question": turn[1], "header": "h", "options": [{"label": label, "description": "d"} for label in turn[2]]}
                rows = [dict(base, type="assistant", message={"role": "assistant", "content": [
                            {"type": "tool_use", "id": use, "name": "AskUserQuestion", "input": {"questions": [asked]}}]}),
                        dict(base, type="user", toolUseResult={"questions": [asked], "answers": {turn[1]: turn[3]}},
                             message={"role": "user", "content": [
                                 {"type": "tool_result", "tool_use_id": use, "content": f"answered: {turn[3]}"}]})]
            else:
                use = f"toolu_{session_id[:6]}_{k}"
                rows = [dict(base, type="assistant", message={"role": "assistant", "content": [
                            {"type": "tool_use", "id": use, "name": turn[1],
                             "input": {"command": turn[3]} if len(turn) > 3 else {}}]}),
                        dict(base, type="user", message={"role": "user", "content": [
                            {"type": "tool_result", "tool_use_id": use, "is_error": True, "content": turn[2]}]})]
            for row in rows:
                out.write(json.dumps(row) + "\n")
    os.utime(path, (seconds + len(turns), seconds + len(turns)))
    return path


def memory_under(out, kind, word):
    block = re.search(rf"^{kind}.*{word}.*\n((?:  .*\n)*)", out, re.M | re.I)
    return block.group(1) if block else ""


def run(*args):
    done = subprocess.run([sys.executable, *args], capture_output=True, text=True, env=ENV, timeout=120)
    return done.stdout + done.stderr


def snapshot():
    """Hash of every file under the config folder, the data folder excluded."""
    found = {}
    for path in glob.glob(os.path.join(CONFIG, "**"), recursive=True):
        if os.path.isfile(path):
            found[path] = hashlib.sha256(open(path, "rb").read()).hexdigest()
    return found


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    # memory a run must leave alone
    os.makedirs(os.path.join(CONFIG, "memory-home"), exist_ok=True)
    with open(os.path.join(CONFIG, "settings.json"), "w") as handle:
        handle.write(json.dumps({"autoMemoryDirectory": os.path.join(CONFIG, "memory-home")}))
    os.makedirs(os.path.join(CONFIG, "projects", "-r-alpha", "memory"), exist_ok=True)
    with open(os.path.join(CONFIG, "projects", "-r-alpha", "memory", "MEMORY.md"), "w") as handle:
        handle.write("- [Tool trap](trap.md) — Bash: boom at <path>\n- [Ask](ask.md) — stops to ask when the rule says act\n")

    # tool repeat: 3 recent sessions in 2 repos, paths and numbers differ, so masking must merge them
    for i, project in enumerate(["-r-alpha", "-r-alpha", "-r-beta"]):
        session(project, f"aaaa000{i}-0000-0000-0000-000000000000", NOW - DAY * (i + 0.5),
                [("owner", "do it"), ("fail", "Bash", f"Exit code 1\nboom at /tmp/x{i}/y.txt line {i + 10} sha {'abcdef1' if i else '1234567'}"
                                                    f" see https://e.x/{i} for 'value{i}'\nThis hook comes from plugin h{i}")])
    # not a repeat: 2 sessions only
    for i in range(2):
        session("-r-alpha", f"bbbb000{i}-0000-0000-0000-000000000000", NOW - DAY,
                [("owner", "go"), ("fail", "Edit", "twice only failure")])
    # not a repeat: 3 sessions, all older than 3 days but inside 14
    for i in range(3):
        session("-r-alpha", f"cccc000{i}-0000-0000-0000-000000000000", NOW - DAY * (5 + i),
                [("owner", "go"), ("fail", "Read", "stale only failure")])
    # dropped: bare exit code and user denied, in 3 recent sessions
    for i in range(3):
        session("-r-alpha", f"dddd000{i}-0000-0000-0000-000000000000", NOW - DAY,
                [("owner", "go"), ("fail", "Bash", "Exit code 2"),
                 ("fail", "Write", "The user doesn't want to proceed with this tool use.")])
    # classifier reason kept: 3 recent sessions
    for i in range(3):
        session("-r-alpha", f"eeee000{i}-0000-0000-0000-000000000000", NOW - DAY,
                [("owner", "go"), ("fail", "Bash", f"Permission for this action was denied by auto mode {i}. [Create Unsafe Agents]")])
    # absence probes: an ls of the path just removed, or one whose exit status is read, is no mistake; an ls of another path is
    gone = "ls: /x/gone: No such file or directory"
    for i in range(3):
        session("-r-alpha", f"a1b1000{i}-0000-0000-0000-000000000000", NOW - DAY,
                [("owner", "go"), ("fail", "Bash", f"Exit code 1\n{gone}", "rm /x/gone && ls /x/gone 2>&1"),
                 ("fail", "Bash", f"Exit code 1\n{gone}", "ls /x/gone 2>&1 || echo gone")])
        session("-r-beta", f"a2b2000{i}-0000-0000-0000-000000000000", NOW - DAY,
                [("owner", "go"), ("fail", "Bash", f"Exit code 1\nls: /x/typo: No such file or directory", ["rm o && ls /x/typo 2>&1", "rm /x/a || ls /x/typo", "rm /x/a | ls /x/typo"][i])])
    # outside the window, and an sdk session
    session("-r-alpha", "ffff0000-0000-0000-0000-000000000000", NOW - 20 * DAY, [("owner", "old"), ("fail", "Bash", "ancient")])
    session("-r-alpha", "ffff0001-0000-0000-0000-000000000000", NOW - DAY, [("owner", "sdk"), ("agent", "x")], "sdk-cli")
    # a short session: owner text cut at 500, agent at 300
    short = session("-r-alpha", "abab0000-0000-0000-0000-000000000000", NOW - 2 * DAY,
                    [("owner", "O" * 600), ("agent", "A" * 400), ("owner", "next")])
    # a long session: every owner line kept, digest at most 30k chars
    long_turns = []
    for k in range(80):
        long_turns += [("agent", f"step {k} " + "z" * 2000), ("owner", f"OWNERLINE{k:03d} please change it")]
    session("-r-beta", "acac0000-0000-0000-0000-000000000000", NOW - 2 * DAY, long_turns)
    # an answered question with the owner's own words; a session with only its first prompt and no answer
    session("-r-alpha", "adad0000-0000-0000-0000-000000000000", NOW - 2 * DAY,
            [("agent", "pick one"), ("answer", "Which way?", ["Merge (Recommended)", "Drop"], "what is this? explain first")])
    session("-r-alpha", "aeae0000-0000-0000-0000-000000000000", NOW - 2 * DAY, [("owner", "start"), ("agent", "alone"), ("fail", "Bash", "lonely")])

    before = snapshot()
    step("due on fresh data", run(SESSIONS, "due", DATA).strip() == "due")
    first = run(SESSIONS, "map", DATA)
    digests = {os.path.basename(path)[:-4] for path in glob.glob(os.path.join(DATA, "digests", "*.txt"))}
    batches = [line for line in first.splitlines() if line.startswith("batch ")]
    step("not due right after a map", run(SESSIONS, "due", DATA).strip() == "not due")
    untouched = snapshot() == before
    step("sdk and out-of-window sessions not mapped",
         not {"ffff0000-0000-0000-0000-000000000000", "ffff0001-0000-0000-0000-000000000000"} & digests
         and "abab0000-0000-0000-0000-000000000000" in digests)
    text = open(os.path.join(DATA, "digests", "abab0000-0000-0000-0000-000000000000.txt")).read() if "abab0000-0000-0000-0000-000000000000" in digests else ""
    step("short digest cuts owner at 500 and agent at 300 chars",
         "O" * 500 in text and "O" * 501 not in text and "A" * 300 in text and "A" * 301 not in text)
    text = open(os.path.join(DATA, "digests", "acac0000-0000-0000-0000-000000000000.txt")).read() if "acac0000-0000-0000-0000-000000000000" in digests else ""
    step("long digest keeps every owner line and the agent text before it, within 30k chars",
         text and all(f"OWNERLINE{k:03d}" in text and f"step {k} " in text for k in range(80)) and len(text) <= 30000
         and "z" * 301 not in text)
    text = open(os.path.join(DATA, "digests", "adad0000-0000-0000-0000-000000000000.txt")).read() if "adad0000-0000-0000-0000-000000000000" in digests else ""
    step("an answer shows as an [ANSWER L<n>] line with its options, the recommended one marked, and the owner's own words",
         re.search(r"^\[ANSWER L\d+\]: Which way\? \| options: Merge \(Recommended\) / Drop \| answer: what is this\? explain first$", text, re.M))
    step("no digest for a session with no owner line after its first prompt and no answer, its signatures kept",
         "aeae0000-0000-0000-0000-000000000000" not in digests
         and os.path.exists(os.path.join(DATA, "stats", "aeae0000-0000-0000-0000-000000000000.json")))
    step("batches of at most 10 digests", batches and all(len(re.findall(r"\.txt\b", batch)) <= 10 for batch in batches))

    # 45 more fresh sessions: a map takes at most 40, newest first; a mapped session with a facet is not listed again
    for k in range(45):
        session("-r-gamma", f"9999{k:04d}-0000-0000-0000-000000000000", NOW - 3600 * (k + 1), [("owner", f"hi {k}"), ("owner", "go on")])
    before = snapshot()
    os.makedirs(os.path.join(DATA, "facets"), exist_ok=True)
    for session_id in digests:
        json.dump({"friction": []}, open(os.path.join(DATA, "facets", f"{session_id}.json"), "w"))
    last = os.path.join(DATA, "last-map")
    os.utime(last, (NOW - 23 * 3600, NOW - 23 * 3600)) if os.path.exists(last) else None
    not_due = run(SESSIONS, "due", DATA).strip() == "not due"
    os.utime(last, (NOW - 25 * 3600, NOW - 25 * 3600)) if os.path.exists(last) else None
    step("due flips at 24 hours after the last map, by last-map's time", not_due and run(SESSIONS, "due", DATA).strip() == "due")
    second = run(SESSIONS, "map", DATA)
    listed = set(re.findall(r"([0-9a-f]{8}-0000-0000-0000-000000000000)\.txt", second))
    step("at most 40 per map, newest first, mapped ones skipped",
         len(listed) == 40 and "99990000-0000-0000-0000-000000000000" in listed
         and "99990044-0000-0000-0000-000000000000" not in listed and not listed & digests)

    # facets: friction items for the reduce
    facets = os.path.join(DATA, "facets")
    os.makedirs(facets, exist_ok=True)
    for i in range(3):
        session_id = f"aaaa000{i}-0000-0000-0000-000000000000"
        json.dump({"friction": [{"quote": f"why did you stop {i}", "what_went_wrong": "stopped to ask", "line": 1}]},
                  open(os.path.join(facets, f"{session_id}.json"), "w"))
    out = run(REPEATS, "mistakes", DATA)
    lines = out.splitlines()
    step("tool repeat in 3 recent sessions listed, paths and numbers merged",
         any(line.startswith("tool 3 sessions") and "boom at" in line for line in lines))
    step("an ls of the path just removed or with its status read is not a repeat, an ls of another missing path is",
         [line.split(" sessions")[0] for line in lines if line.startswith("tool ") and "ls: <path>: No such file" in line] == ["tool 3"])
    step("2-session and stale signatures not listed",
         not any("twice only" in line or "stale only" in line for line in lines if line.startswith("tool ")))
    step("bare exit code, user denied and hook footer dropped; hashes, urls and quoted values masked; reason kept",
         not any(re.search(r"Exit code|doesn't want to proceed|hook comes from|abcdef1|1234567|e\.x|value\d", line)
                 for line in lines if line.startswith("tool "))
         and any(line.startswith("tool 3 sessions") and "[Create Unsafe Agents]" in line for line in lines))
    tool_memory = memory_under(out, "tool 3 sessions", "boom at")

    items = [json.loads(line) for line in open(os.path.join(DATA, "friction.jsonl"))] if os.path.exists(os.path.join(DATA, "friction.jsonl")) else []
    ids = [i.get("id") for i in items]
    mistakes = os.path.join(TMP, "mistakes.json")
    json.dump([{"name": "stops to ask when the rule says act", "ids": ids[:3]},
               {"name": "only two sessions", "ids": ids[:2]}], open(mistakes, "w"))
    out = run(REPEATS, "mistakes", DATA, "--groups", mistakes)
    step("friction items written with ids", len(ids) == 3 and all(ids))
    step("mistake counted by script: 3 sessions listed, 2 not",
         any(line.startswith("mistake 3 sessions") and "stops to ask" in line for line in out.splitlines())
         and not any("only two sessions" in line for line in out.splitlines() if line.startswith("mistake")))
    step("memory line naming a repeat is shown, for tool and mistake repeats",
         "trap.md" in tool_memory and "ask.md" in memory_under(out, "mistake 3 sessions", "stops to ask"))

    key = next((line.split(": ", 1)[1] for line in lines if line.startswith("tool 3 sessions") and "boom at" in line), "none")
    printed = re.search(r"last seen (\S+),", run(REPEATS, "mistakes", DATA).split(key, 1)[-1])
    run(REPEATS, "mistakes", DATA, "--record", "https://github.com/o/r/issues/1", printed.group(1) if printed else "0", key)
    fresh = [line for line in run(REPEATS, "mistakes", DATA).splitlines() if "boom at" in line and line.startswith("tool ")]
    json.dump({key: {"url": "https://github.com/o/r/issues/1", "last_seen": NOW - 10 * DAY}}, open(os.path.join(DATA, "filed.json"), "w"))
    stale = [line for line in run(REPEATS, "mistakes", DATA).splitlines() if "boom at" in line and line.startswith("tool ")]
    step("a recorded repeat carries its url; `seen since` only when sighted after its recorded last sighting",
         fresh and "filed https://github.com/o/r/issues/1" in fresh[0] and "seen since" not in fresh[0]
         and stale and "filed https://github.com/o/r/issues/1" in stale[0] and "seen since" in stale[0])
    step("no file outside the data folder changed", untouched and snapshot() == before)

    print(f"probe: {sum(results)} of {len(results)} steps pass")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
