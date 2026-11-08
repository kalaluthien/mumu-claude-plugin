#!/usr/bin/env python3
"""Print each criterion of a task body's Definition of done whose form a judge would send back, or run-criteria.py cannot read, one line per criterion,
`<position>: <defects>`, and exit 1; a body with none prints nothing and exits 0.

usage: check-criteria.py [--task <n>] <body-file | ->
usage: check-criteria.py --cut-off

It reads the form only, never running a command, since whether a check passes on the base stays the judge's to find.
After the lines it prints, once per defect named, what the defect means and how to fix it.

A task numbered at or above `CUT_OFF`, or one given with no `--task`, must also hold at most 5 criteria, `[task]` parts
not counted, each `[check]` a scenario that prints `PASS`, on base `FAIL`, and none only a text scan, such as a grep, an
`awk` or inline code that reads a file and runs nothing, and a check that starts a live session (`claude -p`) must run it as its
first pipe stage and say `watches: <path>...`, so run-criteria.py can replay its transcript. A task below it keeps the rules it was filed under.
`--cut-off` prints `CUT_OFF`.

A task numbered at or above `GOAL_CUT_OFF`, or one given with no `--task`, whose body holds a `## Goal` must also have in it a `Path:` line
naming the flow of the changed part, as protocol.md's **Scope the path** defines it; the lint prints it as `goal: <defects>`. A body with no Goal, such as a root, is not checked."""
import pathlib
import re
import shlex
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import criteria_check  # noqa: E402
import issue_state  # noqa: E402

NEXT_WORD = r"[^A-Za-z0-9-]+([A-Za-z0-9-]+)"  # the word after a marker such as `prints`
# the first task number filed after the commit that wrote this line, so every task filed before keeps its old rules
CUT_OFF = 1195
# the number of the task that added the Goal path check, so every Goal written before it keeps its old rules
GOAL_CUT_OFF = 1305
MOST = 5
PATH_LINE = re.compile(r"^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?Path(?:\*\*)?:(?:\*\*)?[ \t]*(.*)$", re.M | re.I)
# the blanks of the form FIX prints, which a writer who copies it unfilled has not answered
BLANK = re.compile(r"<(?:caller|step before|step after|who sees the result)>")
# the relations Scope the path names between a changed part and its flow, each written `label: who or what`
RELATION = re.compile(r"^\s*(?:caller|before|after|meets)\s*:\s*(\S.*?)\s*$", re.I)
# a value that opens by saying there is no such party, not a party, unless a party follows `but` or `except`
NOBODY = re.compile(r"^(?:none|no one|nobody|nothing|no\s|n/a|unknown|tbd|-)(?!.*\b(?:but|except)\b)", re.I)
# programs that only read or reshape text, so a check made of them alone never runs the system it judges
SCANS = {"grep", "egrep", "fgrep", "rg", "ag", "awk", "gawk", "sed", "cat", "head", "tail", "wc", "sort", "uniq",
         "cut", "tr", "test", "[", "diff", "cmp", "jq", "echo", "printf", "true", "false"}
INLINE = {"python": "-c", "python3": "-c", "node": "-e", "perl": "-e", "ruby": "-e"}
SHELLS = {"sh", "bash", "zsh"}
# inline code that starts a process runs the system; any other inline code only reads
RUNS = re.compile(r"\b(?:subprocess|os\.system|os\.popen|os\.exec\w*|child_process|system\s*\()")
# wrappers that run the command after them, so the command decides
WRAPPERS = {"env", "command", "exec", "nice", "nohup", "time", "timeout", "xargs"}


FIX = {
    "no kind": "open the criterion with `[check]` or `[score]` before its name",
    "no name": "put a bold name after the kind: `[check] **<name>**: <details>`",
    "no command": "write the command that decides in a code span; a `[check]` is a command whose output decides",
    "no base output": "quote, after `on base`, the failing output of the same command on the base, as in "
                      "`prints ok; on base nothing`",
    "passes on base": "the word after `prints` equals the word after `on base`, so the check passes on the base; "
                      "quote the output it gives there, which must differ",
    "words before the command": "start the details with the command in a code span; move any note after the expected output",
    "two commands": "keep one command in a code span before `prints`; a second code span there makes it ambiguous",
    "no prints or exits": "say `prints <output>` or `exits <status>` after the command",
    "placeholder in the command": "write the command as run, with no `<word>` in it",
    "more than one condition": "split a second condition into its own criterion",
    "expected status not one value": "write one status number after `exits`",
    "expected output not one value": "write one value after `prints`, in a code span or one word",
    "no one value after `on base`": "quote one value after `on base`, in a code span or one word",
    "elided command": "write the whole command; `...` or `…` in the code span cannot be run",
    "no sample": "name the sample with `sample:`",
    "no rubric": "name the rubric with `rubric:`",
    "no base measure": "state the base's measure on the sample, with the word `base`",
    "more than 5 criteria": "keep one criterion per outcome, at most 5; group clauses that one outcome covers",
    "not a scenario": "make the check a scenario that runs the system and prints `PASS`, and quote `FAIL` on base",
    "live stage not replayable": "make the first pipe stage the only `claude -p` run, with no redirect, subshell or `&&` before the pipe, "
                                 "and name the paths it runs against: `watches: <path>...`; the stages after it judge its saved transcript",
    "no path in the Goal": "add to the Goal one line, `Path: caller: <caller>; before: <step before>; after: <step after>; meets: <who sees the result>`, "
                           "naming the flow of the changed part, as protocol.md's **Scope the path** says: its callers, the steps before and after it, "
                           "and whoever meets its result, all on that one line; a Goal that names only the changed part misses what breaks when it changes",
    "path names no flow": "as protocol.md's **Scope the path** says, write the `Path:` line as `label: name` items split by `;`, the only form that counts: at least one of "
                          "`caller:`, `before:`, `after:` or `meets:` followed by the party it names, never `none`, empty, or a `<...>` blank of the form left in the line; "
                          "a line that names only the changed part, or says nothing is affected, gives no flow",
    "text scan": "run the system and judge its behaviour; a grep, `awk` or file read alone checks words, not what works",
}


def stages(command):
    """The words of each simple command in a shell line, split at `|`, `&&`, `||`, `;` and newlines."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    stage = []
    try:
        for token in lexer:
            if token and set(token) <= set("|&;()\n"):
                if stage:
                    yield stage
                stage = []
            else:
                stage.append(token)
    except ValueError:
        stage = command.split()
    if stage:
        yield stage


def scans_only(command):
    """True when every simple command in COMMAND only reads text, so the check runs nothing of the system."""
    for words in stages(command):
        while words and (re.fullmatch(r"\w+=.*|-\w.*|\d+[smhd]?", words[0]) or pathlib.PurePath(words[0]).name in WRAPPERS):
            words = words[1:]
        if not words:
            continue
        program = pathlib.PurePath(words[0]).name
        if program in SHELLS and "-c" in words[1:-1]:
            if not scans_only(words[words.index("-c") + 1]):
                return False
        elif program in INLINE and INLINE[program] in words[1:-1]:
            if RUNS.search(words[words.index(INLINE[program]) + 1]):
                return False
        elif program not in SCANS:
            return False
    return True


def scenario_defects(kind, detail):
    """The defects a task at or above the cut-off adds: a `[check]` that is no PASS/FAIL scenario, or only a text scan."""
    if kind != "check":
        return []
    command, test = criteria_check.expectation(detail)
    if command is None:
        return []
    found = [] if test == ("prints", "PASS") and criteria_check.base_quote(detail) == "FAIL" else ["not a scenario"]
    return found + (["text scan"] if scans_only(command) else [])


def live_defects(kind, detail):
    """A `[check]` that starts a session anywhere but a first stage that run-criteria.py can save and replay, which would start a session on each run."""
    command, _ = criteria_check.expectation(detail)
    return ["live stage not replayable"] if kind == "check" and command and criteria_check.starts_session(command) and not criteria_check.live_stage(detail) else []


def goal_defects(goal):
    """The defects of a Goal's `Path:` line: absent, or present and naming no flow of the changed part."""
    lines = [text.strip() for text in PATH_LINE.findall(goal)]
    if not any(lines):
        return ["no path in the Goal"]
    items = [RELATION.match(item) for text in lines for item in text.split(";")]
    named = [item.group(1) for item in items if item]
    return [] if named and not any(BLANK.search(text) for text in lines) and any(not NOBODY.match(value) for value in named) else ["path names no flow"]


def defects(kind, name, detail):
    """The defects of one criterion, in the order the task lists them."""
    found = [] if kind in ("check", "score") else ["no kind"]
    found += [] if name else ["no name"]
    span = issue_state.SPAN.search(detail)
    rest = detail[:span.start()] + detail[span.end():] if span else detail
    if kind == "check":
        # tasks filed before the base was named quote `on main`
        passes, base = re.search(r"\bprints" + NEXT_WORD, rest), re.search(r"\bon (?:base|main)" + NEXT_WORD, rest)
        found += [] if span else ["no command"]
        found += ["no base output"] if not base else ["passes on base"] if passes and passes.group(1) == base.group(1) else []
    # what run-criteria.py cannot read; lint already names an elided command, and a missing base output covers the quote
    why = criteria_check.unreadable(detail) if kind == "check" and span else None
    elided = bool(span) and ("..." in span.group(2) or "…" in span.group(2))
    covered = why in found or elided and why == "placeholder in the command" or "no base output" in found and why and why.endswith("`on base`")
    found += [why] if why and not covered else []
    if elided:
        found.append("elided command")
    if kind == "score":
        found += [f"no {word}" for word in ("sample", "rubric") if f"{word}:" not in rest]
        found += [] if re.search(r"\b(?:base|main)\b", rest) else ["no base measure"]
    return found


def main(args):
    if args == ["--cut-off"]:
        print(CUT_OFF)
        return 0
    task = None
    if len(args) == 3 and args[0] == "--task" and args[1].isdigit():
        task, args = int(args[1]), args[2:]
    if len(args) != 1 or args[0].startswith("-") and args[0] != "-":
        print(__doc__, file=sys.stderr)
        return 2
    source = args[0]
    body = sys.stdin.read() if source == "-" else pathlib.Path(source).read_text()
    lines = issue_state.ITEM.findall(issue_state.sections(body).get("done", ""))
    new_rules = task is None or task >= CUT_OFF
    goal = issue_state.sections(body).get("goal")
    goal_found = goal_defects(goal) if goal is not None and (task is None or task >= GOAL_CUT_OFF) else []
    # a part, `[task] #n`, is no criterion, so its form is the graph's to check
    matched = [(line_number, issue_state.CRITERION.match(line).groups()[1:]) for line_number, line in enumerate(lines, 1)]
    criteria = [(line_number, groups) for line_number, groups in matched if groups[0] != "task"]
    flagged = [(line_number, found) for line_number, groups in criteria
               for found in [defects(*groups) + (scenario_defects(groups[0], groups[2]) + live_defects(groups[0], groups[2]) if new_rules else [])] if found]
    if new_rules and len(criteria) > MOST:
        flagged.insert(0, ("body", ["more than 5 criteria"]))
    flagged = ([("goal", goal_found)] if goal_found else []) + flagged
    for position, found in flagged:
        print(f"{position}: {', '.join(found)}")
    for name in dict.fromkeys(defect for _, found in flagged for defect in found):
        print(f"- {name}: {FIX[name]}")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
