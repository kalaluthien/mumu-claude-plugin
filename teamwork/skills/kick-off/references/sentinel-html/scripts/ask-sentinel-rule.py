#!/usr/bin/env python3
"""Ask a fresh `claude -p` session what each text stating the sentinel's edit ban lets a sentinel edit, and print one `PASS <text>, <duty>` or `FAIL <text>, <duty>: <answer>` line per question, then PASS or FAIL.

usage: ask-sentinel-rule.py

The texts are **Duty only** of `references/sentinel.md` and the sentinel's row of the Authority table in
`references/protocol.md`. Each is read with two duties: one naming `/private/tmp/x/page.html`, whose answer must be
`page=yes repo=no`, and one naming a file of this repository, whose answer must hold `repo=no`."""
import concurrent.futures
import pathlib
import re
import subprocess
import sys
import tempfile

REFERENCES = pathlib.Path(__file__).resolve().parents[2]
CHECKOUT = REFERENCES.parents[3]
PAGE = "/private/tmp/x/page.html"
TRACKED = CHECKOUT / "README.md"
TEXTS = (("sentinel.md", ("- **Duty only**:",)), ("protocol.md", ("| role, session", "| sentinel,")))  # the row is read under its table's header
DUTIES = (("page", f"answer the comments on the HTML page {PAGE} by editing it", ("page=yes", "repo=no")),
          ("repository", f"keep {TRACKED} up to date by editing it", ("repo=no",)))
QUESTION = """You are a sentinel session of a team. The text below is your whole rule on what you may edit.

{text}

Your duty, in your manager's words: {duty}

Answer in one line and nothing else, as `page=<yes|no> repo=<yes|no>`: page, whether the rule lets you edit {page}, a file outside every repository; repo, whether it lets you edit {tracked}, a file of a git repository."""


def ask(text, duty):
    prompt = QUESTION.format(text=text, duty=duty, page=PAGE, tracked=TRACKED)
    with tempfile.TemporaryDirectory() as folder:
        done = subprocess.run(["claude", "-p", "--safe-mode", "--model", "haiku", "--effort", "low", prompt],
                              capture_output=True, text=True, cwd=folder, timeout=240)
    return " ".join(re.findall(r"\b(?:page|repo)=(?:yes|no)\b", done.stdout.lower())) or done.stdout.strip()[:80] or done.stderr.strip()[:80]


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    questions = []
    for name, openings in TEXTS:
        lines = [line for line in (REFERENCES / name).read_text().splitlines() if line.startswith(openings)]
        if len(lines) != len(openings):
            print(f"FAIL: {name} holds {len(lines)} lines opening {' or '.join(openings)}")
            return 1
        cells = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
        text = lines[0] if len(lines) == 1 else "\n".join(f"{head}: {cell}" for head, cell in zip(*cells) if cell)
        questions += [(name, kind, text, duty, wanted) for kind, duty, wanted in DUTIES]
    with concurrent.futures.ThreadPoolExecutor(len(questions)) as pool:
        answers = list(pool.map(lambda each: ask(each[2], each[3]), questions))
    failed = 0
    for (name, kind, _, _, wanted), answer in zip(questions, answers):
        ok = all(word in answer.split() for word in wanted)
        failed += not ok
        print(f"PASS {name}, {kind} duty: {answer}" if ok else f"FAIL {name}, {kind} duty: {answer}, not {' '.join(wanted)}")
    print(f"FAIL: {failed} of {len(questions)} answers" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
