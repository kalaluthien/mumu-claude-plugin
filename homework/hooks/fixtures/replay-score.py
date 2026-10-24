#!/usr/bin/env python3
"""Score the wrap-up trigger against main's rule on labelled past stops.

usage: replay-score.py <labels.json> [--holdout]

A stop is a `stop_hook_summary` entry of a labelled transcript; the hook at
stop k sees the transcript up to that entry. Stops of every labelled session
replay in time order through one plugin data folder, as live sessions share
it. `head` runs signal-wrap-up.py in the folder above as the Stop hook would, and
after each ask reports the label back as that ask's outcome, `filed` when the
stop is labelled worth a wrap-up, else `empty`, as the skill reports it live.
`main` is main's rule rebuilt from the constants of the removed takeaway.py: ask a
retro once WORK_THRESHOLD tool calls ran since the stop after its last ask
and HARVEST_INTERVAL minutes passed since that ask, else a dream once
DREAM_THRESHOLD memory files were written since its last dream ask.

Without --holdout every stop is scored and each head ask prints its sentence.
With --holdout the sessions whose file name hashes odd are scored, after the
even half replays first to train head's thresholds.
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from datetime import datetime

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import memory as memory_file  # noqa: E402
import transcript  # noqa: E402

SIGNAL = str(HERE.parent / "signal-wrap-up.py")


def main_constants():
    # the thresholds of homework/scripts/takeaway.py, which held main's rule and is removed
    return {"WORK_THRESHOLD": 40.0, "HARVEST_INTERVAL": 120.0, "DREAM_THRESHOLD": 5.0}


def stops_of(path):
    """Per stop: (byte offset of its summary line, time, tool calls and memory files since the last stop)."""
    stops, offset, calls, memory, last = [], 0, 0, set(), None
    with open(os.path.expanduser(path), "rb") as handle:
        for raw in handle:
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                offset += len(raw)
                continue
            last = entry.get("timestamp") or last
            if entry.get("subtype") == "stop_hook_summary":
                at = transcript.seconds(last)
                if at is None:
                    sys.exit(f"no time at a stop of {path}: {last!r}")
                stops.append({"offset": offset, "at": at, "calls": calls, "memory": memory})
                calls, memory = 0, set()
            body = (entry.get("message") or {}).get("content")
            for block in body if isinstance(body, list) else []:
                if block.get("type") == "tool_use":
                    calls += 1
                    memory.update(memory_file.PATH.findall(json.dumps(block.get("input") or {})))
            offset += len(raw)
    return stops


class Main:
    def __init__(self, constants):
        self.work = constants["WORK_THRESHOLD"]
        self.interval = constants["HARVEST_INTERVAL"] * 60
        self.dream = constants["DREAM_THRESHOLD"]
        self.sessions, self.stamp, self.written = {}, None, {}

    def ask(self, session, stop):
        for name in stop["memory"]:
            self.written[name] = stop["at"]
        state = self.sessions.setdefault(session, {"calls": 0, "asked": None, "in_retro": False})
        # main counts calls only from the stop that ended the retro it asked for
        state["calls"] = 0 if state["in_retro"] else state["calls"] + stop["calls"]
        state["in_retro"] = False
        waited = state["asked"] is None or stop["at"] - state["asked"] >= self.interval
        if waited and state["calls"] >= self.work:
            state.update(calls=0, asked=stop["at"], in_retro=True)
            return True
        if self.stamp is None:
            self.stamp = stop["at"]
            return False
        if sum(1 for at in self.written.values() if at > self.stamp) >= self.dream:
            self.stamp = stop["at"]
            return True
        return False


def head_ask(data, path, stop, session):
    with open(os.path.expanduser(path), "rb") as handle:
        prefix = handle.read(stop["offset"])
    with tempfile.NamedTemporaryFile("wb", suffix=".jsonl", dir=data, delete=False) as cut:
        cut.write(prefix)
    payload = {"session_id": session, "transcript_path": cut.name, "cwd": str(HERE),
               "hook_event_name": "Stop", "stop_hook_active": False}
    run = subprocess.run([SIGNAL], input=json.dumps(payload), capture_output=True, text=True,
                         env={**os.environ, "CLAUDE_PLUGIN_DATA": data})
    os.unlink(cut.name)
    if run.returncode != 0:
        sys.exit(f"signal-wrap-up.py failed at {session} stop: {run.stderr.strip()}")
    out = json.loads(run.stdout) if run.stdout.strip() else {}
    return out.get("reason") if out.get("decision") == "block" else None


def score(asked, labels):
    worth = [key for key, label in labels.items() if label]
    hits = sum(1 for key in asked if labels[key])
    precision = hits / len(asked) if asked else 0.0
    recall = sum(1 for key in worth if key in asked) / len(worth) if worth else 0.0
    return precision, recall, 100 * len(asked) / len(labels)


def replay(stops, labels, scored, verbose):
    """Ask sets (head, main) over the scored stops."""
    main = Main(main_constants())
    head, rebuilt = set(), set()
    with tempfile.TemporaryDirectory() as data:
        for at, path, k, stop in stops:
            session = os.path.basename(path).rsplit(".", 1)[0]
            key = (path, k)
            reason = head_ask(data, path, stop, session)
            if reason is not None:
                outcome = "filed" if labels[key] else "empty"
                subprocess.run([SIGNAL, "outcome", data, session, outcome], check=True, capture_output=True)
                if key in scored:
                    head.add(key)
                if verbose:
                    print(f"{datetime.fromtimestamp(at).isoformat()} {session[:8]} stop {k}: {reason}")
            if main.ask(session, stop) and key in scored:
                rebuilt.add(key)
    return head, rebuilt


def run(labels_path, holdout):
    with open(labels_path, encoding="utf-8") as handle:
        rows = json.load(handle)["stops"]
    labels = {(row["transcript"], row["stop"]): bool(row["worth"]) for row in rows}
    paths = sorted({row["transcript"] for row in rows})
    gone = [p for p in paths if not os.path.exists(os.path.expanduser(p))]
    if gone:
        print(f"skipped {len(gone)} labelled transcripts that no longer exist")
    paths = [p for p in paths if p not in gone]
    odd = {p for p in paths if int(hashlib.sha256(os.path.basename(p).encode()).hexdigest(), 16) % 2}
    stops = []
    for path in paths:
        for k, stop in enumerate(stops_of(path), 1):
            if (path, k) in labels:
                stops.append((stop["at"], path, k, stop))
    stops.sort(key=lambda s: (s[0], s[1], s[2]))
    if holdout:
        stops = [s for s in stops if s[1] not in odd] + [s for s in stops if s[1] in odd]
        scored = {(p, k) for _, p, k, _ in stops if p in odd}
    else:
        scored = {(p, k) for _, p, k, _ in stops}
    head, rebuilt = replay(stops, labels, scored, not holdout)
    subset = {key: labels[key] for key in scored}
    worth = sum(subset.values())
    print(f"scored {len(subset)} stops of {len({p for p, _ in subset})} sessions, {worth} worth a wrap-up")
    if not subset:
        return 0
    for name, asked in (("head", head), ("main", rebuilt)):
        precision, recall, rate = score(asked, subset)
        print(f"{name}: precision {precision:.3f}, recall {recall:.3f}, asks per 100 stops {rate:.1f}")
    return 0


def main(args):
    if len(args) not in (1, 2) or args[0].startswith("-") or (len(args) == 2 and args[1] != "--holdout"):
        print(__doc__, file=sys.stderr)
        return 2
    return run(args[0], len(args) == 2)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
