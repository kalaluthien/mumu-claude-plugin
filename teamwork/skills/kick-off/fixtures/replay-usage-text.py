#!/usr/bin/env python3
"""Call use-board.py in ways it cannot read and check the usage it answers with. Print `ok <case>` or `fail <case>: <detail>` per case,
then `PASS` or `FAIL`, and exit 1 on any failure:
- `short`: an unknown verb prints the usage on stderr, under MOST characters, with nothing on stdout and exit 2;
- `one-line`: every verb the script runs has exactly one `usage:` line, and no line names a verb it does not run;
- `options`: each verb's line names every option the script takes for it and no other;
- `unread`: per verb, a call that gives every required option and one it does not take names that one, then prints the same usage, and exits 2;
- `help`: `comment --help`, `comment 1 -h` and `--help` print the same usage on stdout, nothing on stderr, and exit 0;
- `explained`: every option is named in a playbook under references/, where its meaning sits.

usage: replay-usage-text.py"""
import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
# the usage with each verb's rules written into it took 3,820 characters
MOST = 1600


def usage_of(said):
    """SAID without the `use-board: ` lines that name what was wrong, which differ per call while the usage after them does not."""
    return "".join(line for line in said.splitlines(True) if not line.startswith("use-board: "))


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("usage-text-") as work:
        sandbox = replay_probe.Sandbox(work)

        def call(*argv):
            done = sandbox.python(USE, *argv)
            return done.returncode, done.stdout, done.stderr

        code, out, said = call("no-such-verb")
        usage = usage_of(said)
        cases.step("short", code == 2 and not out and usage.count("usage: use-board.py ") > 1 and len(usage) < MOST, (code, len(usage), out))

        # the script's own table of verbs and options, which no call prints whole
        spec = importlib.util.spec_from_file_location("use_board", USE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        lines = {}
        for line in re.findall(r"^usage: use-board\.py (.*)$", usage, re.M):
            lines.setdefault(line.split()[0], []).append(line)
        cases.step("one-line", set(lines) == set(module.VERBS) and all(len(found) == 1 for found in lines.values()), sorted(set(lines) ^ set(module.VERBS)))

        stray = {verb: sorted(set(re.findall(r"--[a-z-]+", " ".join(lines.get(verb, [])))) ^ {flag for flag, _ in flags}) for verb, (_, _, flags) in module.VERBS.items()}
        cases.step("options", not any(stray.values()), {verb: found for verb, found in stray.items() if found})

        unread = {verb: call(verb, *(["1"] if by_place else []), *[word for flag, keywords in flags if keywords.get("required") or flag in ("--blocked",) for word in (flag, "x")],
                             "--no-such-option") for verb, (_, by_place, flags) in module.VERBS.items()}
        named = {verb: (code, out, usage_of(said), "--no-such-option" in said) for verb, (code, out, said) in unread.items()}
        cases.step("unread", all(answer == (2, "", usage, True) for answer in named.values()), [verb for verb, answer in named.items() if answer != (2, "", usage, True)])

        helped = [call("comment", "--help"), call("comment", "1", "-h"), call("--help")]
        cases.step("help", all(code == 0 and not said and out == usage for code, out, said in helped), [(code, out[:200], said[:200]) for code, out, said in helped])

        pages = "".join(path.read_text() for path in (ROOT / "skills" / "kick-off" / "references").rglob("*.md"))
        unexplained = sorted({flag for _, _, flags in module.VERBS.values() for flag, _ in flags if not re.search(re.escape(flag) + r"(?![a-z-])", pages)})
        cases.step("explained", not unexplained, unexplained)
        return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
