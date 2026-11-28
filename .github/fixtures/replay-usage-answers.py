#!/usr/bin/env python3
"""Plant scripts that answer a help call or an unknown flag rightly or wrongly in a throwaway root, run the repository check's script
call on it, and print `ok <case>` or `FAIL <case>: <detail>` per case, then `PASS` as the last line when all hold, else `FAIL`.

usage: replay-usage-answers.py

Cases: a copy of `.github/script-template.py` is named by no line, and a script that refuses `--help` with exit 2, one that prints its
help on stderr, one that prints help without `usage:`, one that prints help on both streams, one that answers an unknown flag with
exit 0, and one that answers an unknown flag with nothing in 30 s are each named. Exits 0 on `PASS`, 1 on `FAIL`, 2 with this text for
any argument. Standard library only, Python 3.9."""

import importlib.util
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location("check_repository", REPOSITORY / ".github" / "check-repository.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)
REFUSE = 'print(__doc__, file=sys.stderr)\nsys.exit(2)\n'
HELP_ON_STDERR = 'if "--help" in sys.argv:\n    print(__doc__, file=sys.stderr)\n    sys.exit(0)\n' + REFUSE
HELP_WITHOUT_USAGE = 'if "--help" in sys.argv:\n    print("Plant.")\n    sys.exit(0)\n' + REFUSE
HELP_ON_BOTH = 'if "--help" in sys.argv:\n    print(__doc__)\n    print(__doc__, file=sys.stderr)\n    sys.exit(0)\n' + REFUSE
HANGS = 'import time\nif "--help" in sys.argv:\n    print(__doc__)\n    sys.exit(0)\ntime.sleep(60)\n'
UNKNOWN_SUCCEEDS = 'if "--help" in sys.argv:\n    print(__doc__)\n    sys.exit(0)\nprint(__doc__, file=sys.stderr)\n'
# name: (script text, (flag named in a failure line or None when no line may name the script))
CASES = {
    "template": ((REPOSITORY / ".github" / "script-template.py").read_text(), None),
    "help-refused": (REFUSE, "--help"),
    "help-on-stderr": (HELP_ON_STDERR, "--help"),
    "help-without-usage": (HELP_WITHOUT_USAGE, "--help"),
    "help-on-both": (HELP_ON_BOTH, "--help"),
    "unknown-succeeds": (UNKNOWN_SUCCEEDS, CHECK.UNKNOWN_FLAG),
    "hangs": (HANGS, CHECK.UNKNOWN_FLAG),
}


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as root:
        files = []
        for name, (text, _) in CASES.items():
            path = pathlib.Path(root, ".github", f"{name}.py")
            path.parent.mkdir(exist_ok=True)
            path.write_text(text if text.startswith("#!") else f'"""Plant.\n\nusage: {name}.py"""\nimport sys\n{text}')
            files.append(f".github/{name}.py")
        failures = []
        called = CHECK.check_scripts(root, files, failures)
    passed = called == len(CASES)
    for name, (_, flag) in CASES.items():
        named = [line for line in failures if line.startswith(f"usage .github/{name}.py: ")]
        held = not named if flag is None else any(line.startswith(f"usage .github/{name}.py: {flag} gave ") for line in named)
        print(f"ok {name}" if held else f"FAIL {name}: {named or 'not named'}")
        passed = passed and held
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
