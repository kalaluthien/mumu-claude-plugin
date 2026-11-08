#!/usr/bin/env python3
"""Build fixture transcripts and facets in a temporary config folder, run habit's map and reduce on them, and print one
line per step and `probe: <passed> of <steps> steps pass`; exit 0 only when all pass.

usage: probe-habit.py"""
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
HABITS = str(SCRIPTS / "list-repeats.py")
NOW = time.time()
DAY = 86400
TMP = tempfile.mkdtemp(prefix="probe-habit-")
CONFIG = os.path.join(TMP, "config")
DATA = os.path.join(TMP, "habit")
ENV = dict(os.environ, CLAUDE_CONFIG_DIR=CONFIG)
results = []


def step(name, ok, detail=""):
    results.append(bool(ok))
    print(f"ok {name}" if ok else f"fail {name}: {detail.strip()}")


def session(project, session_id, seconds, text):
    """Write a transcript of an owner line, an agent line and a second owner line, last changed at seconds."""
    folder = os.path.join(CONFIG, "projects", project)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{session_id}.jsonl")
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S.123Z", time.gmtime(seconds))
    base = {"sessionId": session_id, "timestamp": stamp, "entrypoint": "cli", "cwd": "/x"}
    with open(path, "w") as out:
        out.write(json.dumps(dict(base, type="user", origin={"kind": "human"}, message={"role": "user", "content": text})) + "\n")
        out.write(json.dumps(dict(base, type="assistant", message={"role": "assistant", "content": [{"type": "text", "text": "ok"}]})) + "\n")
        out.write(json.dumps(dict(base, type="user", origin={"kind": "human"}, message={"role": "user", "content": "go on"})) + "\n")
    os.utime(path, (seconds, seconds))
    return path


def run(*args):
    done = subprocess.run([sys.executable, *args], capture_output=True, text=True, env=ENV, timeout=120)
    return done.stdout + done.stderr


def listed(output):
    return set(re.findall(r"([0-9a-f]{8}-0000-0000-0000-000000000000)\.txt", output))


def snapshot():
    """Hash of every file under the config folder."""
    return {path: hashlib.sha256(open(path, "rb").read()).hexdigest()
            for path in glob.glob(os.path.join(CONFIG, "**"), recursive=True) if os.path.isfile(path)}


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    os.makedirs(os.path.join(CONFIG, "projects", "-r-alpha", "memory"), exist_ok=True)
    with open(os.path.join(CONFIG, "projects", "-r-alpha", "memory", "MEMORY.md"), "w") as handle:
        handle.write("- [Plain words](plain.md) — explain a made-up label before using it\n")
    # 3 owner sessions in 2 repos, one 20 days old; 62 fresh ones for the limit
    session("-r-alpha", "aaaa0000-0000-0000-0000-000000000000", NOW - DAY, "what is E1? explain")
    session("-r-beta", "aaaa0001-0000-0000-0000-000000000000", NOW - 2 * DAY, "what does that label mean")
    session("-r-alpha", "aaaa0002-0000-0000-0000-000000000000", NOW - 20 * DAY, "always answer in Korean")
    for k in range(62):
        session("-r-gamma", f"9999{k:04d}-0000-0000-0000-000000000000", NOW - 3600 * (k + 1), f"hi {k}")
    before = snapshot()

    step("due with --due-hours 168 on fresh data", run(SESSIONS, "due", DATA, "--due-hours", "168").strip() == "due")
    short = run(SESSIONS, "map", os.path.join(TMP, "short"), "--limit", "100")
    first = run(SESSIONS, "map", DATA, "--window-days", "28", "--limit", "120")
    last = os.path.join(DATA, "last-map")
    os.utime(last, (NOW - 2 * DAY, NOW - 2 * DAY)) if os.path.exists(last) else None
    step("not due 2 days after a map", run(SESSIONS, "due", DATA, "--due-hours", "168").strip() == "not due")
    os.utime(last, (NOW - 8 * DAY, NOW - 8 * DAY)) if os.path.exists(last) else None
    step("due 8 days after a map", run(SESSIONS, "due", DATA, "--due-hours", "168").strip() == "due")
    step("--window-days 28 maps a 20-day-old session the default skips",
         "aaaa0002-0000-0000-0000-000000000000" in listed(first) and "aaaa0002-0000-0000-0000-000000000000" not in listed(short))
    limited = run(SESSIONS, "map", os.path.join(TMP, "limited"), "--window-days", "28", "--limit", "60")
    step("--limit 60 digests more than 40", len(listed(limited)) == 60, limited[-300:])

    facets = os.path.join(DATA, "facets")
    os.makedirs(facets, exist_ok=True)
    said = {"aaaa0000": [("ask", "what is E1? explain", "explain a made-up label before using it")],
            "aaaa0001": [("ask", "what does that label mean", "explain a made-up label before using it")],
            "aaaa0002": [("rule", "always answer in Korean", "answer in Korean")]}
    for short_id, items in said.items():
        habits = [{"kind": kind, "quote": quote, "line": 1, "before": "the agent used a label", "preference": preference}
                  for kind, quote, preference in items]
        json.dump({"habits": habits}, open(os.path.join(facets, f"{short_id}-0000-0000-0000-000000000000.json"), "w"))
    run(HABITS, "habits", DATA)
    path = os.path.join(DATA, "habits.jsonl")
    items = [json.loads(line) for line in open(path)] if os.path.exists(path) else []
    step("habits.jsonl written with an id, kind and quote per item",
         len(items) == 3 and all(item.get("id") and item.get("kind") and item.get("quote") for item in items))
    ids = {item["quote"]: item["id"] for item in items}
    groups = os.path.join(TMP, "preferences.json")
    json.dump([{"name": "explain a made-up label before using it", "ids": [ids.get("what is E1? explain"), ids.get("what does that label mean")]},
               {"name": "answer in Korean", "ids": [ids.get("always answer in Korean")]}], open(groups, "w"))
    out = run(HABITS, "habits", DATA, "--groups", groups)
    lines = out.splitlines()
    step("a preference in 2 sessions listed, one in 1 not",
         any(line.startswith("preference 2 sessions, 2 repos") and "made-up label" in line for line in lines)
         and not any("Korean" in line for line in lines if line.startswith("preference")), out)
    step("a memory line naming a preference shown", re.search(r"^preference .*made-up label.*\n(  .*\n)*  memory .*plain\.md", out + "\n", re.M), out)

    name = "explain a made-up label before using it"
    seen = re.search(r"last seen (\d+),", out)
    run(HABITS, "habits", DATA, "--record", "/m/plain.md", seen.group(1) if seen else "0", name)
    fresh = [line for line in run(HABITS, "habits", DATA, "--groups", groups).splitlines() if line.startswith("preference")]
    json.dump({name: {"url": "/m/plain.md", "last_seen": NOW - 10 * DAY}}, open(os.path.join(DATA, "kept.json"), "w"))
    stale = [line for line in run(HABITS, "habits", DATA, "--groups", groups).splitlines() if line.startswith("preference")]
    step("a recorded preference carries `kept <where>`; `seen since` only when sighted after its recorded last sighting",
         fresh and "kept /m/plain.md" in fresh[0] and "seen since" not in fresh[0]
         and stale and "kept /m/plain.md" in stale[0] and "seen since" in stale[0], f"{fresh} {stale}")
    step("no file outside the data folder changed", snapshot() == before)

    print(f"probe: {sum(results)} of {len(results)} steps pass")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
