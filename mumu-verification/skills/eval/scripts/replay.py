#!/usr/bin/env python3
"""Replay prompt.md eval cases as a real session beside other plugins, and count the runs whose Skill calls match each case.

`claude plugin eval` loads one plugin, so a skill that fires alone may still lose to the skills of the plugins a
session really has; this runs `claude -p` in a fresh git repo with every `--with` plugin dir besides the plugin
under test, as `--agent` when given, and reads each run's Skill calls from its stream. A case's `graders/*.md` of
`type: tool_used`, `tool: Skill` give the `input_match` a run must call. Prints one line per case, runs matched of
runs; exit 0 when every run of every case matched, 1 otherwise, 2 when a run could not start.
"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

STRIP = ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "HERDR_PANE_ID", "HERDR_TAB_ID")


def front(text):
    """(frontmatter dict of `key: value` lines, body) of a markdown file."""
    m = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
    if not m:
        return {}, text
    return {k.strip(): v.strip().strip('"') for k, _, v in (l.partition(":") for l in m[1].splitlines()) if v}, m[2]


def wants(case):
    """The input_match of each Skill tool_used grader of a case."""
    out = []
    for g in sorted((case / "graders").glob("*.md")):
        fm, _ = front(g.read_text())
        if fm.get("type") == "tool_used" and fm.get("tool") == "Skill" and fm.get("input_match"):
            out.append(fm["input_match"])
    return out


def run(plugin, others, agent, case, turns, keep=None):
    """The skills one run called, or None when claude could not start; its stream saved to `keep` when given."""
    _, body = front((case / "prompt.md").read_text())
    with tempfile.TemporaryDirectory() as repo:
        for cmd in (["git", "init", "-q"], ["git", "commit", "-q", "--allow-empty", "-m", "init"]):
            subprocess.run(cmd, cwd=repo, check=True)
        argv = ["claude", "-p", body.strip()]
        for d in (*others, plugin):
            argv += ["--plugin-dir", str(d)]
        argv += (["--agent", agent] if agent else []) + ["--max-turns", str(turns), "--permission-mode", "bypassPermissions",
                                                         "--output-format", "stream-json", "--verbose"]
        env = {k: v for k, v in os.environ.items() if k not in STRIP}
        p = subprocess.run(argv, cwd=repo, env=env, capture_output=True, text=True)
    if keep:
        keep.write_text(p.stdout + p.stderr)
    called, started = [], False
    for line in p.stdout.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        started |= d.get("type") == "result"
        for b in (d.get("message") or {}).get("content") or [] if d.get("type") == "assistant" else []:
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Skill":
                called.append(str((b.get("input") or {}).get("skill", "")))
    return called if started else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plugin", type=pathlib.Path, help="the plugin under test")
    ap.add_argument("cases", nargs="+", type=pathlib.Path, help="case dirs holding prompt.md and graders/")
    ap.add_argument("--with", dest="others", action="append", default=[], type=pathlib.Path, help="another plugin dir to load")
    ap.add_argument("--agent", help="run the session as this agent, e.g. mumu-teamwork:worker")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("-j", type=int, default=6)
    ap.add_argument("--keep", type=pathlib.Path, help="save each run's stream as <dir>/<case>-<run>.jsonl")
    args = ap.parse_args()
    jobs = [(c, i) for c in args.cases for i in range(args.runs)]
    if args.keep:
        args.keep.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(args.j) as pool:
        got = list(pool.map(lambda j: run(args.plugin.resolve(), [o.resolve() for o in args.others], args.agent, j[0], args.turns,
                                          args.keep and args.keep / f"{j[0].name}-{j[1] + 1}.jsonl"), jobs))
    if any(g is None for g in got):
        print("a run could not start: check `claude -p` alone", file=sys.stderr)
        return 2
    ok = True
    for c in args.cases:
        want = wants(c)
        runs = [g for (cc, _), g in zip(jobs, got) if cc == c]
        hit = sum(all(any(w in s for s in g) for w in want) for g in runs)
        ok &= bool(want) and hit == len(runs)
        print(f"{c.name}: {hit}/{len(runs)} runs called {', '.join(want) or 'nothing graded'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
