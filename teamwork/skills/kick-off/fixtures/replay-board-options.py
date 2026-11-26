#!/usr/bin/env python3
"""Replay board writes given as named options on a scratch git board, printing `ok <case>` or `fail <case>: <what it saw>` per case,
then `PASS` or `FAIL`, and exiting 1 on any failure. Cases:
- `named-writes`: `file`, `comment --reported`, `comment --blocked --asks owner --option`, `decide --decision`, `edit --body --reason --base`,
  `resolve --summary`, `title --title`, `label --label`, `hold --holders` and `depend --depends` each exit 0, then `read`, `read --as worker`,
  `read --body` and `reopen` in their old form; `read` shows each keyword line the script built, `read --full` the edit's diff, and each stored `comments/<k>.json`
  keeps only keys board-record-schema.json names;
- `named-docs`: every `use-board.py` write spelled in a file under teamwork/ outside a `fixtures/` folder parses through the script's own parser;
- `named-lint`: `check-criteria.py --reason` passes a good reason, refuses one that opens with a keyword, and refuses `--edit-line`;
- `refused-missing`: a write without `--base`, `--reason`, `--body`, `--decision`, `--summary` or `--title`, the `edit` whose `--reason` opens
  `REPORTED:` with no `--base`, and a stale `--base` each exit 2, name the option and leave the board ref where it was;
- `refused-misplaced`: a `--text` file that opens `DECIDED:`, `BLOCKED:` or `REPORTED:`, both `--blocked` and `--reported`, an `--asks` other than `owner`, `--option` on a `--reported` line, one `--option` on a question
  to the owner, a `--depends` word that names no task, an empty `--reported`, a two-line `--decision`, a `--live-runs` that is no count,
  `read --body` with `--full`, a task word that names no task, and the old
  `edit <task> <file> "DECIDED: …" --base <sha>` call each exit 2, name the option to use and leave the board ref where it was.

usage: replay-board-options.py"""
import ast
import contextlib
import importlib.util
import io
import json
import pathlib
import re
import shlex
import sys

HERE = pathlib.Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
sys.path.insert(0, str(PLUGIN / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = HERE.parent / "scripts"
USE = SCRIPTS / "use-board.py"
SCHEMA = json.loads((HERE.parent / "assets" / "board-record-schema.json").read_text())
WRITES = ("comment", "decide", "hold", "depend", "file", "edit", "title", "resolve", "label", "reopen")
SPELLED = re.compile(r"use-board\.py[ \t]+(" + "|".join(WRITES) + r")\b([^`\n]*)")


def use(*argv):
    return box.python(USE, *map(str, argv), claude=["--name", "a-manager"])


def ref():
    return replay_probe.sh("git", "rev-parse", "-q", "--verify", "refs/teamwork-blackboard", cwd=box.repository, environment=box.environment, check=False).stdout.strip()


def strings(path):
    """The texts of PATH a reader meets: a Python file's string literals, each f-string's fields as `X`, else the whole file."""
    text = path.read_text(errors="replace")
    if path.suffix != ".py":
        return [text]
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [text]
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            found.append("".join(part.value if isinstance(part, ast.Constant) else "X" for part in node.values))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.append(node.value)
    return found


def words_of(spelled):
    """The call SPELLED as argv, each `<placeholder>` a word, each `( a | b )` its first choice, brackets and `...` dropped."""
    text = re.sub(r"<[^<>]*>", "x", spelled.replace("\\|", "|"))
    text = re.sub(r"\(\s*([^()|]*?)\s*\|[^()]*\)", r"\1", text)
    return shlex.split(re.sub(r"\[|\]|\.\.\.|…", " ", text))


def named_docs(step):
    spec = importlib.util.spec_from_file_location("use_board", USE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    wrong = []
    paths = [path for path in PLUGIN.rglob("*") if path.is_file() and "fixtures" not in path.relative_to(PLUGIN).parts and "__pycache__" not in path.parts
             and path.suffix in (".md", ".py", ".json", ".ts", ".tsx", ".sh", ".txt")]
    checked = 0
    for path in paths:
        for text in strings(path):
            for verb, rest in SPELLED.findall(text):
                if not rest.strip() or rest.lstrip().startswith(("would", "or", "and", ",")):
                    continue  # the verb named in prose, not a call
                try:
                    argv = [verb, *words_of(rest)]
                except ValueError as e:
                    wrong.append(f"{path.relative_to(PLUGIN)}: `use-board.py {verb}{rest}` does not split: {e}")
                    continue
                said = io.StringIO()
                try:
                    with contextlib.redirect_stderr(said):
                        module.parser().parse_args(argv)
                    checked += 1
                except SystemExit:
                    wrong.append(f"{path.relative_to(PLUGIN)}: `use-board.py {verb}{rest}` -> {said.getvalue().splitlines()[0] if said.getvalue() else 'refused'}")
    step("named-docs", not wrong and checked >= 10, wrong or f"only {checked} spelled writes found")


def named_lint(step):
    check = [sys.executable, str(SCRIPTS / "check-criteria.py")]
    good, bad, old = (box.run([*check, *argv]) for argv in (["--reason", "add the probe's second case"], ["--reason", "DECIDED: add the probe"],
                                                             ["--edit-line", "DECIDED: add the probe"]))
    step("named-lint", (good.returncode, good.stdout) == (0, "") and bad.returncode == 1 and "write:" in bad.stdout and "--reason" in bad.stdout and old.returncode == 2,
         [(done.returncode, done.stdout[:200]) for done in (good, bad, old)])


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("board-options-") as work:
        return replay(work)


def replay(work):
    global box
    box = replay_probe.Sandbox(work, [replay_probe.agent("a-worker", 1), replay_probe.agent("b-worker", 2)])
    cases = replay_probe.Cases()
    step = cases.step

    def written(name, text):
        return replay_probe.write_text(work, name, text)

    body, rest = written("body.md", replay_probe.BODY), written("rest.md", "More on it.\n")
    first, second = (use("file", "--title", title, "--body", body, "--label", "probe").stdout.strip() for title in ("Seed the board", "Wait for the probe"))
    number, other = (re.search(r"(\d+)$", url).group(1) if url else "" for url in (first, second))
    sha = re.search(r"body sha: (\w+)", use("read", number).stdout).group(1) if number else ""
    calls = [("comment", number, "--reported", "probe findings", "--text", rest),
             ("comment", number, "--blocked", "which probe runs first?", "--asks", "owner", "--option", "the fast one", "--option", "the slow one"),
             ("decide", number, "--decision", "ship the probe today", "--text", rest, "--holders", "a-worker"),
             ("edit", number, "--body", written("new.md", replay_probe.BODY + "2. [check] **The probe works when it runs twice**: `basename PASS` prints `PASS`; on base `FAIL`.\n"),
              "--reason", "add the second run", "--base", sha),
             ("title", number, "--title", "Seed the probe board"), ("label", number, "--label", "second"), ("hold", number, "--holders", "a-worker b-worker"),
             ("depend", number, "--depends", other), ("resolve", other, "--summary", "the probe landed", "--text", rest), ("reopen", other),
             ("read", number, "--as", "worker"), ("read", number, "--body")]
    done = [(call, use(*call)) for call in calls]
    shown = use("read", number).stdout
    full = use("read", number, "--full").stdout
    keys = set()
    for name in box.git("ls-tree", "-r", "--name-only", "refs/teamwork-blackboard").split():
        if name.endswith(".json") and "/comments/" in f"/{name}":
            keys |= set(json.loads(box.git("show", f"refs/teamwork-blackboard:{name}")))
    lines = ["REPORTED: probe findings", "BLOCKED: which probe runs first?", "1. the fast one", "DECIDED: ship the probe today", "DECIDED: add the second run",
             "#" + number + " Seed the probe board", "labels: probe, second", "holders: a-worker b-worker", f"depends: #{other}"]
    step("named-writes", first and second and all(answer.returncode == 0 for _, answer in done) and all(line in shown for line in lines)
         and keys <= set(SCHEMA["properties"]) and "text" in keys and "+2. [check] **The probe works when it runs twice**" in full and "+2. [check]" not in shown,
         [f"{' '.join(map(str, call))}: exit {answer.returncode} {answer.stderr[:200]}" for call, answer in done if answer.returncode]
         + [f"read lacks {line!r}" for line in lines if line not in shown] + [f"stray keys {sorted(keys - set(SCHEMA['properties']))}"]
         + ([] if "+2. [check]" in full and "+2. [check]" not in shown else ["`read --full` and `read` do not differ by the edit's diff"]))

    def refused(name, cases):
        seen = []
        for argv, option in cases:
            before = ref()
            answer = use(*argv)
            if answer.returncode != 2 or option not in answer.stderr.split("usage:")[0] or ref() != before:
                seen.append(f"{' '.join(map(str, argv))}: exit {answer.returncode}, board moved {ref() != before}, wanted {option}: {answer.stderr[:300]}")
        step(name, not seen, "; ".join(seen))

    sha = re.search(r"body sha: (\w+)", use("read", number).stdout).group(1)
    new = written("newer.md", replay_probe.BODY + "3. [check] **The probe works when it runs three times**: `basename PASS` prints `PASS`; on base `FAIL`.\n")
    refused("refused-missing", [(("edit", number, "--body", new, "--reason", "add a run"), "--base"), (("edit", number, "--body", new, "--base", sha), "--reason"),
                                (("edit", number, "--reason", "add a run", "--base", sha), "--body"), (("decide", number), "--decision"),
                                (("resolve", number), "--summary"), (("file", "--body", body), "--title"),
                                (("edit", number, "--body", new, "--reason", "REPORTED: task filed"), "--base"),
                                (("edit", number, "--body", new, "--reason", "add a run", "--base", "0" * 12), "--base")])
    refused("refused-misplaced", [(("decide", number, "--decision", "ship it today now", "--text", written("d.md", "DECIDED: ship it\n")), "--decision"),
                                  (("comment", number, "--reported", "probe findings", "--text", written("b.md", "BLOCKED: which one?\n")), "--blocked"),
                                  (("resolve", number, "--summary", "probe landed", "--text", written("r.md", "REPORTED: probe landed\n")), "--summary"),
                                  (("comment", number, "--blocked", "which one?", "--reported", "probe findings"), "--blocked"),
                                  (("comment", number, "--blocked", "which one?", "--asks", "a-manager", "--option", "a", "--option", "b"), "--asks owner"),
                                  (("comment", number, "--reported", "probe findings", "--option", "a", "--option", "b"), "--blocked"),
                                  (("comment", number, "--blocked", "which one?", "--asks", "owner", "--option", "a"), "--option"),
                                  (("depend", number, "--depends", "the-probe"), "--depends"),
                                  (("comment", number, "--reported", " "), "--reported"),
                                  (("decide", number, "--decision", "ship the probe today\nand tomorrow"), "--decision"),
                                  (("decide", number, "--decision", "ship the probe today", "--live-runs", "many"), "--live-runs"),
                                  (("read", number, "--body", "--full"), "--body"),
                                  (("title", "the-probe", "--title", "Seed it again"), "its number or its url"),
                                  (("edit", number, new, "DECIDED: add a run", "--base", sha), "--body")])
    named_docs(step)
    named_lint(step)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
