#!/usr/bin/env python3
"""Print one line each time a worker of this session's lead mission changes, and nothing otherwise.

Usage: worker-watch.py <plugin data dir>, run by the `worker-watch` monitor.
Lines: `blocked`, `gone`, `idle` and `working`, then `<name> <issue-url>`, on a
change of the worker's herdr state; and `stuck <name> <issue-url>` when it has
been idle `WORKER_WATCH_STUCK_AFTER` seconds (1800) with its issue open, at
most once an hour. The mission and the loop are `lib/team.py`'s.
"""
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import team  # noqa: E402


def step(state, workers, words, now, stuck_after):
    """Next state, lines to print, and names due a `stuck` check, from each worker's word (`team.words`).

    A state is `{name: (word, idle since, stuck checked at)}`; a worker not yet
    seen starts as working.
    """
    new, lines, due = {}, [], []
    for name, url in workers.items():
        word, since, checked = state.get(name, ("working", None, None))
        now_word = words[name]
        if now_word != word:
            lines.append(f"{now_word} {name} {url}")
            since, checked = (now if now_word == "idle" else None), None
        if now_word == "idle" and now - since >= stuck_after and (checked is None or now - checked >= team.REPEAT):
            due.append(name)
            checked = now
        new[name] = (now_word, since, checked)
    return new, lines, due


def issue_open(url):
    run = subprocess.run(["gh", "issue", "view", url, "--json", "state", "-q", ".state"], capture_output=True, text=True)
    return run.stdout.strip() == "OPEN"


def main():
    stuck_after = float(os.environ.get("WORKER_WATCH_STUCK_AFTER", 1800))
    state = {}

    def tick(parent, workers, words, now):
        nonlocal state
        state, lines, due = step(state, workers, words, now, stuck_after)
        return lines + [f"stuck {name} {workers[name]}" for name in due if issue_open(workers[name])]

    team.poll(sys.argv[1], tick)


if __name__ == "__main__":
    main()
