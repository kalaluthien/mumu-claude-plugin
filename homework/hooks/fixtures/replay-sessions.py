#!/usr/bin/env python3
"""Replay labelled past sessions through the Stop hook and count which got a wrap-up ask.

  replay-sessions.py <sessions.json> [--holdout] [<signal-wrap-up.py>]

Each session replays alone, stop by stop, in a fresh plugin data folder, the
hook at stop k seeing the transcript up to that stop, at the highest lesson
threshold, since a retro owed to a session must not hang on a threshold that
the outcomes of other sessions move. A session labelled `mid` is covered when
the hook asked at least once; one labelled `short` is spared when it never asked.
With --holdout only the sessions whose file name hashes odd are scored, the
half left out when the trigger was tuned, as replay-score.py splits stops.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "lib"))
import transcript  # noqa: E402

HIGHEST = "12"


def stop_offsets(path):
    offsets, offset = [], 0
    with open(path, "rb") as handle:
        for raw in handle:
            offset += len(raw)
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if transcript.is_stop(entry):
                offsets.append(offset)
    return offsets


def asks(signal, path):
    """How many stops of the session the hook asked at."""
    with open(path, "rb") as handle:
        whole = handle.read()
    count = 0
    with tempfile.TemporaryDirectory() as data:
        cut = os.path.join(data, "session.jsonl")
        for offset in stop_offsets(path):
            with open(cut, "wb") as handle:
                handle.write(whole[:offset])
            payload = {"session_id": "replayed", "transcript_path": cut, "cwd": HERE,
                       "hook_event_name": "Stop", "stop_hook_active": False}
            run = subprocess.run([signal], input=json.dumps(payload), capture_output=True, text=True,
                                 env={**os.environ, "CLAUDE_PLUGIN_DATA": data, "WRAP_UP_THRESHOLD": HIGHEST})
            if run.returncode != 0:
                sys.exit(f"{signal} failed on {path}: {run.stderr.strip()}")
            count += '"decision": "block"' in run.stdout
    return count


def odd(path):
    return int(hashlib.sha256(os.path.basename(path).encode()).hexdigest(), 16) % 2


def main(labels_path, signal, holdout):
    with open(labels_path, encoding="utf-8") as handle:
        rows = [row for row in json.load(handle)["sessions"] if not holdout or odd(row["transcript"])]
    tally = {"short": [0, 0], "mid": [0, 0]}
    missing = 0
    for row in rows:
        path = os.path.expanduser(row["transcript"])
        if not os.path.exists(path):
            missing += 1
            continue
        n = asks(signal, path)
        tally[row["label"]][0] += 1
        tally[row["label"]][1] += n > 0
        print(f"{row['label']:5} asks {n:3} {os.path.basename(path)[:8]}", file=sys.stderr)
    (mid, covered), (short, asked) = tally["mid"], tally["short"]
    print(f"replayed {mid + short} sessions, {missing} transcripts gone")
    print(f"mid-length and longer: {covered} of {mid} got a retro ask ({100 * covered / max(mid, 1):.0f}%)")
    print(f"short and simple: {short - asked} of {short} got none ({100 * (short - asked) / max(short, 1):.0f}%)")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    holdout = "--holdout" in args
    args = [arg for arg in args if arg != "--holdout"]
    if len(args) not in (1, 2):
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        sys.exit(2)
    sys.exit(main(args[0], os.path.abspath(args[1]) if len(args) == 2 else os.path.join(HERE, "..", "signal-wrap-up.py"), holdout))
