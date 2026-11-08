#!/usr/bin/env python3
"""Run the manager kick-off in a clean `claude -p` twice, on the owner's word to end and on a `succeed` start, and print `PASS` when the first opens `manager-ending.md` and not `manager-succession.md`, the second the reverse,
`manager.md` holds neither file's steps, and `count-start-text.py origin/main` prints `PASS`, which fails on a manager-read path that does not exist, else `FAIL: <what differed>`.

usage: replay-manager-handover.py"""
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "teamwork/lib"))
import replay_runs  # noqa: E402

KICK_OFF = ROOT / "teamwork/skills/kick-off"
ENDING = "teamwork-manager\n\nThe owner says: 이제 작업을 끝내자. Read the playbook file for ending yourself, then name the commands you would run."
SUCCESSION = "succeed teamwork-manager\n\nRead the playbook file for this start, then name the commands you would run."
MODEL, BUDGET = "sonnet", "0.75"


def opened_files(request):
    uses, _, stream = replay_runs.manager_run(ROOT, pathlib.Path(tempfile.mkdtemp(prefix="manager-handover-")), request, MODEL, BUDGET)
    text = json.dumps([use["input"] for use in uses.values()])
    return {name for name in ("manager-ending.md", "manager-succession.md") if name in text}


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    problems = []
    for what, request, want, other in (("ending", ENDING, "manager-ending.md", "manager-succession.md"), ("succeed", SUCCESSION, "manager-succession.md", "manager-ending.md")):
        opened = opened_files(request)
        if want not in opened or other in opened:
            problems.append(f"{what} opened {sorted(opened) or 'neither file'}")
    held = (KICK_OFF / "references/manager.md").read_text()
    problems += [f"manager.md still holds {text}" for text in ("close-session.py", "-next` in your workspace") if text in held]
    counted = subprocess.run([sys.executable, str(ROOT / "teamwork/hooks/fixtures/count-start-text.py"), "origin/main"], capture_output=True, text=True)
    if counted.stdout.strip().splitlines()[-1:] != ["PASS"]:
        problems.append("count-start-text.py origin/main did not print PASS")
    print("PASS" if not problems else "FAIL: " + "; ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
