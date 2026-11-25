#!/usr/bin/env python3
"""Replay malformed and good text and options through the board's write scripts on a scratch git board, whose holders live in a fake herdr,
printing `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`, and exiting 1 on any failure. A refusing case passes when every write exits 2,
the message names a fix and the board is unchanged; an `unstored-` case when every write exits 2 saying nothing was written, the board unchanged;
an `accept-` case when every write exits 0 and the board changed. Cases:
- `fence-*`: a `teamwork` or a `decision` fence at a line's start in a filed body, a comment, a decision, a summary or an edited body;
- `option-*`: an `--asks` that names no owner, `--asks owner` with fewer than two `--option`, an option on a `REPORTED:`, a `--live-runs` that is no count;
- `keyword-*`: a `--blocked` or `--reported` line that is empty or holds two lines, a `--text` file that opens with a keyword of the verb or of another verb,
  a bare `--reported` with no `--text` or with one that opens with another keyword;
- `heading-*`: a section heading misspelt or repeated;
- `edit-*`: a new body or `--reason` `use-board.py edit` is given;
- `unstored-*`: a holder's or a decider's name that board-record-schema.json refuses;
- `accept-*`: text and options that must still post, and a bare `--blocked` or `--reported` taking its line from `--text`;
- `stored-decision`: a `decide` with `--one-way`, `--answers`, `--holders` and `--live-runs` keeps a `comments/<k>.json` whose keys the schema all names, and `read` shows each;
- `stored-question`: a `comment --asks owner` with two `--option` keeps them as `options`, and `read` numbers them and says the task waits on the owner;
- `url-names-task`: `read` and `comment` take the url `file` printed as they take the number.

usage: replay-input-form.py [--only <case>,...]"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
LIB = HERE.parents[2] / "lib"
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(LIB))
import replay_probe  # noqa: E402

BASE = "A summary.\n\n## Goal\n\nDo it.\n\nPath: caller: the probe run; meets: the owner\n\n## Definition of done\n\n1. [check] **The probe works when it runs once**: `basename PASS` prints `PASS`; on base `FAIL`.\n"
TEAMWORK = "\n```teamwork\nholders: a-worker\n```\n"
DECISION = "\n```decision\ndecision: ship it\ndecided by: a-worker\ndoor: two-way\n```\n"
BY = ("--by", "a-manager")
TWO = ("--option", "the first", "--option", "the second")
SCHEMA = json.loads((HERE.parent / "assets" / "board-record-schema.json").read_text())

# name -> (writes, fix): each write is (verb, text, option...) with verb file, comment, decide or resolve, the text's first line, minus its keyword, going to the verb's line option;
# (verb, None, word...) with verb hold or depend; ("call", verb, text or None, option...) with the options handed as they are, text going to `--text`;
# or ("edit", before, after, reason); the message of a refusal holds FIX
REFUSED = {
    "fence-teamwork": ([("file", BASE + TEAMWORK), ("comment", "REPORTED: probe findings\n" + TEAMWORK), ("comment", "BLOCKED: which one?\n\n```teamwork\nasks: owner\n```\n"),
                        ("decide", "DECIDED: ship the probe today\n" + TEAMWORK, *BY), ("resolve", "REPORTED: probe landed\n" + TEAMWORK),
                        ("edit", BASE, BASE + TEAMWORK, "add a holder")], "`teamwork` fence"),
    "fence-decision": ([("file", BASE + DECISION), ("comment", "REPORTED: probe findings\n" + DECISION), ("decide", "DECIDED: ship it\n" + DECISION, *BY),
                        ("resolve", "REPORTED: probe landed\n" + DECISION), ("edit", BASE, BASE + DECISION, "add a decision")], "`decision` fence"),
    "option-asks-value": ([("comment", "BLOCKED: which one?\n", "--asks", "someone", *TWO)], "--asks owner"),
    "option-asks-no-option": ([("comment", "BLOCKED: which one?\n", "--asks", "owner")], "two answers"),
    "option-asks-one-option": ([("comment", "BLOCKED: which one?\n", "--asks", "owner", "--option", "the first")], "two answers"),
    "option-on-report": ([("comment", "REPORTED: probe findings\n", "--asks", "owner", *TWO), ("comment", "REPORTED: probe findings\n", *TWO)], "--blocked"),
    "option-live-runs-word": ([("decide", "DECIDED: cap the live runs\n", *BY, "--live-runs", "many")], "--live-runs 12"),
    "keyword-lowercase": ([("call", "comment", None, "--blocked", "")], "not empty"),
    "keyword-bare": ([("call", "comment", None, "--blocked", "which one?\nand which other?")], "one line"),
    "keyword-bold": ([("call", "comment", None, "--reported", "  ")], "not empty"),
    "keyword-later-line": ([("call", "comment", "BLOCKED: which one?\n", "--blocked", "which one?")], "keyword line"),
    "keyword-bare-no-text": ([("call", "comment", None, "--reported")], "not empty"),
    "keyword-bare-other": ([("call", "comment", "BLOCKED: which one?\n", "--reported")], "keyword line"),
    "keyword-other-verb": ([("call", "comment", "DECIDED: ship the probe today\n", "--reported", "probe findings"), ("call", "decide", "BLOCKED: which one?\n", "--decision", "ship it", *BY),
                            ("call", "resolve", "DECIDED: closing it\n", "--summary", "closing it")], "keyword line"),
    "heading-misspelt": ([("file", BASE.replace("## Goal", "## goal")), ("file", BASE.replace("## Definition of done", "## Definition Of Done"))], "write exactly"),
    "heading-level": ([("file", BASE.replace("## Goal", "### Goal"))], "## Goal"),
    "heading-repeated": ([("file", BASE + "\n## Definition of done\n\n1. [check] **The probe works again when it runs twice**: `basename PASS` prints `PASS`; on base `FAIL`.\n")], "keep one"),
    "edit-keyword-lowercase": ([("edit", BASE, BASE + "\nMore.\n", "DECIDED: lower")], "no keyword"),
    "edit-keyword-empty": ([("edit", BASE, BASE + "\nMore.\n", "")], "not one line"),
    "edit-keyword-free": ([("edit", BASE, BASE + "\nMore.\n", "REPORTED: add more text")], "no keyword"),
    "edit-keyword-two-lines": ([("edit", BASE, BASE + "\nMore.\n", "add more\nholders: oops")], "not one line"),
}
UNSTORED = {
    "unstored-holders-capital": [("hold", None, "A-Worker"), ("decide", "DECIDED: ship the probe today\n", *BY, "--holders", "A-Worker")],
    "unstored-holders-comma": [("decide", "DECIDED: ship the probe today\n", *BY, "--holders", "a-worker, b-worker")],
    "unstored-by-spaces": [("decide", "DECIDED: ship the probe today\n", "--by", "A Manager")],
}
ACCEPTED = {
    "accept-clean-comment": [("comment", "REPORTED: probe findings\n"), ("comment", "BLOCKED: which one?\n"), ("comment", "BLOCKED: which one?\n", *TWO)],
    "accept-other-fence": [("comment", "REPORTED: probe findings\n\n```yaml\nholders: a-worker\n```\n\nThe `teamwork` fence is gone.\n"), ("file", BASE + "\n```text\ndecision: none\n```\n")],
    "accept-clean-edit": [("edit", BASE, BASE + "\nMore.\n", "add more")],
    "accept-fixing-edit": [("edit", BASE + TEAMWORK, BASE, "drop the fence"), ("edit", BASE + TEAMWORK, BASE + TEAMWORK + "\nMore.\n", "add more beside the fence")],
    "accept-every-option": [("file", BASE), ("file", BASE, "--label", "a-label", "--scope", "", "--depends", "1"), ("comment", "BLOCKED: which one?\n", "--asks", "owner", *TWO),
                            ("decide", "DECIDED: ship the probe today\n", *BY, "--one-way", "--holders", "a-worker b-worker", "--live-runs", "2"),
                            ("decide", 'DECIDED: ship the probe today\n\nThe owner said "ship it".\n', "--by", "owner"),
                            ("hold", None, "a-worker", "b-worker"), ("hold", None), ("depend", None, "1"), ("depend", None, "#1")],
    "accept-keyword-spaced": [("call", "comment", "\n more probe findings\n", "--reported", "probe findings"), ("call", "decide", "\n more on it\n", "--decision", "ship the probe today", *BY),
                              ("call", "resolve", "\n more on it\n", "--summary", "done")],
    "accept-bare-line": [("call", "comment", "probe findings\n\nMore.\n", "--reported"), ("call", "comment", "BLOCKED: which one?\n", "--blocked")],
    "accept-keyword-put-first": [("decide", "ship the probe today\n", *BY), ("resolve", "the probe landed\n")],
}
REF = "refs/teamwork-blackboard"


def main(args):
    only = args[1].split(",") if args[:1] == ["--only"] and len(args) == 2 else None
    if args and only is None:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("input-form-") as work:
        return replay(replay_probe.Sandbox(work, [replay_probe.agent("a-worker", 2), replay_probe.agent("b-worker", 3)]), only)


def replay(sandbox, only):
    work, cases = sandbox.work, replay_probe.Cases()
    counter = iter(range(10 ** 6))

    def snapshot():
        """The board's commit, which every write moves."""
        return sandbox.run(["git", "rev-parse", "-q", "--verify", REF]).stdout

    def prepare(spec):
        """The task SPEC writes to, its number, None for a `file`; a body the guard refuses, as an older version wrote it, filed straight on the board."""
        if spec[0] == "file":
            return None
        text = spec[1] if spec[0] == "edit" else BASE
        if text == BASE:
            return int(use("file", "--title", "A task", "--body", written(BASE)).stdout.strip().rsplit("/", 1)[1])
        return sandbox.evaluate(f"import board_git; print(board_git.file('A task', {text!r}, []))")

    def written(text):
        path = work / f"text-{next(counter)}.md"
        path.write_text(text)
        return path

    def use(*argv):
        return sandbox.python(SCRIPTS / "use-board.py", *map(str, argv))

    def keyed(verb, number, text, *options):
        """Posts TEXT as VERB: its first line, minus a keyword, to the verb's line option and the rest to `--text`."""
        word, line, rest = re.match(r"\s*(?:(BLOCKED|REPORTED|DECIDED):)?[ \t]*([^\n]*)\n?(.*)", text, re.S).groups()
        flag = {"comment": "--blocked" if word == "BLOCKED" else "--reported", "decide": "--decision", "resolve": "--summary"}[verb]
        rest = rest.lstrip("\n")
        return use(verb, number, flag, line, *(["--text", written(rest)] if rest.strip() else []), *options)

    def write(spec, number):
        """Runs one write SPEC on the board; the completed process."""
        verb, *rest = spec
        if verb == "edit":
            _, after, line = rest
            sha = re.search(r"^body sha: (\S+)$", use("read", number).stdout, re.M).group(1)
            return use("edit", number, "--body", written(after), "--reason", line, "--base", sha)
        if verb == "call":
            word, text, *options = rest
            return use(word, number, *options, *([] if text is None else ["--text", written(text)]))
        text, *options = rest
        if verb == "file":
            return use("file", "--title", "A task", "--body", written(text), *options)
        if text is None:
            return use(verb, number, "--holders" if verb == "hold" else "--depends", " ".join(options))
        return keyed(verb, number, text, *options)

    def run(name, writes, holds):
        """Runs each of WRITES; HOLDS(done, changed) says whether one went as the case wants."""
        if only and name not in only:
            return
        seen = []
        for spec in writes:
            number = prepare(spec)
            before = snapshot()
            done = write(spec, number)
            changed = snapshot() != before
            seen += [] if holds(done, changed) else [f"{' '.join(map(str, spec[:1] + spec[2:]))}: exit {done.returncode}, board changed {changed}: {done.stdout}{done.stderr}"]
        cases.step(name, not seen, "; ".join(seen))

    def stored(number, position):
        """The record the board keeps as NUMBER's comment at POSITION, as its file holds it."""
        shown = sandbox.run(["git", "show", f"{REF}:{number}/comments/{position:04d}.json"])
        return json.loads(shown.stdout or "{}")

    def stored_decision():
        number = prepare(("comment", None))
        question = keyed("comment", number, "BLOCKED: which one?\n").stdout.strip()
        decided = keyed("decide", number, "DECIDED: ship the probe today\n\nIt is ready.\n", *BY, "--one-way", "--answers", question, "--holders", "a-worker b-worker", "--live-runs", "2")
        url, record, read = decided.stdout.strip(), stored(number, 2), use("read", number).stdout
        wanted = {"text": "DECIDED: ship the probe today\n\nIt is ready.\n", "decision": "ship the probe today", "by": "a-manager", "one_way": True, "answers": question,
                  "holders": ["a-worker", "b-worker"], "live_runs": 2}
        shows = ["state: OPEN, held\n", "holders: a-worker b-worker\n", "binding decisions: 1\n", f"- #{number} a-manager, one-way: ship the probe today ({url}); answers {question}\n", "open questions: 0\n",
                 f"--- {url} (by: a-manager; answers: {question}; one way; holders: a-worker b-worker; live runs: 2)\n"]
        cases.step("stored-decision", decided.returncode == 0 and record == wanted and set(record) <= set(SCHEMA["properties"]) and all(line in read for line in shows),
             f"exit {decided.returncode} {decided.stderr}\n{record}\n{[line for line in shows if line not in read]}\n{read}")

    def stored_question():
        number = prepare(("comment", None))
        asked = keyed("comment", number, "BLOCKED: which one?\n", "--asks", "owner", *TWO)
        url, record, read = asked.stdout.strip(), stored(number, 1), use("read", number).stdout
        shows = ["state: OPEN, waits on the owner\n", "open questions: 1\n", f"- #{number} to the owner: which one? ({url})\n", f"--- {url} (asks: owner)\nBLOCKED: which one?\n\n1. the first\n2. the second\n"]
        cases.step("stored-question", asked.returncode == 0 and record == {"text": "BLOCKED: which one?\n", "asks": "owner", "options": ["the first", "the second"]}
             and set(record) <= set(SCHEMA["properties"]) and all(line in read for line in shows), f"exit {asked.returncode} {asked.stderr}\n{record}\n{[line for line in shows if line not in read]}\n{read}")

    def url_names_task():
        filed = use("file", "--title", "A task", "--body", written(BASE))
        url = filed.stdout.strip()
        number = int(url.rsplit("/", 1)[1])
        posted = keyed("comment", url, "REPORTED: probe findings\n")
        held = use("hold", url, "--holders", "a-worker")
        by_url, by_number = use("read", url), use("read", number)
        cases.step("url-names-task", url.startswith("git+file://") and posted.stdout.strip() == f"{url}#comment-1" and held.stdout.strip() == f"{url}#comment-2"
             and by_url.returncode == 0 and by_url.stdout == by_number.stdout and f"#{number} A task\n" in by_url.stdout and "REPORTED: probe findings" in by_url.stdout
             and "holders: a-worker\n" in by_url.stdout, f"{url}\n{posted.stdout}{posted.stderr}{held.stdout}{held.stderr}{by_url.stdout}{by_url.stderr}")

    for name, (writes, fix) in REFUSED.items():
        run(name, writes, lambda done, changed, fix=fix: done.returncode == 2 and fix.lower() in done.stderr.lower() and not done.stdout and not changed)
    for name, writes in UNSTORED.items():
        run(name, writes, lambda done, changed: done.returncode == 2 and "nothing written" in done.stderr and not done.stdout and not changed)
    for name, writes in ACCEPTED.items():
        run(name, writes, lambda done, changed: done.returncode == 0 and changed)
    for name, case in (("stored-decision", stored_decision), ("stored-question", stored_question), ("url-names-task", url_names_task)):
        if not only or name in only:
            case()
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
