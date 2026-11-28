#!/usr/bin/env python3
"""Plant a skill script that lists its steps by a `steps` call in a throwaway git root, run the repository check's fixture runners on
it as files change, and print `ok <case>` or `FAIL <case>: <detail>` per case, then `PASS` as the last line when all hold, else `FAIL`.

usage: replay-runner-steps.py

Cases:
- `each`: the first check runs each listed step once, as its own call;
- `replayed`: a second check on the same files runs none;
- `elsewhere`: a change in the plugin outside the script's skill and the plugin's `lib/` runs none;
- `fed`: a change in the plugin's `lib/` runs each step again;
- `named`: a step that fails is named with its step, and the other step is not;
- `unlisted`: a script whose `steps` call lists nothing is named.
Exits 0 on `PASS`, 1 on `FAIL`, 2 with this text for any argument. Standard library only, Python 3.9."""

import importlib.util
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("check_repository", HERE.parent / "check-repository.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)
SCRIPT = "plugin/skills/skill/scripts/run-stub.py"
STUB = '''"""Stand in for a skill script whose steps run one by one.

usage: run-stub.py steps
usage: run-stub.py [one] [two]"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if sys.argv[1:] == ["steps"]:
    print("" if (HERE / "unlisted").exists() else "one\\ntwo")
    sys.exit(0)
with open(HERE.parents[3] / "calls.log", "a") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
sys.exit(1 if sys.argv[1:] == ["two"] and (HERE / "fail").exists() else 0)
'''


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    passed = True

    def step(name, held, detail):
        nonlocal passed
        print(f"ok {name}" if held else f"FAIL {name}: {detail}")
        passed = passed and held

    with tempfile.TemporaryDirectory() as scratch:
        root = pathlib.Path(scratch)
        log = root / "calls.log"

        def plant(path, text):
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text(text)
            subprocess.run(["git", "-C", root, "add", "-A"], check=True)

        def check():
            log.write_text("")
            failures = []
            CHECK.run_fixtures(str(root), CHECK.list_files(str(root)), failures, set())
            return sorted(log.read_text().split()), failures

        subprocess.run(["git", "init", "-q", root], check=True)
        (root / ".gitignore").write_text("calls.log\n")
        plant(SCRIPT, STUB)
        plant("plugin/lib/shared.txt", "one\n")
        plant("plugin/other/notes.txt", "one\n")
        got = check()
        step("each", got == (["one", "two"], []), got)
        got = check()
        step("replayed", got == ([], []), got)
        plant("plugin/other/notes.txt", "two\n")
        got = check()
        step("elsewhere", got == ([], []), got)
        plant("plugin/lib/shared.txt", "two\n")
        got = check()
        step("fed", got == (["one", "two"], []), got)
        plant("plugin/skills/skill/scripts/fail", "")
        calls, failures = check()
        step("named", calls == ["one", "two"] and len(failures) == 1 and failures[0].startswith(f"fixture {SCRIPT} two: exit 1"), (calls, failures))
        plant("plugin/skills/skill/scripts/unlisted", "")
        calls, failures = check()
        step("unlisted", calls == [] and failures == [f"fixture {SCRIPT} steps: exit 0, no step listed"], (calls, failures))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
