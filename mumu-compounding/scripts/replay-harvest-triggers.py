#!/usr/bin/env python3
"""Replay candidate harvest triggers over past session transcripts.

  replay-harvest-triggers.py [<projects dir>]   default ~/.claude/projects

Each top-level `*/<session>.jsonl` of an interactive session (no `sdk`
entrypoint, as takeaway.py skips) is replayed stop by stop, a stop being a
`stop_hook_summary` entry. A trigger counts its events since the harvest its
last simulated block asked for, and asks at a stop once the count reaches its
threshold and HARVEST_INTERVAL minutes passed since that block, the cooldown
takeaway.py applies. Per trigger it prints the stops it asks at, the sessions
it asks in, how many of those wrote a memory after its first ask, and the same
two counts for the sessions the call-count trigger never asks in.
"""
import glob
import json
import os
import re
import sys
from datetime import datetime

HARVEST_INTERVAL = 120
REFUSAL = re.compile(r"Permission for this action was denied|doesn't want to proceed|hook error|<tool_use_error>Blocked")
PUSHBACK = re.compile(r"\[Request interrupted by user|아니|말고|잘못|틀렸|왜 |하지 ?마|\bno\b|\bdon't\b|\bwrong\b|\binstead\b|\bstop\b", re.I)


def entries_of(path):
    out = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def content(entry):
    body = (entry.get("message") or {}).get("content")
    return body if isinstance(body, list) else [{"type": "text", "text": body or ""}]


def owner_text(entry):
    """The owner's typed prompt, or None for tool results, commands and notices."""
    if entry.get("type") != "user" or entry.get("isMeta"):
        return None
    text = " ".join(b.get("text", "") for b in content(entry) if b.get("type") == "text").strip()
    if not text or text.startswith("<") or text.startswith("This session is being continued"):
        return None
    return text


def events(entry, prompts_seen):
    """The events of one entry, by kind."""
    found = {"calls": 0, "failures": 0, "refusals": 0, "pushback": 0}
    if entry.get("type") == "assistant":
        found["calls"] = sum(1 for b in content(entry) if b.get("type") == "tool_use")
    for block in content(entry) if entry.get("type") == "user" else []:
        if block.get("type") == "tool_result" and block.get("is_error"):
            text = block.get("content")
            text = text if isinstance(text, str) else json.dumps(text)
            found["failures"] += 1
            found["refusals"] += bool(REFUSAL.search(text))
    text = owner_text(entry)
    if text is not None and prompts_seen and PUSHBACK.search(text):
        found["pushback"] = 1
    return found


def writes_memory(entry):
    for block in content(entry) if entry.get("type") == "assistant" else []:
        if block.get("type") != "tool_use":
            continue
        args = block.get("input") or {}
        if block.get("name") in ("Write", "Edit") and "/memory/" in str(args.get("file_path", "")):
            return True
        command = str(args.get("command", "")) if block.get("name") == "Bash" else ""
        if "/memory/" in command and re.search(r">|\btee\b|\bmv\b|\bcp\b|write_text", command):
            return True
    return False


def minutes(entry):
    try:
        return datetime.fromisoformat(str(entry.get("timestamp")).replace("Z", "+00:00")).timestamp() / 60
    except ValueError:
        return None


def replay(entries, kind, threshold):
    """Indexes of the stops this trigger asks at."""
    asks, count, prompts, block_at, waiting = [], 0, 0, None, False
    for i, entry in enumerate(entries):
        if entry.get("subtype") == "stop_hook_summary":
            if waiting:  # the harvest's own stop: count afresh from here
                waiting, count = False, 0
                continue
            now = minutes(entry)
            cool = block_at is None or now is None or now - block_at >= HARVEST_INTERVAL
            if cool and count >= threshold:
                asks.append(i)
                block_at, waiting = now, True
            continue
        count += events(entry, prompts)[kind]
        prompts += owner_text(entry) is not None
    return asks


TRIGGERS = [("calls", 40), ("failures", 3), ("failures", 5), ("refusals", 2), ("pushback", 2)]


def main(root):
    sessions = []
    for path in sorted(glob.glob(os.path.join(root, "*", "*.jsonl"))):
        entries = entries_of(path)
        if any(str(e.get("entrypoint", "")).startswith("sdk") for e in entries):
            continue
        if not any(e.get("subtype") == "stop_hook_summary" for e in entries):
            continue
        memory = [i for i, e in enumerate(entries) if writes_memory(e)]
        sessions.append((entries, memory))
    wrote = sum(1 for _, memory in sessions if memory)
    print(f"sessions: {len(sessions)} interactive with stops, {wrote} wrote a memory\n")
    by_calls = [bool(replay(entries, "calls", 40)) for entries, _ in sessions]
    missed = sum(1 for (_, memory), called in zip(sessions, by_calls) if memory and not called)
    print(f"wrote a memory where calls>=40 never asks: {missed}\n")
    print("| trigger | stops asked | sessions asked | of those, wrote a memory after | "
          "asked where calls>=40 never asks | of those, wrote a memory after |")
    print("| --- | --- | --- | --- | --- | --- |")
    for kind, threshold in TRIGGERS:
        stops = asked = hit = extra = extra_hit = 0
        for (entries, memory), called in zip(sessions, by_calls):
            asks = replay(entries, kind, threshold)
            if not asks:
                continue
            later = any(i > asks[0] for i in memory)
            stops, asked, hit = stops + len(asks), asked + 1, hit + later
            if not called:
                extra, extra_hit = extra + 1, extra_hit + later
        print(f"| {kind} >= {threshold} | {stops} | {asked} | {hit} | {extra} | {extra_hit} |")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.claude/projects")))
