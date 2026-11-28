#!/usr/bin/env python3
"""Plant in a throwaway plugin a verb, a flag, a plugin environment variable and a parameter that only their own file and a fixture
name, beside one of each a skill document passes, a flag a `# kept` mark keeps and a mark that keeps nothing, and print `ok <case>`
or `FAIL <case>: <detail>` per case, then `PASS` as the last line when all hold, else `FAIL`.

usage: replay-unused-options.py

Each case runs `.github/list-unreached.py`: on the planted plugin it must list the four unpassed names and the idle mark alone, leaving
the parameters of a `_` name, a stub, a function calling `locals`, `self`, `cls`, a dunder and a subclass's method, and print the kept
flag with its reason; under six hash seeds it must print the same lines; on this repository it must exit 0, printing at least one
kept line, each with its reason."""

import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]
SCAN = REPOSITORY / ".github" / "list-unreached.py"
SKILL = "planted/skills/echo/"
SCRIPT = '''#!/usr/bin/env python3
"""Echo a word.

usage: echo-word.py say <word> [--loud]
       echo-word.py hum [--quiet] [--slow]
"""
import os
import sys

TONE = os.environ.get("PLANTED_TONE")
LEVEL = os.environ.get("PLANTED_LEVEL")


def remain(word, spare):
    return word.upper() if "--loud" in sys.argv else word


def hush(_word):
    return 0


def stub(word):
    pass


def refuse(word):
    raise NotImplementedError


def echo(word):
    return locals()


class Box:
    def size(self):
        return 1

    def make(cls):
        return 1

    def __eq__(self, other):
        return True


class Wide(Box):
    def size(self, scale=1):
        return 2


def main(args):
    print(remain(args[1], None), hush(1), stub(1), refuse, echo(1), Box().size(), Box().make(), Wide().size(), TONE, LEVEL, "--quiet" in args)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))  # kept --slow as a seam: a replay runs it slow
# kept --gone until #1
# kept --lost until #1
# kept --old until #1
# kept --spent until #1
'''
FILES = {
    "planted/.claude-plugin/plugin.json": '{"name": "planted", "version": "0.1.0"}\n',
    SKILL + "SKILL.md": "---\nname: echo\ndescription: Use when a word must be echoed.\n---\n\nRun `scripts/echo-word.py say <word> --loud` with PLANTED_TONE set.\n",
    SKILL + "scripts/echo-word.py": SCRIPT,
    SKILL + "fixtures/replay-echo.py": 'import subprocess\nsubprocess.run(["echo-word.py", "hum", "--quiet", "--slow"], env={"PLANTED_LEVEL": "1"})\n',
}
WANTED = {
    "unreached {}scripts/echo-word.py:5 verb hum".format(SKILL),
    "unreached {}scripts/echo-word.py:5 option --quiet".format(SKILL),
    "unreached {}scripts/echo-word.py:11 variable PLANTED_LEVEL".format(SKILL),
    "unreached {}scripts/echo-word.py:14 parameter spare".format(SKILL),
    *("unreached {}scripts/echo-word.py kept {}: the scan lists no such option".format(SKILL, name) for name in ("--gone", "--lost", "--old", "--spent")),
}


def check(name, problems):
    print("ok " + name if not problems else "FAIL {}: {}".format(name, "; ".join(problems)))
    return not problems


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as work:
        root = pathlib.Path(work)
        for path, text in FILES.items():
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text(text)
        result = subprocess.run([sys.executable, str(SCAN), str(root)], capture_output=True, text=True)
        seeded = {subprocess.run([sys.executable, str(SCAN), str(root)], capture_output=True, text=True, env={**os.environ, "PYTHONHASHSEED": str(seed)}).stdout
                  for seed in range(6)}
    listed = {line for line in result.stdout.splitlines() if line.startswith("unreached ")}
    problems = ["missing " + line for line in sorted(WANTED - listed)] + ["wrongly lists " + line for line in sorted(listed - WANTED)]
    problems += [] if result.returncode == 1 else ["exit {}".format(result.returncode)]
    problems += ["stderr " + result.stderr.strip()[-120:]] if result.stderr else []
    kept = "kept {}scripts/echo-word.py:5 option --slow as a seam: a replay runs it slow".format(SKILL)
    problems += [] if kept in result.stdout.splitlines() else ["missing " + kept]
    holds = check("a verb, flag, variable and parameter only their file and a fixture name are listed, those a skill passes or a mark keeps are not, and a mark that keeps nothing is", problems)
    holds = check("the scan prints the same lines under every hash seed", [] if len(seeded) == 1 else ["{} different outputs".format(len(seeded))]) and holds
    clean = subprocess.run([sys.executable, str(SCAN), str(REPOSITORY)], capture_output=True, text=True)
    kept = [line for line in clean.stdout.splitlines() if line.startswith("kept ")]
    problems = [] if clean.returncode == 0 else [line for line in clean.stdout.splitlines() if line.startswith("unreached ")][:5] or ["exit {}".format(clean.returncode)]
    problems += [] if kept else ["no kept line, though the table names options the repository keeps"]
    problems += ["a kept line names no reason: " + line for line in kept if not (" until #" in line or " as a seam: " in line)]
    holds = check("the repository lists nothing and names each kept option's reason", problems) and holds
    print("PASS" if holds else "FAIL")
    return 0 if holds else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
