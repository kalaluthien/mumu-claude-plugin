#!/usr/bin/env python3
"""Map dejavu's window of sessions: write digests for the haiku facet agents, and tool-failure signatures.

  list-sessions.py due <data>                  `due` when <data>/last-map is 24 hours old or missing, else `not due`
  list-sessions.py map <data>                  every in-window session: signatures to <data>/stats/; the newest 40
                                               without a facet: digests to <data>/digests/; touches <data>/last-map
  list-sessions.py digest <data> <path>...     digests and signatures of the named transcripts, window aside

Digests print as `batch <k>: <digest> ...` lines of at most 10, one haiku agent each. The window is the interactive
top-level transcripts under ${CLAUDE_CONFIG_DIR:-~/.claude}/projects changed in the last 14 days.
"""
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "lib"))
import claude_config  # noqa: E402
import transcript  # noqa: E402

WINDOW_DAYS, PER_RUN, PER_BATCH, DUE_HOURS = 14, 40, 10, 24
OWNER_CAP, AGENT_CAP, DIGEST_CAP = 500, 300, 30000
TAGS = re.compile(r"<(system-reminder|task-notification)>.*?</\1>", re.S)
# urls before paths, so a url is masked whole
VARIABLE = [(re.compile(p), r) for p, r in [
    (r"https?://\S+", "<url>"), (r"/[\w.~@%+-]+(?:/[\w.~@%+-]+)+", "<path>"), (r"\b[0-9a-f]{7,40}\b", "<hash>"),
    (r"(['\"`]).*?\1", "<q>"), (r"\d+", "<n>"), (r"\s+", " ")]]
NOISE = re.compile(r"^(Exit code <n>|<n>|-+|ok\b.*|This hook comes from .*)$")
DENIED = re.compile(r"doesn't want to proceed|user denied|rejected by the user", re.I)
REASON = re.compile(r"\[[A-Z][A-Za-z /-]+\]")
# a token starts at a word boundary, so a word like task-manager keeps its "sk-"
TOKEN = re.compile(r"\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_\w{22,}|sk-ant-[\w-]{20,}|sk-[\w-]{20,}"
                   r"|xox[abposr]-[\w-]{10,}|AKIA[A-Z0-9]{16})")


def repo_of(path):
    """The project folder's name, a worktree folded into its repository."""
    return re.sub(r"--claude-worktrees-.*$", "", os.path.basename(os.path.dirname(path)))


def window(now):
    """Top-level transcripts changed within the window, newest first."""
    paths = glob.glob(os.path.join(glob.escape(str(claude_config.folder())), "projects", "*", "*.jsonl"))
    recent = [p for p in paths if os.path.getmtime(p) >= now - WINDOW_DAYS * 86400]
    return sorted(recent, key=os.path.getmtime, reverse=True)


def signature(tool, text):
    """The tool and the last meaningful error line, variable parts masked; None for a bare exit code or a denial."""
    if DENIED.search(text):
        return None
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        for pattern, mask in VARIABLE:
            line = pattern.sub(mask, line)
        if line and not NOISE.match(line):
            lines.append(line)
    reason = REASON.search(text)
    return f"{tool}: {lines[-1][:100]}" + (f" {reason.group(0)}" if reason else "") if lines else None


def read(path):
    """(stats, lines, owners) of a transcript, stats None for an sdk session; lines are the digest's lines."""
    entries = transcript.entries_of(path) or []
    if any(str(e.get("entrypoint", "")).startswith("sdk") for e in entries):
        return None, [], []
    uses, failures, lines, owners, end = {}, [], [], [], None
    for number, entry in enumerate(entries, 1):
        end = transcript.seconds(entry.get("timestamp")) or end
        if entry.get("isSidechain"):
            continue
        for block in transcript.blocks_of(entry, "tool_use"):
            uses[block.get("id")] = block.get("name")
            lines.append(f"[Tool: {block.get('name')}]")
        for block in transcript.blocks_of(entry, "tool_result"):
            key = block.get("is_error") and signature(uses.get(block.get("tool_use_id"), "?"), transcript.text_of(block))
            if key:
                failures.append({"key": key, "line": number, "time": transcript.seconds(entry.get("timestamp"))})
        if entry.get("type") == "assistant":
            for block in transcript.blocks_of(entry, "text"):
                if block.get("text", "").strip():
                    lines.append(f"[Agent L{number}]: {block['text'].strip()[:AGENT_CAP]}")
        elif entry.get("type") == "user" and (entry.get("origin") or {}).get("kind") == "human":
            body = (entry.get("message") or {}).get("content")
            texts = [body] if isinstance(body, str) else [b.get("text", "") for b in transcript.blocks_of(entry, "text")]
            for text in texts:
                text = TAGS.sub("", text).strip()
                if text and not text.startswith("[Request interrupted"):
                    owners.append({"line": number, "text": text})
                    lines.append(f"[OWNER L{number}]: {text[:OWNER_CAP]}")
    stats = {"path": path, "repo": repo_of(path), "end": end, "failures": failures}
    return stats, lines, owners


def digest(path, lines):
    """The insights cut when it fits; else every owner line with the agent text before it, oldest middle cut."""
    head = f"Session: {os.path.basename(path)[:-6]}\nProject: {repo_of(path)}\n"
    text = head + "\n".join(lines)
    if len(text) <= DIGEST_CAP:
        return text
    keep = []
    for k, line in enumerate(lines):
        if line.startswith("[OWNER"):
            before = next((lines[j] for j in range(k - 1, -1, -1) if not lines[j].startswith("[Tool")), "")
            if before.startswith("[Agent") and (not keep or keep[-1] != before):
                keep.append(before)
            keep.append(line)
    body = "\n".join(keep)
    room = DIGEST_CAP - len(head) - 30
    return head + ("[oldest middle cut]\n" + body[-room:] if len(body) > room else body)


def private(target):
    """Open target for writing as 0600; chmod too, since an existing file keeps its old mode."""
    handle = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(handle, 0o600)
    return open(handle, "w", encoding="utf-8")


def write(data, path, kind, value):
    # digests hold the owner's words; makedirs(exist_ok=True) keeps an old folder's mode, so chmod each
    folder = os.path.join(data, kind)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    os.chmod(data, 0o700)
    os.chmod(folder, 0o700)
    target = os.path.join(folder, os.path.basename(path)[:-6] + (".txt" if kind == "digests" else ".json"))
    with private(target) as out:
        out.write(TOKEN.sub("<token>", value) if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
    return target


def batches(digests):
    for k in range(0, len(digests), PER_BATCH):
        print(f"batch {k // PER_BATCH + 1}: {' '.join(digests[k:k + PER_BATCH])}")


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("due", "map", "digest"):
        sys.exit(__doc__)
    verb, data, now = sys.argv[1], sys.argv[2], time.time()
    stamp = os.path.join(data, "last-map")
    if verb == "due":
        old = not os.path.exists(stamp) or os.path.getmtime(stamp) <= now - DUE_HOURS * 3600
        print("due" if old else "not due")
        return
    paths = sys.argv[3:] if verb == "digest" else window(now)
    faceted = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(glob.escape(data), "facets", "*.json"))}
    digests, waiting = [], 0
    for path in paths:
        stats, lines, owners = read(path)
        if stats is None:
            continue
        write(data, path, "stats", stats)
        if os.path.basename(path)[:-6] in faceted and verb == "map":
            continue
        if len(digests) < PER_RUN or verb == "digest":
            digests.append(write(data, path, "digests", digest(path, lines)))
        else:
            waiting += 1
    if verb == "map":
        os.makedirs(data, mode=0o700, exist_ok=True)
        private(stamp).close()
        print(f"{len(digests)} sessions to facet; {waiting} wait for later runs")
    batches(digests)


if __name__ == "__main__":
    main()
