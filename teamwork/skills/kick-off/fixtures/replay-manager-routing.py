#!/usr/bin/env python3
"""Run the manager kick-off in a clean `claude -p` on a request for a visible change and print `PASS` when the manager runs `print-steering.py` with no key, writes a start command carrying `--steer visible-change`, opens
neither `handoff-worker-prompt.md` nor the succession and ending files, and the words of the files a start reads are fewer than at `origin/main` (`manager.md` and the handoff file, with the key list `print-steering.py` prints),
else `FAIL: <what differed>`.

usage: replay-manager-routing.py"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "teamwork/lib"))
import replay_runs  # noqa: E402

KICK_OFF = "teamwork/skills/kick-off/"
REQUEST = "teamwork-manager\n\nThe owner says: 이슈 보드 화면에서 막힌 작업의 상태 표시를 눈에 띄는 색으로 바꿔줘. Route it: write the exact `start-session.py` command you would run for its worker."
MODEL, BUDGET = "sonnet", "0.75"


def words_at(ref, names):
    total = 0
    for name in names:
        shown = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:{KICK_OFF}references/{name}"], capture_output=True, text=True) if ref else None
        total += len((shown.stdout if ref else (ROOT / KICK_OFF / "references" / name).read_text()).split())
    return total


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    uses, final, stream = replay_runs.manager_run(ROOT, pathlib.Path(tempfile.mkdtemp(prefix="manager-routing-")), REQUEST, MODEL, BUDGET)
    commands = [use["input"].get("command", "") for use in uses.values() if use["name"] == "Bash"]
    opened = json.dumps([use["input"] for use in uses.values()])
    problems = []
    if not any(re.search(r"print-steering\.py(?!\s+[a-z])", command) for command in commands):
        problems.append("it never ran print-steering.py with no key")
    if "--steer visible-change" not in final + " ".join(commands):
        problems.append("its start command lacks --steer visible-change")
    problems += [f"it opened {name}" for name in ("handoff-worker-prompt.md", "manager-succession.md", "manager-ending.md") if name in opened]
    keys = subprocess.run([str(ROOT / KICK_OFF / "scripts/print-steering.py")], capture_output=True, text=True).stdout
    before, after = words_at("origin/main", ["manager.md", "handoff.md"]), words_at(None, ["manager.md", "handoff-task.md"]) + len(keys.split())
    if after >= before:
        problems.append(f"a start reads {after} words, not fewer than the {before} at origin/main")
    if problems:
        problems.append(f"it ran {[command[:60] for command in commands][:6]} and ended with {final[:300]!r}")
    print("PASS" if not problems else "FAIL: " + "; ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
