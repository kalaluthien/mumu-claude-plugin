#!/usr/bin/env python3
"""Plant a skill script that lists its steps by a `steps` call in a throwaway git root, run the repository check's fixture runners on
it as files change, and print `ok <case>` or `FAIL <case>: <detail>` per case, then `PASS` as the last line when all hold, else `FAIL`.

usage: replay-runner-steps.py

Cases:
- `each`: the first check runs each listed step once, as its own call;
- `replayed`: a second check on the same files runs none;
- `elsewhere`: a change in the plugin outside the script's skill and the plugin's `lib/` runs none;
- `fed`: a change in the plugin's `lib/` runs each step again;
- `named`: a step that fails is named with its step, its last line cut to 200 characters and each `FAIL` line before it beneath, and
  the other step is not;
- `unlisted`: a script whose `steps` call lists nothing is named;
- `fixtures`: a skill script whose usage lists a `fixtures` call runs with it;
- `not-stepped`: a script listing steps outside a skill's `scripts/` folder, or in a language the check runs none of, runs no step;
- `runners`: a `fixtures/replay-*` runner in Python and one in TypeScript each run once, by their interpreter;
- `fresh-step`, `fresh-script`, `fresh-all`: on the same files, a fresh set naming one step runs it alone, one naming the script runs
  each of its steps, and `True` runs every call;
- `no-git`: a copy outside git runs each step on every check;
- `node`: a `.cjs` script's step runs by node, beside the plugin-wide runners its new file reruns;
- `broken`, `slow`, `missing`: a `steps` call that exits non-zero, runs past STEPS_SECONDS or whose interpreter is missing is named
  and none of its steps run.
Exits 0 on `PASS`, 1 on `FAIL`, 2 with this text for any argument. Standard library only, Python 3.9."""

import importlib.util
import pathlib
import shutil
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
    if (HERE / "slow").exists():
        import time
        time.sleep(5)
    print("" if (HERE / "unlisted").exists() else "one\\ntwo")
    sys.exit(1 if (HERE / "broken").exists() else 0)
with open(HERE.parents[3] / "calls.log", "a") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
if sys.argv[1:] == ["two"] and (HERE / "fail").exists():
    print("FAIL detail\\n" + "x" * 300)
    sys.exit(1)
'''

FIXTURES = '''"""Stand in for a skill script that checks the fixtures beside it.

usage: check-stub.py fixtures"""
import pathlib
import sys

with open(pathlib.Path(__file__).resolve().parents[4] / "calls.log", "a") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
'''

RUNNER = '''import pathlib

with open(pathlib.Path(__file__).resolve().parents[2] / "calls.log", "a") as log:
    log.write("python\\n")
'''

NODE = '''// usage: run-node.cjs steps
const fs = require("fs");
if (process.argv[2] === "steps") console.log("three");
else fs.appendFileSync(`${__dirname}/../../../../calls.log`, process.argv[2] + "\\n");
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

        def check(fresh=frozenset(), where=root):
            (where / "calls.log").write_text("")
            failures = []
            CHECK.run_fixtures(str(where), CHECK.list_files(str(where)), failures, fresh if fresh is True else set(fresh))
            return sorted((where / "calls.log").read_text().split()), failures

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
        step("named", calls == ["one", "two"] and failures == [f"fixture {SCRIPT} two: exit 1, {'x' * 200}\n    FAIL detail"], (calls, failures))
        plant("plugin/skills/skill/scripts/unlisted", "")
        calls, failures = check()
        step("unlisted", calls == [] and failures == [f"fixture {SCRIPT} steps: exit 0, no step listed"], (calls, failures))
        plant("plugin/skills/skill/scripts/check-stub.py", FIXTURES)
        got = check()
        step("fixtures", got == (["fixtures"], [f"fixture {SCRIPT} steps: exit 0, no step listed"]), got)
        plant("plugin/skills/skill/lib/run-lib.py", STUB)
        plant("plugin/skills/skill/scripts/run-stub.sh", STUB)
        got = check()
        step("not-stepped", got == (["fixtures"], [f"fixture {SCRIPT} steps: exit 0, no step listed"]), got)
        for name in ("fail", "unlisted"):
            (root / "plugin/skills/skill/scripts" / name).unlink()
        plant("plugin/fixtures/replay-python.py", RUNNER)
        plant("plugin/fixtures/replay-script.ts", 'import { appendFileSync } from "fs";\nappendFileSync(`${import.meta.dir}/../../calls.log`, "typescript\\n");\n')
        got = check()
        step("runners", got == (["fixtures", "one", "python", "two", "typescript"], []), got)
        got = check({SCRIPT + " two"})
        step("fresh-step", got == (["two"], []), got)
        got = check({SCRIPT})
        step("fresh-script", got == (["one", "two"], []), got)
        got = check(True)
        step("fresh-all", got == (["fixtures", "one", "python", "two", "typescript"], []), got)
        with tempfile.TemporaryDirectory() as outside:
            copy = pathlib.Path(outside) / "copy"
            shutil.copytree(root, copy, ignore=shutil.ignore_patterns(".git"))
            runs = [check(where=copy) for _ in range(2)]
            step("no-git", all(got == (["fixtures", "one", "python", "two", "typescript"], []) for got in runs), runs)
        plant("plugin/skills/node/scripts/run-node.cjs", NODE)
        got = check()
        step("node", got == (["fixtures", "python", "three", "typescript"], []), got)
        for name, flag, setting, failure in (
                ("broken", "broken", None, "exit 1, no step listed"),
                ("slow", "slow", ("STEPS_SECONDS", 1), "Command"),
                ("missing", None, ("INTERPRETERS", {**CHECK.INTERPRETERS, ".py": [str(root / "missing")]}), "[Errno")):
            if flag:
                plant(f"plugin/skills/skill/scripts/{flag}", "")
            kept = setting and getattr(CHECK, setting[0])
            if setting:
                setattr(CHECK, *setting)
            calls, failures = check(True)
            if setting:
                setattr(CHECK, setting[0], kept)
            if flag:
                (root / "plugin/skills/skill/scripts" / flag).unlink()
            step(name, "one" not in calls and any(line.startswith(f"fixture {SCRIPT} steps: {failure}") for line in failures), (calls, failures))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
