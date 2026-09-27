#!/usr/bin/env python3
"""Count, over Claude Code session transcripts, how often a change fitted a mumu-verification skill and the skill was called.

A session is one top-level `<projects>/*/*.jsonl` whose first record is at or after --since. Its kind is its
`agent-setting` (`mumu-team:worker` worker, `mumu-team:lead` lead), else `headless` for an `sdk-cli`
entrypoint (evals, probes, `claude -p`), else `plain`. A skill fits a session when a file it changed
matches that skill's description, read from the path and the text written; its changes are its Edit, Write
and MultiEdit calls, and the diff of each pull request it links (a `pr-link` record) whose head branch is
the session's name, since a worker often edits through Bash:
  test  a code file (.py .sh .js .ts .kt ...) outside a test folder or test_* name
  spec  an `.als` file, or written text stating a protocol rule (never, always, only after, at most, ...)
  eval  a prompt of a Claude plugin: SKILL.md, skills/**/references/*.md, agents/*.md, commands/*.md,
        evals/**, CLAUDE.md, AGENTS.md
Files in a temp dir, a scratchpad or `~/.claude/projects` (memory) are not a change. A session called a
skill when a Skill tool call or a typed slash command names `mumu-verification:<skill>`. It listed the
plugin when a `skill_listing` attachment names `mumu-verification:`, and the plugin's SessionStart hook
reached it when its text is in the transcript.

Output: a markdown table per kind and skill, then each non-empty cell's session ids, `--ids` long.
"""
import argparse
import collections
import concurrent.futures
import glob
import json
import os
import re
import subprocess
import sys

SKILLS = ("test", "spec", "eval")
CODE = re.compile(r"\.(py|sh|bash|zsh|js|mjs|cjs|ts|tsx|jsx|kt|kts|java|swift|rs|go|rb|c|cc|cpp|h)$")
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*$|_test\.[a-z]+$|\.test\.[a-z]+$")
RULE = re.compile(r"\b(never|always|only after|at most|at least once|lifecycle|transition|permission|ownership|protocol)\b", re.I)
PROMPT = re.compile(r"(^|/)(SKILL\.md|CLAUDE\.md|AGENTS\.md)$|/skills/.+/references/[^/]+\.md$|/(agents|commands)/[^/]+\.md$|/evals/")
NOT_CHANGE = re.compile(r"^(/tmp/|/private/|/var/folders/)|/scratchpad/|/\.claude/projects/")
HOOK_TEXT = "load the matching mumu-verification skill"
CALL = re.compile(r"mumu-verification:(test|spec|eval)\b")


def fits(path, text):
    """The skills whose description a write of `text` to `path` fits."""
    if not path or NOT_CHANGE.search(path):
        return set()
    out = set()
    if CODE.search(path) and not TEST_PATH.search(path):
        out.add("test")
    if path.endswith(".als") or RULE.search(text or ""):
        out.add("spec")
    if PROMPT.search(path):
        out.add("eval")
    return out


def written(name, inp):
    """(path, text) pairs a tool call writes."""
    if name == "Write":
        return [(inp.get("file_path"), inp.get("content", ""))]
    if name == "Edit":
        return [(inp.get("file_path"), inp.get("new_string", ""))]
    if name == "MultiEdit":
        return [(inp.get("file_path"), "\n".join(e.get("new_string", "") for e in inp.get("edits", [])))]
    return []


def session(path):
    """One transcript's facts, or None when it holds no record with a timestamp."""
    s = {"id": os.path.basename(path)[:-6], "start": None, "setting": None, "entry": None, "name": None,
         "fit": set(), "called": set(), "listed": False, "hook": False, "prs": set()}
    with open(path, errors="replace") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue
            s["start"] = s["start"] or d.get("timestamp")
            s["entry"] = s["entry"] or d.get("entrypoint")
            t = d.get("type")
            if t == "agent-setting":
                s["setting"] = d.get("agentSetting")
            elif t == "pr-link" and d.get("prUrl"):
                s["prs"].add(d["prUrl"])
            elif t in ("agent-name", "custom-title"):
                s["name"] = d.get("agentName") or d.get("customTitle") or s["name"]
            a = d.get("attachment")
            if isinstance(a, dict) and a.get("type") == "skill_listing" and "mumu-verification:" in str(a.get("content", "")):
                s["listed"] = True
            if HOOK_TEXT in line:
                s["hook"] = True
            m = d.get("message")
            content = m.get("content") if isinstance(m, dict) else None
            if t == "user" and isinstance(content, str) and "<command-name>" in content:
                s["called"] |= set(re.findall(r"<command-name>/mumu-verification:(\w+)", content))
            if t != "assistant" or not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                inp = b.get("input") or {}
                if b.get("name") == "Skill":
                    s["called"] |= set(CALL.findall(str(inp.get("skill", ""))))
                for p, text in written(b.get("name"), inp):
                    s["fit"] |= fits(p, text)
    return s if s["start"] else None


def pr_changes(url):
    """(head branch, [(path, added text)]) of a pull request, from `gh`; None when gh fails."""
    m = re.match(r"https://github.com/([^/]+/[^/]+)/pull/(\d+)", url)
    if not m:
        return None
    head = subprocess.run(["gh", "api", f"repos/{m[1]}/pulls/{m[2]}", "-q", ".head.ref"], capture_output=True, text=True)
    diff = subprocess.run(["gh", "pr", "diff", url], capture_output=True, text=True)
    if head.returncode or diff.returncode:
        return None
    files, path = collections.defaultdict(list), None
    for line in diff.stdout.splitlines():
        if line.startswith("diff --git "):
            path = "/" + line.split(" b/", 1)[-1]
        elif path and line.startswith("+") and not line.startswith("+++"):
            files[path].append(line[1:])
        elif path and line.startswith("+++ "):
            files[path]
    return head.stdout.strip(), [(p, "\n".join(t)) for p, t in files.items()]


def add_prs(sessions):
    """Fold into each session's fit the diffs of its own pull requests; returns the urls gh could not read."""
    urls = sorted({u for s in sessions for u in s["prs"]})
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        got = dict(zip(urls, pool.map(pr_changes, urls)))
    for s in sessions:
        for u in s["prs"]:
            if got[u] and got[u][0] == s["name"]:
                for p, text in got[u][1]:
                    s["fit"] |= fits(p, text)
    return [u for u, v in got.items() if v is None]


def kind(s):
    if s["setting"] == "mumu-team:worker":
        return "worker"
    if s["setting"] == "mumu-team:lead":
        return "lead"
    return "headless" if s["entry"] == "sdk-cli" else "plain"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--projects", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--since", default="2026-09-23T10:57:00Z", help="ISO time; default the commit 05b31fe")
    ap.add_argument("--no-prs", action="store_true", help="skip the pull request diffs (no network)")
    ap.add_argument("--ids", type=int, default=0, help="print up to N session ids per cell, 0 for all")
    args = ap.parse_args()
    sessions = [s for p in sorted(glob.glob(os.path.join(args.projects, "*", "*.jsonl")))
                if (s := session(p)) and s["start"] >= args.since]
    unread = [] if args.no_prs else add_prs(sessions)
    kinds = collections.Counter(kind(s) for s in sessions)
    print(f"sessions: {len(sessions)} since {args.since} ({', '.join(f'{k} {n}' for k, n in sorted(kinds.items()))})\n")
    print("| kind | skill | fit | fit, listed | fit, called | fit, not listed, called | called, no fit |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    cells = {}
    for k in sorted(kinds):
        ks = [s for s in sessions if kind(s) == k]
        for sk in SKILLS:
            row = {
                "fit": [s for s in ks if sk in s["fit"]],
                "fit, listed": [s for s in ks if sk in s["fit"] and s["listed"]],
                "fit, called": [s for s in ks if sk in s["fit"] and sk in s["called"]],
                "fit, not listed, called": [s for s in ks if sk in s["fit"] and not s["listed"] and sk in s["called"]],
                "called, no fit": [s for s in ks if sk in s["called"] and sk not in s["fit"]],
            }
            print(f"| {k} | {sk} | " + " | ".join(str(len(v)) for v in row.values()) + " |")
            cells.update({(k, sk, c): v for c, v in row.items() if v})
    if unread:
        print(f"\npull requests gh could not read: {len(unread)}")
    listed = [s for s in sessions if s["listed"]]
    print(f"\nlisted {len(listed)} of {len(sessions)}; SessionStart hook text seen in {sum(s['hook'] for s in sessions)}")
    print("\n## Session ids\n")
    for (k, sk, c), v in cells.items():
        v = v if not args.ids else v[: args.ids]
        print(f"- {k} {sk} {c}: " + ", ".join(f"{s['id'][:8]}" + (f" ({s['name']})" if s["name"] else "") for s in v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
