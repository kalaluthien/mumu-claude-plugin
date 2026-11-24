#!/usr/bin/env python3
"""Call each Python script of this plugin's skills with `--help` and with an unknown `--x` at each word position of a valid call, in a scratch folder, and list each call that is not refused: exit 2, `usage:` on stderr, nothing on stdout and the folder left as it was.

usage: replay-option-calls.py [<repository root>]

The repository check passes its root, which this ignores, since the scripts it calls sit in the skills beside this one. Prints one
`option <script>: <call> gave <answer>` line per call not refused, then `<n> scripts, <n> calls, <n> not refused`,
and exits 0 only when none failed."""
import concurrent.futures
import os
import pathlib
import subprocess
import sys
import tempfile

SKILLS = pathlib.Path(__file__).resolve().parents[2]
UNKNOWN = ("--help", "--x")
CALLS = [
    ("system/scripts/serve-relay.py", ["body", "--port", "1", "--quiet", "1"]),
    ("system/scripts/connect-page.py", ["body"]),
    ("system/scripts/check-page.py", ["body"]),
    ("system/scripts/check-contract.py", ["check", "body", "--root", "folder", "--tags", "body"]),
    ("system/scripts/check-contract.py", ["read", "body", "--tags", "body"]),
    ("system/scripts/check-contract.py", ["outline", "body", "level"]),
    ("system/scripts/check-contract.py", ["gaps", "body"]),
    ("system/scripts/check-contract.py", ["tags"]),
    ("system/scripts/check-contract.py", ["rules"]),
    ("system/scripts/check-contract.py", ["fixtures"]),
    ("system/scripts/make-page.py", ["body", "page.html"]),
    ("system/scripts/score-contract.py", ["body", "--root", "folder"]),
    ("system/scripts/sort-edges.py", ["body", "--root", "folder"]),
]


def calls_with_option(words):
    """Each call that puts an unknown option into WORDS at a word position: before the word, or in its place."""
    for position in range(len(words) + 1):
        for option in UNKNOWN:
            yield words[:position] + [option] + words[position:]
            if position < len(words):
                yield words[:position] + [option] + words[position + 1:]


def snapshot(folder):
    return sorted((str(path.relative_to(folder)), path.stat().st_size, path.stat().st_mtime_ns) for path in folder.rglob("*"))


def refusal(name, call):
    """What the call CALL of the script NAME gave, in a scratch folder of its own, when it was not refused; else nothing."""
    with tempfile.TemporaryDirectory() as scratch:
        folder = pathlib.Path(scratch)
        (folder / "body").write_text("<!doctype html><title>x</title>\n")
        before = snapshot(folder)
        try:
            answered = subprocess.run([sys.executable, str(SKILLS / name), *call], cwd=folder, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return "no answer in 30 s"
        return (f"exit {answered.returncode}, stdout {answered.stdout[:60]!r}" if answered.returncode != 2 or answered.stdout or "usage:" not in answered.stderr
                else "a change to the folder" if snapshot(folder) != before else "")


def main(args):
    if len(args) > 1 or (args and args[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 2
    calls = [(name, call) for name, words in CALLS for call in calls_with_option(words)]
    with concurrent.futures.ThreadPoolExecutor(os.cpu_count()) as pool:
        answers = pool.map(lambda one: refusal(*one), calls)
    failures = [f"option {name}: {' '.join(call)} gave {answer}" for (name, call), answer in zip(calls, answers) if answer]
    for line in failures:
        print(line)
    print(f"{len({name for name, _ in CALLS})} scripts, {len(calls)} calls, {len(failures)} not refused")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
