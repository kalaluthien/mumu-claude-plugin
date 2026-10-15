#!/usr/bin/env python3
"""usage: probe-dejavu.py

Build fixture transcripts and facets in a temporary config dir, run dejavu's two scripts on them, and print one line
per case and `probe: <passed> of <cases> cases pass`; exit 0 only when all pass."""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../.."))
SESSIONS = os.path.join(ROOT, "homework/skills/wrap-up/scripts/list-sessions.py")
REPEATS = os.path.join(ROOT, "homework/skills/wrap-up/scripts/list-repeats.py")
NOW = time.time()
DAY = 86400
TMP = tempfile.mkdtemp(prefix="probe-dejavu-")
CONFIG = os.path.join(TMP, "config")
DATA = os.path.join(TMP, "data")
ENV = dict(os.environ, CLAUDE_CONFIG_DIR=CONFIG)
results = []


def case(name, ok):
    results.append(bool(ok))
    print(f"{'pass' if ok else 'FAIL'}: {name}")


def stamp(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S.123Z", time.gmtime(t))


def session(project, sid, t, turns, entrypoint="cli"):
    """Write a transcript; turns are ('owner', text) | ('agent', text) | ('fail', tool, error text)."""
    folder = os.path.join(CONFIG, "projects", project)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{sid}.jsonl")
    with open(path, "w") as out:
        for k, turn in enumerate(turns):
            base = {"sessionId": sid, "timestamp": stamp(t + k), "entrypoint": entrypoint, "cwd": "/x"}
            if turn[0] == "owner":
                rows = [dict(base, type="user", origin={"kind": "human"}, message={"role": "user", "content": turn[1]})]
            elif turn[0] == "agent":
                rows = [dict(base, type="assistant", message={"role": "assistant",
                                                              "content": [{"type": "text", "text": turn[1]}]})]
            else:
                use = f"toolu_{sid[:6]}_{k}"
                rows = [dict(base, type="assistant", message={"role": "assistant", "content": [
                            {"type": "tool_use", "id": use, "name": turn[1], "input": {}}]}),
                        dict(base, type="user", message={"role": "user", "content": [
                            {"type": "tool_result", "tool_use_id": use, "is_error": True, "content": turn[2]}]})]
            for row in rows:
                out.write(json.dumps(row) + "\n")
    os.utime(path, (t + len(turns), t + len(turns)))
    return path


def run(*args):
    done = subprocess.run([sys.executable, *args], capture_output=True, text=True, env=ENV, timeout=120)
    return done.stdout + done.stderr


def snapshot():
    """Hash of every file under the config dir, the data dir excluded."""
    found = {}
    for path in glob.glob(os.path.join(CONFIG, "**"), recursive=True):
        if os.path.isfile(path):
            found[path] = hashlib.sha256(open(path, "rb").read()).hexdigest()
    return found


# memory a run must leave alone
os.makedirs(os.path.join(CONFIG, "projects", "-r-alpha", "memory"), exist_ok=True)
with open(os.path.join(CONFIG, "projects", "-r-alpha", "memory", "MEMORY.md"), "w") as f:
    f.write("- [Tool trap](trap.md) — Bash: boom at <path>\n- [Gate](gate.md) — always run the gate first\n")

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
# outside the window, and an sdk session
session("-r-alpha", "ffff0000-0000-0000-0000-000000000000", NOW - 20 * DAY, [("owner", "old"), ("fail", "Bash", "ancient")])
session("-r-alpha", "ffff0001-0000-0000-0000-000000000000", NOW - DAY, [("owner", "sdk"), ("agent", "x")], "sdk-cli")
# a short session: owner text cut at 500, agent at 300
short = session("-r-alpha", "abab0000-0000-0000-0000-000000000000", NOW - 2 * DAY,
                [("owner", "O" * 600), ("agent", "A" * 400)])
# a long session: every owner line kept, digest at most 30k chars
long_turns = []
for k in range(80):
    long_turns += [("agent", f"step {k} " + "z" * 2000), ("owner", f"OWNERLINE{k:03d} please change it")]
session("-r-beta", "acac0000-0000-0000-0000-000000000000", NOW - 2 * DAY, long_turns)

before = snapshot()
case("due on fresh data", run(SESSIONS, "due", DATA).strip() == "due")
first = run(SESSIONS, "map", DATA)
digests = {os.path.basename(p)[:-4] for p in glob.glob(os.path.join(DATA, "digests", "*.txt"))}
batches = [line for line in first.splitlines() if line.startswith("batch ")]
case("not due right after a map", run(SESSIONS, "due", DATA).strip() == "not due")
untouched = snapshot() == before
case("sdk and out-of-window sessions not mapped",
     not {"ffff0000-0000-0000-0000-000000000000", "ffff0001-0000-0000-0000-000000000000"} & digests
     and "abab0000-0000-0000-0000-000000000000" in digests)
text = open(os.path.join(DATA, "digests", "abab0000-0000-0000-0000-000000000000.txt")).read() if "abab0000-0000-0000-0000-000000000000" in digests else ""
case("short digest cuts owner at 500 and agent at 300 chars",
     "O" * 500 in text and "O" * 501 not in text and "A" * 300 in text and "A" * 301 not in text)
text = open(os.path.join(DATA, "digests", "acac0000-0000-0000-0000-000000000000.txt")).read() if "acac0000-0000-0000-0000-000000000000" in digests else ""
case("long digest keeps every owner line and the agent text before it, within 30k chars",
     text and all(f"OWNERLINE{k:03d}" in text and f"step {k} " in text for k in range(80)) and len(text) <= 30000
     and "z" * 301 not in text)
case("batches of at most 10 digests", batches and all(len(re.findall(r"\.txt\b", b)) <= 10 for b in batches))

# 45 more fresh sessions: a map takes at most 40, newest first; a mapped session with a facet is not listed again
for k in range(45):
    session("-r-gamma", f"9999{k:04d}-0000-0000-0000-000000000000", NOW - 3600 * (k + 1), [("owner", f"hi {k}")])
before = snapshot()
os.makedirs(os.path.join(DATA, "facets"), exist_ok=True)
for sid in digests:
    json.dump({"friction": [], "instructions": []}, open(os.path.join(DATA, "facets", f"{sid}.json"), "w"))
last = os.path.join(DATA, "last-map")
os.utime(last, (NOW - 23 * 3600, NOW - 23 * 3600)) if os.path.exists(last) else None
not_due = run(SESSIONS, "due", DATA).strip() == "not due"
os.utime(last, (NOW - 25 * 3600, NOW - 25 * 3600)) if os.path.exists(last) else None
case("due flips at 24 hours after the last map, by last-map's time", not_due and run(SESSIONS, "due", DATA).strip() == "due")
second = run(SESSIONS, "map", DATA)
listed = set(re.findall(r"([0-9a-f]{8}-0000-0000-0000-000000000000)\.txt", second))
case("at most 40 per map, newest first, mapped ones skipped",
     len(listed) == 40 and "99990000-0000-0000-0000-000000000000" in listed
     and "99990044-0000-0000-0000-000000000000" not in listed and not listed & digests)

# facets: one instruction in 2 sessions, one in 1; friction items for the reduce
facets = os.path.join(DATA, "facets")
os.makedirs(facets, exist_ok=True)
said = [["Always run the gate first."], ["  always run the GATE first!! ", "one-off rule 1"], ["Never touch Desktop."]]
for i in range(3):
    sid = f"aaaa000{i}-0000-0000-0000-000000000000"
    json.dump({"friction": [{"quote": f"why did you stop {i}", "what_went_wrong": "stopped to ask", "line": 1}],
               "instructions": said[i]}, open(os.path.join(facets, f"{sid}.json"), "w"))
out = run(REPEATS, DATA)
lines = out.splitlines()
case("tool repeat in 3 recent sessions listed, paths and numbers merged",
     any(l.startswith("tool 3 sessions") and "boom at" in l for l in lines))
case("2-session and stale signatures not listed",
     not any("twice only" in l or "stale only" in l for l in lines if l.startswith("tool ")))
case("bare exit code, user denied and hook footer dropped; hashes, urls and quoted values masked; reason kept",
     not any(re.search(r"Exit code|doesn't want to proceed|hook comes from|abcdef1|1234567|e\.x|value\d", l)
             for l in lines if l.startswith("tool "))
     and any(l.startswith("tool 3 sessions") and "[Create Unsafe Agents]" in l for l in lines))
case("instruction in 2 sessions listed, in 1 not",
     any(l.startswith("instruction 2 sessions") and "gate" in l.lower() for l in lines)
     and not any(l.startswith("instruction") and ("one-off" in l or "Desktop" in l) for l in lines))
def memory_under(kind, word):
    block = re.search(rf"^{kind}.*{word}.*\n((?:  .*\n)*)", out, re.M | re.I)
    return block.group(1) if block else ""
case("memory line naming a repeat is shown, for tool and instruction repeats",
     "trap.md" in memory_under("tool 3 sessions", "boom at") and "gate.md" in memory_under("instruction", "gate"))

items = [json.loads(l) for l in open(os.path.join(DATA, "friction.jsonl"))] if os.path.exists(os.path.join(DATA, "friction.jsonl")) else []
ids = [i.get("id") for i in items]
mistakes = os.path.join(TMP, "mistakes.json")
json.dump([{"name": "stops to ask when the rule says act", "ids": ids[:3]},
           {"name": "only two sessions", "ids": ids[:2]}], open(mistakes, "w"))
out = run(REPEATS, DATA, "--mistakes", mistakes)
case("friction items written with ids", len(ids) == 3 and all(ids))
case("mistake counted by script: 3 sessions listed, 2 not",
     any(l.startswith("mistake 3 sessions") and "stops to ask" in l for l in out.splitlines())
     and not any("only two sessions" in l for l in out.splitlines() if l.startswith("mistake")))

key = next((l.split(": ", 1)[1] for l in lines if l.startswith("tool 3 sessions") and "boom at" in l), "none")
printed = re.search(r"last seen (\S+),", run(REPEATS, DATA).split(key, 1)[-1])
run(REPEATS, DATA, "--record", "https://github.com/o/r/issues/1", printed.group(1) if printed else "0", key)
fresh = [l for l in run(REPEATS, DATA).splitlines() if "boom at" in l and l.startswith("tool ")]
json.dump({key: {"url": "https://github.com/o/r/issues/1", "last_seen": NOW - 10 * DAY}}, open(os.path.join(DATA, "filed.json"), "w"))
stale = [l for l in run(REPEATS, DATA).splitlines() if "boom at" in l and l.startswith("tool ")]
case("a recorded repeat carries its url; `seen since` only when sighted after its recorded last sighting",
     fresh and "filed https://github.com/o/r/issues/1" in fresh[0] and "seen since" not in fresh[0]
     and stale and "filed https://github.com/o/r/issues/1" in stale[0] and "seen since" in stale[0])
case("no file outside the data dir changed", untouched and snapshot() == before)

print(f"probe: {sum(results)} of {len(results)} cases pass")
sys.exit(0 if all(results) else 1)
