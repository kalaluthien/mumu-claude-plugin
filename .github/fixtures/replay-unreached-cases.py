#!/usr/bin/env python3
"""Plant each way a file, function or import can hide or be wrongly listed on a throwaway copy of this repository, and print `ok <case>` or `FAIL <case>: <detail>` per case, then `PASS` as the last line when all hold, else `FAIL`.

usage: replay-unreached-cases.py [--repository-check]

By default each case runs `.github/list-unreached.py` on the copy and requires the lines it names. `--repository-check` plants
one unreached file in each plugin and requires `.github/check-repository.py` of the copy to fail naming it, to pass on the
copy with none planted, and the old home of the checker in `teamwork/` to be gone."""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]
SKILL = "teamwork/skills/kick-off/"
SKILL_MD = SKILL + "SKILL.md"
MAIN = "\n\ndef main(args):\n    return 0\n"
FILE_SKILL = SKILL_MD + " names "

# name: (planted files, text appended to existing files, lines that must be printed, paths that must not be named)
CASES = {
    "a dead file in a folder a doc names by its files is listed": (
        {SKILL + "references/adapters/planted-dead.md": "dead\n"}, {}, ["unreached " + SKILL + "references/adapters/planted-dead.md"], []),
    "a live file named by its path is not listed": (
        {SKILL + "references/planted-live.md": "live\n"}, {SKILL_MD: "\nsee references/planted-live.md\n"}, [], [SKILL + "references/planted-live.md"]),
    "a dead twin of a live file name is listed": (
        {SKILL + "references/planted-twin.md": "live\n", SKILL + "references/adapters/planted-twin.md": "dead\n"},
        {SKILL_MD: "\nsee references/planted-twin.md\n"}, ["unreached " + SKILL + "references/adapters/planted-twin.md"], [SKILL + "references/planted-twin.md"]),
    "two dead files naming each other are listed": (
        {SKILL + "references/planted-one.md": "see planted-two.md\n", SKILL + "references/planted-two.md": "see planted-one.md\n"}, {},
        ["unreached " + SKILL + "references/planted-one.md", "unreached " + SKILL + "references/planted-two.md"], []),
    "a dead script and the doc that runs it are listed": (
        {SKILL + "scripts/planted-dead.py": MAIN, SKILL + "references/planted-run.md": "run planted-dead.py\n"}, {},
        ["unreached " + SKILL + "scripts/planted-dead.py", "unreached " + SKILL + "references/planted-run.md"], []),
    "a file with a space in its name is listed": (
        {SKILL + "references/planted dead.md": "dead\n"}, {}, ["unreached " + SKILL + "references/planted dead.md"], []),
    "a future import and a name in __all__ are not unused": (
        {SKILL + "scripts/planted-live.py": "from __future__ import annotations\nimport os\n__all__ = ['os']\n" + MAIN},
        {SKILL_MD: "\nrun scripts/planted-live.py\n"}, [], [SKILL + "scripts/planted-live.py"]),
    "an import inside try that nothing uses is listed": (
        {SKILL + "scripts/planted-try.py": "try:\n    import json\nexcept ImportError:\n    json = None\n" + MAIN},
        {SKILL_MD: "\nrun scripts/planted-try.py\n"}, ["unreached " + SKILL + "scripts/planted-try.py:2 import json"], []),
    "a recursive function nothing else calls is listed": (
        {SKILL + "scripts/planted-rec.py": "def fact(n):\n    return 1 if n < 2 else n * fact(n - 1)\n" + MAIN},
        {SKILL_MD: "\nrun scripts/planted-rec.py\n"}, ["unreached " + SKILL + "scripts/planted-rec.py:1 fact"], []),
    "a function named only in a docstring is listed": (
        {SKILL + "scripts/planted-doc.py": "def helper_one():\n    return 1\n\n\ndef main(args):\n    \"\"\"call helper_one later\"\"\"\n    return 0\n"},
        {SKILL_MD: "\nrun scripts/planted-doc.py\n"}, ["unreached " + SKILL + "scripts/planted-doc.py:1 helper_one"], []),
    "a helper only a dead function calls is listed with it": (
        {SKILL + "scripts/planted-chain.py": "def planted_inner():\n    return 1\n\n\ndef planted_outer():\n    return planted_inner()\n" + MAIN},
        {SKILL_MD: "\nrun scripts/planted-chain.py\n"},
        ["unreached " + SKILL + "scripts/planted-chain.py:1 planted_inner", "unreached " + SKILL + "scripts/planted-chain.py:5 planted_outer"], []),
    "a method nothing calls is listed": (
        {SKILL + "scripts/planted-cls.py": "class Box:\n    def spare(self):\n        return 1\n\n\ndef main(args):\n    return Box()\n"},
        {SKILL_MD: "\nrun scripts/planted-cls.py\n"}, ["unreached " + SKILL + "scripts/planted-cls.py:2 spare"], []),
    "functions of a file that calls getattr on a computed name are not unused": (
        {SKILL + "scripts/planted-dispatch.py": "def one():\n    return 1\n\n\ndef main(args):\n    return getattr(__import__('sys'), args[0])\n"},
        {SKILL_MD: "\nrun scripts/planted-dispatch.py\n"}, [], [SKILL + "scripts/planted-dispatch.py"]),
    "a file with a NUL byte does not stop the run": (
        {"teamwork/lib/planted_nul.py": "X = 1\x00\n"}, {}, ["unreached teamwork/lib/planted_nul.py"], []),
    "a lib module named only in a comment is not listed": (
        {"teamwork/lib/planted_adapter.py": "X = 1\n"}, {"teamwork/lib/agent.py": "\n# adapters: lib/planted_adapter.py\n"}, [], ["teamwork/lib/planted_adapter.py"]),
    "a lib module imported by a dead script is listed": (
        {"teamwork/lib/planted_lib.py": "X = 1\n", SKILL + "scripts/planted-user.py": "import planted_lib\n"}, {},
        ["unreached teamwork/lib/planted_lib.py", "unreached " + SKILL + "scripts/planted-user.py"], []),
    "a module imported inside a lib package is not listed": (
        {"teamwork/lib/planted_pkg/__init__.py": "", "teamwork/lib/planted_pkg/inner.py": "X = 1\n", "teamwork/lib/planted_pkg/outer.py": "from . import inner\nY = inner.X\n",
         SKILL + "scripts/planted-pkg.py": "from planted_pkg.outer import Y\nprint(Y)\n"},
        {SKILL_MD: "\nrun scripts/planted-pkg.py\n"}, [], ["teamwork/lib/planted_pkg"]),
    "a fixture that replays a live script is not listed, one that replays nothing live is": (
        {"teamwork/hooks/fixtures/replay-planted.py": "# replays route-event.py\n", "teamwork/hooks/fixtures/planted-case.json": "{}\n",
         "teamwork/hooks/planted-dead.py": MAIN, "teamwork/hooks/fixtures/replay-dead.py": "# replays planted-dead.py\n"}, {},
        ["unreached teamwork/hooks/planted-dead.py", "unreached teamwork/hooks/fixtures/replay-dead.py", "unreached teamwork/hooks/fixtures/planted-case.json"],
        ["teamwork/hooks/fixtures/replay-planted.py"]),
    "a lib module only a live fixture imports is not listed": (
        {"teamwork/lib/planted_helper.py": "X = 1\n", "teamwork/hooks/fixtures/replay-helper.py": "# replays route-event.py\nimport planted_helper\nprint(planted_helper.X)\n"},
        {}, [], ["teamwork/lib/planted_helper.py"]),
    "data below a folder a live program lists is not listed, a dead script beside it is": (
        {SKILL + "scripts/planted-reader.py": "import pathlib\nprint(list(pathlib.Path('planted-data').glob('*.json')))\n", SKILL + "fixtures/planted-data/a.json": "{}\n", SKILL + "fixtures/planted-data/b.json": "{}\n", SKILL + "fixtures/planted-scripts/dead.py": MAIN},
        {SKILL_MD: "\nrun scripts/planted-reader.py\n"}, ["unreached " + SKILL + "fixtures/planted-scripts/dead.py"], [SKILL + "fixtures/planted-data/"]),
    "a function named by a one-word docstring is still unused": (
        {SKILL + "scripts/planted-doc-word.py": '"""planted_hidden"""\n\n\ndef planted_hidden():\n    return 1\n' + MAIN},
        {SKILL_MD: "\nrun scripts/planted-doc-word.py\n"}, ["unreached " + SKILL + "scripts/planted-doc-word.py:4 planted_hidden"], []),
    "a command in bin named bare is not listed": (
        {"teamwork/bin/planted-command": "#!/bin/sh\n"}, {SKILL_MD: "\nrun planted-command\n"}, [], ["teamwork/bin/planted-command"]),
    "a script imported without its extension is not listed, one nobody imports is": (
        {"teamwork/hooks/planted-module.ts": "export const x = 1\n", "teamwork/hooks/planted-orphan.ts": "export const y = 1\n"},
        {"teamwork/hooks/draw-issue-pane.tsx": "\nimport { x } from './planted-module'\n"}, ["unreached teamwork/hooks/planted-orphan.ts"], ["teamwork/hooks/planted-module.ts"]),
    "a dead file in each other plugin is listed": (
        {"homework/lib/planted-dead.md": "dead\n", "paperwork/lib/planted-dead.md": "dead\n"}, {},
        ["unreached homework/lib/planted-dead.md", "unreached paperwork/lib/planted-dead.md"], []),
}


def copy_repository(target):
    """A copy of the tracked and untracked-but-not-ignored files of this repository in target."""
    out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=REPOSITORY, capture_output=True, text=True, check=True).stdout
    for path in filter(None, out.split("\0")):
        if (REPOSITORY / path).is_file():
            (target / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPOSITORY / path, target / path)


def plant(root, files, appended):
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)
    for path, text in appended.items():
        with open(root / path, "a") as handle:
            handle.write(text)


def run_cases(base):
    """Print a line per case; return whether all hold."""
    holds = True
    script = REPOSITORY / ".github" / "list-unreached.py"
    clean = subprocess.run([sys.executable, str(script), str(base)], capture_output=True, text=True)
    detail = "" if clean.returncode == 0 else clean.stdout.strip().replace("\n", "; ") + clean.stderr.strip()
    print(("ok" if clean.returncode == 0 else "FAIL") + " the repository itself lists nothing" + (": " + detail if detail else ""))
    holds = clean.returncode == 0
    usage = subprocess.run([sys.executable, str(script), "--bogus"], capture_output=True, text=True)
    good = usage.returncode == 2 and not usage.stdout and "usage: list-unreached.py" in usage.stderr
    print(("ok" if good else "FAIL") + " an option it cannot read prints its usage on stderr and exits 2")
    holds = holds and good
    missing = subprocess.run([sys.executable, str(script), str(base / "no-such-folder")], capture_output=True, text=True)
    good = missing.returncode == 2 and not missing.stdout and "usage: list-unreached.py" in missing.stderr
    print(("ok" if good else "FAIL") + " a root that is no folder prints its usage on stderr and exits 2")
    holds = holds and good
    for name, (files, appended, wanted, absent) in CASES.items():
        with tempfile.TemporaryDirectory() as work:
            root = pathlib.Path(work)
            shutil.copytree(base, root, dirs_exist_ok=True)
            plant(root, files, appended)
            result = subprocess.run([sys.executable, str(script), str(root)], capture_output=True, text=True)
            lines = result.stdout.splitlines()
            problems = ["missing " + want for want in wanted if want not in lines]
            problems += ["wrongly names " + path for path in absent for line in lines if path in line]
            problems += [] if result.returncode == (1 if wanted else 0) else ["exit {}".format(result.returncode)]
            problems += ["stderr " + result.stderr.strip()[-120:]] if result.stderr else []
            print("ok " + name if not problems else "FAIL {}: {}".format(name, "; ".join(problems)))
            holds = holds and not problems
    return holds


def run_repository_check(base):
    """Print a line per plugin; return whether the check fails on a planted dead file in each and passes on none."""
    holds = True
    check = REPOSITORY / ".github" / "check-repository.py"
    plain = subprocess.run([sys.executable, str(check), str(base)], capture_output=True, text=True)
    print(("ok" if plain.returncode == 0 else "FAIL") + " the check passes on the repository with nothing planted")
    holds = plain.returncode == 0
    gone = not (REPOSITORY / "teamwork/skills/kick-off/scripts/list-unreached.py").exists()
    print(("ok" if gone else "FAIL") + " the checker no longer sits in teamwork")
    holds = holds and gone
    with tempfile.TemporaryDirectory() as work:
        root = pathlib.Path(work)
        shutil.copytree(base, root, dirs_exist_ok=True)
        plant(root, {"teamwork/lib/planted-dead.md": "dead\n"}, {})
        (root / ".github" / "list-unreached.py").write_text("")
        result = subprocess.run([sys.executable, str(root / ".github" / "check-repository.py"), str(root)], capture_output=True, text=True)
        good = result.returncode == 1
        print(("ok" if good else "FAIL") + " the check fails when the lister prints nothing")
        holds = holds and good
    missing = subprocess.run([sys.executable, str(check), str(base / "no-such-folder")], capture_output=True, text=True)
    good = missing.returncode == 2 and not missing.stdout and "usage: check-repository.py" in missing.stderr
    print(("ok" if good else "FAIL") + " a root that is no folder prints the usage on stderr and exits 2")
    holds = holds and good
    for manifest in sorted(base.glob("*/.claude-plugin/plugin.json")):
        plugin = manifest.parent.parent.name
        with tempfile.TemporaryDirectory() as work:
            root = pathlib.Path(work)
            shutil.copytree(base, root, dirs_exist_ok=True)
            planted = "{}/lib/planted-dead.md".format(plugin)
            plant(root, {planted: "dead\n"}, {})
            result = subprocess.run([sys.executable, str(root / ".github" / "check-repository.py"), str(root)], capture_output=True, text=True)
            good = result.returncode == 1 and "unreached " + planted in result.stdout.splitlines()
            print(("ok" if good else "FAIL") + " the check fails on a dead file planted in " + plugin)
            holds = holds and good
    return holds


def main(args):
    if args not in ([], ["--repository-check"]):
        print(__doc__, file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as work:
        base = pathlib.Path(work)
        copy_repository(base)
        holds = run_repository_check(base) if args else run_cases(base)
    print("PASS" if holds else "FAIL")
    return 0 if holds else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
