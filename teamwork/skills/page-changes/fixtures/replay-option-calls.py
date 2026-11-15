#!/usr/bin/env python3
"""Call each script of this skill with `--help` and with an unknown `--x` at each word position of a valid call, in a scratch folder, and list each call that is not refused: exit 2, `usage:` on stderr, nothing on stdout and the folder left as it was.

usage: replay-option-calls.py [<repository root>]

The repository check passes its root, which this ignores, since the scripts it calls sit beside it. Prints one
`option <script>: <call> gave <answer>` line per call not refused, then `<n> scripts, <n> calls, <n> not refused`,
and exits 0 only when none failed."""
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
UNKNOWN = ("--help", "--x")
CALLS = {
    "serve-page-changes.py": ["body", "--port", "1", "--quiet", "1"],
    "connect-page.py": ["body"],
    "check-page.py": ["body"],
}


def calls_with_option(words):
    """Each call that puts an unknown option into WORDS at a word position: before the word, or in its place."""
    for position in range(len(words) + 1):
        for option in UNKNOWN:
            yield words[:position] + [option] + words[position:]
            if position < len(words):
                yield words[:position] + [option] + words[position + 1:]


def snapshot(folder):
    return sorted((str(path.relative_to(folder)), path.stat().st_size, path.stat().st_mtime_ns) for path in folder.rglob("*"))


def main(args):
    if len(args) > 1 or (args and args[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 2
    failures, called = [], 0
    for name, words in CALLS.items():
        with tempfile.TemporaryDirectory() as scratch:
            folder = pathlib.Path(scratch)
            (folder / "body").write_text("<!doctype html><title>x</title>\n")
            for call in calls_with_option(words):
                before = snapshot(folder)
                called += 1
                try:
                    answered = subprocess.run([sys.executable, str(HERE.parent / "scripts" / name), *call], cwd=folder, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
                    answer = (f"exit {answered.returncode}, stdout {answered.stdout[:60]!r}" if answered.returncode != 2 or answered.stdout or "usage:" not in answered.stderr
                              else "a change to the folder" if snapshot(folder) != before else "")
                except subprocess.TimeoutExpired:
                    answer = "no answer in 30 s"
                if answer:
                    failures.append(f"option {name}: {' '.join(call)} gave {answer}")
    for line in failures:
        print(line)
    print(f"{len(CALLS)} scripts, {called} calls, {len(failures)} not refused")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
