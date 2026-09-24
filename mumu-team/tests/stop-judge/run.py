#!/usr/bin/env python3
"""Run the worker Stop decision of each case in cases.json two ways and print how each agrees with the labels.

- string: bin/worker-stop.py, the #19 command hook, fed the Stop payload a worker sends.
- haiku: a real `claude -p` session whose only added hook is a `type: "agent"` Stop hook on Haiku with
  judge-prompt.md; the session ends its first turn with the case's last message, and the hook's first verdict counts.

Both read the case's issue and pull request from a fake `gh` first on PATH, in a fresh worktree-shaped directory per run.

usage: run.py [--runs N] [--jobs N] [--case ID]... [--split dev|test] [--judges string,haiku] [--out results.jsonl]
"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
PLUGIN = HERE.parent.parent
JUDGE_MODEL = "claude-haiku-4-5"
MAIN_MODEL = "sonnet"
# A hook agent runs in dontAsk mode, whatever the session's mode: only allowed tools run.
ALLOW = ["Bash(gh issue view *)", "Bash(gh pr list *)"]

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, sys
d = os.environ["FAKE_GH_DIR"]
with open(os.path.join(d, "calls"), "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
case = json.load(open(os.path.join(d, "case.json")))
who = {"login": "kalaluthien"}
issue = {"state": case["issue"]["state"], "comments": [{"author": who, "body": b} for b in case["issue"]["comments"]]}
prs = [dict(p, comments=[{"author": who, "body": b} for b in p["comments"]]) for p in case["prs"]]
cmd = sys.argv[1:3]
if cmd == ["issue", "view"]:
    print(json.dumps(issue))
elif cmd == ["pr", "list"]:
    print(json.dumps(prs))
elif cmd == ["pr", "view"] and prs:
    print(json.dumps(prs[0]))
else:
    sys.exit(f"fake gh: unsupported {sys.argv[1:]}")
'''


def setup(case, index, root):
    """Make a worktree-shaped cwd and a fake gh for one run; return (cwd, env)."""
    d = pathlib.Path(tempfile.mkdtemp(prefix=f"{case['id']}-", dir=root))
    (d / "bin").mkdir()
    (d / "bin" / "gh").write_text(FAKE_GH)
    (d / "bin" / "gh").chmod(0o755)
    (d / "case.json").write_text(json.dumps(case))
    cwd = d / "repo" / ".claude" / "worktrees" / f"{case['id']}-{40 + index}"
    cwd.mkdir(parents=True)
    env = dict(os.environ, FAKE_GH_DIR=str(d), PATH=f"{d / 'bin'}:{os.environ['PATH']}")
    return cwd, env


def calls(env):
    p = pathlib.Path(env["FAKE_GH_DIR"], "calls")
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def run_string(case, index, root):
    cwd, env = setup(case, index, root)
    payload = {"hook_event_name": "Stop", "session_id": "s", "cwd": str(cwd), "stop_hook_active": False,
               "agent_type": "mumu-team:worker", "last_assistant_message": case["last"]}
    t = time.monotonic()
    out = subprocess.run([str(PLUGIN / "bin" / "worker-stop.py")], input=json.dumps(payload), env=env,
                         capture_output=True, text=True, timeout=60)
    latency = time.monotonic() - t
    block = out.stdout.strip() and json.loads(out.stdout).get("decision") == "block"
    return {"verdict": "keep" if block else "stop", "latency": latency, "cost": 0.0, "gh": calls(env)}


def run_haiku(case, index, root):
    cwd, env = setup(case, index, root)
    settings = cwd.parent.parent.parent.parent / "settings.json"
    settings.write_text(json.dumps({"permissions": {"allow": ALLOW}, "hooks": {"Stop": [{"hooks": [{
        "type": "agent", "model": JUDGE_MODEL, "timeout": 120, "prompt": (HERE / "judge-prompt.md").read_text()}]}]}}))
    ask = ("Reply with exactly the text between the markers and nothing else. Use no tools.\n<<<\n"
           f"{case['last']}\n>>>")
    proc = subprocess.Popen(["claude", "-p", ask, "--model", MAIN_MODEL, "--settings", str(settings), "--max-turns", "1", "--permission-mode", "auto",
                             "--output-format", "stream-json", "--verbose"],
                            cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    said = verdict = reason = None
    usage = {}
    for line in proc.stdout:
        now = time.monotonic()
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "assistant" and said is None:
            said = now
        elif ev.get("type") == "user" and ev.get("isSynthetic") and verdict is None:
            text = "".join(c.get("text", "") for c in ev["message"]["content"] if isinstance(c, dict))
            if "Stop hook" in text:
                verdict, reason, done = "keep", text, now
        elif ev.get("type") == "result":
            if verdict is None:
                verdict, done = "stop", now
            usage = ev.get("modelUsage", {})
    proc.wait()
    judge = usage.get(JUDGE_MODEL, {})
    return {"verdict": verdict or "error", "reason": reason, "latency": (done - said) if said and verdict else None,
            "cost": judge.get("costUSD"), "gh": calls(env)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--case", action="append")
    ap.add_argument("--split", help="dev or test; all when omitted")
    ap.add_argument("--judges", default="string,haiku")
    ap.add_argument("--out", default="results.jsonl")
    a = ap.parse_args()
    cases = [c for c in json.loads((HERE / "cases.json").read_text()) if (not a.case or c["id"] in a.case) and (not a.split or c["split"] == a.split)]
    root = tempfile.mkdtemp(prefix="stop-judge-")
    jobs = [(j, i, c, r) for j in a.judges.split(",") for i, c in enumerate(cases) for r in range(a.runs)]
    fn = {"string": run_string, "haiku": run_haiku}
    with open(a.out, "a") as out, concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        futures = {pool.submit(fn[j], c, i, root): (j, c, r) for j, i, c, r in jobs}
        for f in concurrent.futures.as_completed(futures):
            j, c, r = futures[f]
            row = dict(f.result(), judge=j, case=c["id"], run=r, label=c["label"])
            out.write(json.dumps(row) + "\n")
            out.flush()
            print(j, c["id"], r, c["label"], row["verdict"], f"{row['latency'] or 0:.1f}s", row["cost"], file=sys.stderr)


if __name__ == "__main__":
    main()
