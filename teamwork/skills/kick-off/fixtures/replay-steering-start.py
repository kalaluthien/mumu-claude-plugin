#!/usr/bin/env python3
"""Start workers in a sandbox with `--steer` of two keys, of none, of a key beside one that takes its line alone, of an unknown key and of lines over the cap, and print `PASS` when
the prompt of the first ends with exactly the two lines of the steering table and equals the lines `print-steering.py` prints for those keys, the prompt of the second equals the plain kick-off, and every refused start exits 2 with no agent started, else `FAIL: <what differed>`.

usage: replay-steering-start.py"""
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]  # the plugin
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

KICKOFF = "Run the teamwork:kick-off skill with these arguments: "
LONG_ROW = "| long | any | a case with a line over the cap | " + " ".join(["word"] * 120) + " |\n"


def table_line(key):
    return re.search(rf"^\| {key} \| .*? \| .*? \| (.*) \|$", (ROOT / "skills/kick-off/assets/handoff-worker-prompt.md").read_text(), re.M)[1]


def run(box, plugin, *command):
    """The finished COMMAND of PLUGIN's kick-off scripts beside a live manager, and the prompts it sent."""
    box.herdr([replay_probe.agent("teamwork-manager", 2)])
    box.calls.unlink(missing_ok=True)
    done = box.run([plugin / "skills/kick-off/scripts" / command[0], *command[1:]], TEAMWORK_START_SESSION_TIMEOUT="3")
    return done, [call[3] for call in box.herdr_calls() if call[:2] == ["agent", "prompt"]]


def start(box, name, *steering):
    return ["start-session.py", name, box.repository, f"worker {name} manager teamwork-manager https://example.com/1", "--model", "haiku", "--effort", "medium", *steering]


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("steering-start-") as work:
        box = replay_probe.Sandbox(work)
        problems = check(box)
    return replay_probe.fail("; ".join(problems)) if problems else replay_probe.Cases().finish()


def check(box):
    copy = box.work / "teamwork"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__"))
    with open(copy / "skills/kick-off/assets/handoff-worker-prompt.md", "a") as table:
        table.write(LONG_ROW)
    wanted = f"{table_line('visible-change')} {table_line('new-mechanism')}"
    plain = KICKOFF + "worker a-worker manager teamwork-manager https://example.com/1"
    problems = []
    done, prompts = run(box, ROOT, *start(box, "a-worker", "--steer", "visible-change", "--steer", "new-mechanism"))
    told = box.run([ROOT / "skills/kick-off/scripts/print-steering.py", "visible-change", "new-mechanism"]).stdout.strip()
    if prompts != [f"{plain} — {wanted}"] or told != wanted:
        problems.append(f"two keys sent {prompts}, print-steering printed {told!r}")
    done, prompts = run(box, ROOT, *start(box, "a-worker"))
    if prompts != [plain]:
        problems.append(f"no key sent {prompts}")
    for refused in (("research", "cleanup"), ("nope",), ("long",)):
        done, prompts = run(box, copy, *start(box, "a-worker", *[word for key in refused for word in ("--steer", key)]))
        if done.returncode != 2 or prompts:
            problems.append(f"--steer {' '.join(refused)} exited {done.returncode} and sent {prompts}")
    return problems


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
