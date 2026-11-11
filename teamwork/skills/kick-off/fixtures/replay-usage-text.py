#!/usr/bin/env python3
"""Call use-board.py in ways it cannot read and check the usage it answers with. Print `ok <case>` or `fail <case>: <detail>` per case,
then `PASS` or `FAIL`, and exit 1 on any failure:
- `short`: an unknown verb prints the usage on stderr, under MOST characters, with nothing on stdout and exit 2;
- `one-line`: every verb the script runs has exactly one `usage:` line, and no line names a verb it does not run;
- `options`: each verb's line names every option the script takes for it and no other;
- `unread`: per verb, a call with an option it does not take prints the same usage and exits 2;
- `explained`: every option is named in a playbook under references/, where its meaning sits.

usage: replay-usage-text.py"""
import importlib.util
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
# the usage with each verb's rules written into it took 3,820 characters
MOST = 1600
failed = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[:600]}", flush=True)
    if not ok:
        failed.append(name)


def call(*argv):
    done = subprocess.run([sys.executable, str(USE), *argv], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    code, out, usage = call("no-such-verb")
    step("short", code == 2 and not out and usage.count("usage: use-board.py ") > 1 and len(usage) < MOST, (code, len(usage), out))

    spec = importlib.util.spec_from_file_location("use_board", USE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    lines = {}
    for line in re.findall(r"^usage: use-board\.py (.*)$", usage, re.M):
        lines.setdefault(line.split()[0], []).append(line)
    step("one-line", set(lines) == set(module.VERBS) and all(len(found) == 1 for found in lines.values()), sorted(set(lines) ^ set(module.VERBS)))

    stray = {verb: sorted(set(re.findall(r"--[a-z-]+", " ".join(lines.get(verb, [])))) ^ set(options)) for verb, (_, options, _) in module.VERBS.items()}
    step("options", not any(stray.values()), {verb: found for verb, found in stray.items() if found})

    unread = {verb: call(verb, "1", "--no-such-option") for verb in module.VERBS}
    step("unread", all(answer == (2, "", usage) for answer in unread.values()), [verb for verb, answer in unread.items() if answer != (2, "", usage)])

    pages = "".join(path.read_text() for path in (ROOT / "skills" / "kick-off" / "references").rglob("*.md"))
    unexplained = sorted({option for _, options, _ in module.VERBS.values() for option in options if not re.search(re.escape(option) + r"(?![a-z-])", pages)})
    step("explained", not unexplained, unexplained)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
