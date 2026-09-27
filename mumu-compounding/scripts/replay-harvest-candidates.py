#!/usr/bin/env python3
"""Replay `takeaway.py candidates` over the hand-labelled transcripts of #208.

  replay-harvest-candidates.py [<projects dir>]   default ~/.claude/projects

Each transcript of tests/replay/labels.json is cut to its labelled length in a
temporary folder, as the harvest at that point would read it, and its
candidates are matched to its labels: a transcript label by its entry's
timestamp, a comment label by its url. Prints per transcript the labels found,
the candidates listed, and the labels missed, then the total recall.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
LABELS = HERE.parent / "tests" / "replay" / "labels.json"


def main(root):
    transcripts = json.loads(LABELS.read_text())["transcripts"]
    found = total = 0
    print("| session | compacted | labels found | candidates | missed |")
    print("| --- | --- | --- | --- | --- |")
    with tempfile.TemporaryDirectory() as tmp:
        for session, case in transcripts.items():
            source = pathlib.Path(root) / case["folder"] / f"{session}.jsonl"
            lines = [line for line in source.read_text(encoding="utf-8").splitlines(True) if line.strip()]
            cut = pathlib.Path(tmp) / f"{session}.jsonl"
            cut.write_text("".join(lines[:case["lines"]]), encoding="utf-8")
            out = subprocess.run([sys.executable, str(HERE / "takeaway.py"), "candidates", str(cut)],
                                 capture_output=True, text=True, check=True).stdout.splitlines()[:-1]
            hits = [label for label in case["labels"]
                    if any(line.startswith(label["at"]) and (label.get("url") or "") in line for line in out)]
            missed = [label.get("url") or f"{label['kind']} {label['at']}" for label in case["labels"] if label not in hits]
            found, total = found + len(hits), total + len(case["labels"])
            print(f"| {session[:8]} | {case['compacted']} | {len(hits)}/{len(case['labels'])} | {len(out)} | "
                  f"{', '.join(missed) or '-'} |")
    print(f"\nrecall: {found}/{total} = {found / total:.0%}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.claude/projects")))
