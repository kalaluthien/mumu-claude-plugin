#!/usr/bin/env python3
"""Run each `[check]` of a task's Definition of done at the head, in the worktree's root, then each `[check]` of an
optional `.teamwork/default-criteria.md` there as `standing`, and print a table to comment on the task, which the
judge reads instead of running each check again.

usage: run-criteria.py [--timeout <s>] [--base [--ref <ref>] | --pass <n>=<sample-file>...] <task | body-file | ->

`-` reads the task as JSON, its `body`, `trusted` and `comments`.
A task, by number or JSON, whose author is not `trusted` is refused, exit 1, since its checks would run as commands; a body
file is the worker's own draft, so it runs.

A row is `pass` or `fail` by the output the criterion says it `prints`, or the status it `exits`; `unclear` when the
script cannot decide it, such as a `<placeholder>`, two commands or an expected text found inside other output, which the
judge runs; `judged` for a `[score]`. A timeout is a `fail`. Exit 1 on any `fail`. A `BLOCKED due: <name>` line follows
when a criterion fails with the output it had in an earlier table on the task: ask your manager by `BLOCKED:`, since
it has failed twice the same way.

`--base` runs each `[check]` in an export of the base instead, `--ref` or else `origin/HEAD`, and prints `base ok` when
its output equals the text quoted after `on base` (or `on main`, in tasks filed before), `wrong base` when it differs,
`unclear` when the quote is not one value; exit 1 on any `wrong base`; an `exits` or `more` check, a git check (the
export has no `.git`) and a check with a placeholder are `unclear`. The output is compared whole. It never fetches: run `git fetch` first. A body file reads criteria before the task exists, so run it before the first judge.

`--pass <n>=<sample-file>` (once per criterion, with a body file) runs criterion `n` at the head with its first pipe stage
replaced by `cat <sample-file>`, so the stages after it meet the input the pass would give. It prints `pass ok` when the
output equals the text after `prints` (or meets `exits` or `more`), `wrong pass` when it differs, `unclear` for a criterion with no sample or whose first
stage it cannot split surely: before its first pipe, outside quotes, only words, blanks and `. / = : , + @ % ~ < -`
may stand, and the first word is no `if`, `while`, `for` or other compound keyword; inside double quotes no `$(`, `${`, backtick
or backslash; exit 1 on any
`wrong pass`. It finds a check that can never pass, such as `check-schema.py check /dev/stdin`, which reads its input twice."""
import json
import os
import pathlib
import re
import shlex
import signal
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402
import criteria_check  # noqa: E402
import issue_state  # noqa: E402
import usage_parser  # noqa: E402

HEADER = "REPORTED: criteria at "
CELL = 160


def read_task(source):
    if source == "-":
        task = json.load(sys.stdin)  # a comment the board adapter has not marked, as a board's own listing prints it, gets its mark here
        return {**task, "comments": [{**comment, "trusted": comment.get("trusted", board.trusted(comment))} for comment in task.get("comments", [])]}
    found = board.fresh(source)
    if found is None:
        sys.exit(f"run-criteria: could not read task {source} from GitHub")
    return found


def runnable(task):
    """TASK when its author may write records; else exit, since an untrusted author's `[check]` would run as a command."""
    if not issue_state.trusted(task):
        sys.exit("run-criteria: the task's author is not trusted, so its checks are not run; a trusted author must file the criteria")
    return task


def base_row(label, kind, name, detail, archive, timeout):
    command, test = criteria_check.expectation(detail)
    quoted = criteria_check.base_quote(detail)
    if kind != "check":
        return label, name, "unclear", "not run: not a `[check]`"
    if test[0] is None:
        return label, name, "unclear", f"not run: {test[1]}"
    # an `exits` or `more` check is decided by status or count, which the quoted text is not
    if test[0] != "prints":
        return label, name, "unclear", "not run: an `exits` or `more` check has no quoted output"
    if quoted is None:
        return label, name, "unclear", "not run: no one value after `on base`"
    status, out = run(command, archive, timeout)
    if "not a git repository" in out:
        return label, name, "unclear", "git needs a checkout, which the export lacks"
    return label, name, "base ok" if status is not None and out == quoted else "wrong base", cell(out)


# outside quotes only these may precede the first pipe; anything else (`;`, `&`, `{`, `(`, `#`, a backslash, ...) might hide a pipe or a stage
SAFE = re.compile(r"[\w \t./=:,+@%~<-]|\$\w|\$(?=[\"'])")


# a compound command owns the pipe that follows its first word, so the pipe is not a stage boundary
KEYWORDS = {"if", "while", "until", "for", "case", "select", "time", "function", "coproc"}


def after_first_pipe(command):
    """The command without its first pipe stage, split at the first `|` outside quotes, or None when the split is not certain:
    no pipe, or before it a character outside SAFE, or in double quotes a `$(`, `${`, backtick or backslash, which
    could hide a pipe or drop part of the first stage."""
    if command.split(None, 1)[:1] and command.split(None, 1)[0] in KEYWORDS:
        return None
    quote, i = None, 0
    while i < len(command):
        char = command[i]
        if char == "\\":
            return None
        if quote:
            # a substitution inside double quotes can hold quotes of its own, which end this quote early
            if quote == '"' and (char == "`" or command[i:i + 2] in ("$(", "${")):
                return None
            quote = None if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char == "|" and command[i:i + 2] != "||":
            return command[i + 1:]
        elif not (match := SAFE.match(command, i)):
            return None
        else:
            i = match.end() - 1
        i += 1
    return None


def pass_row(label, kind, name, detail, sample, cwd, timeout):
    command, test = criteria_check.expectation(detail)
    if kind != "check" or test[0] is None:
        return label, name, "unclear", "not run: not a `[check]` with a decidable pass"
    rest = after_first_pipe(command)
    if sample is None or rest is None:
        return label, name, "unclear", "not run: no sample, or no pipe to put it before"
    status, out = run(f"cat {shlex.quote(sample)} |{rest}", cwd, timeout)
    return label, name, {"pass": "pass ok", "fail": "wrong pass", "unclear": "unclear"}[verdict(test, status, out)], cell(out)


def base_ref(ref):
    found = ref or subprocess.run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], capture_output=True,
                                  text=True).stdout.strip()
    return found or sys.exit("run-criteria: origin/HEAD is not set; name the base with --ref")


def run_on_base(root, ref, rows, timeout):
    """Rows of every criterion run in a `git archive` copy of the base, so the head's files never answer."""
    with tempfile.TemporaryDirectory(prefix="run-criteria-base-") as copy:
        exported = subprocess.Popen(["git", "archive", ref], cwd=root, stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", copy], stdin=exported.stdout, check=True)
        if exported.wait():
            sys.exit(f"run-criteria: could not export {ref}; fetch it first")
        return [base_row(str(n), *criterion, copy, timeout) for n, criterion in enumerate(rows, 1)]


def run(command, cwd, timeout):
    """(exit status or None on a timeout, stdout and stderr as one text)."""
    process = subprocess.Popen(["bash", "-c", command], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         start_new_session=True)
    try:
        out, _ = process.communicate(timeout=timeout)
        return process.returncode, out.strip()
    except subprocess.TimeoutExpired:
        # the check's children share its session, so killing only bash would leave them running
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        return None, f"timed out after {timeout} s"


def verdict(test, status, out):
    kind, want = test
    if status is None:
        return "fail"
    if kind == "exits":
        return "pass" if status == want else "fail"
    if kind == "more":
        first = out.split(maxsplit=1)[:1]
        return "pass" if first and first[0].isdigit() and int(first[0]) >= want else "fail"
    if out == want:
        return "pass"
    # the text among other lines may sit beside a failure, so the judge reads it
    return "unclear" if want and re.search(rf"(?<!\w){re.escape(want)}(?!\w)", out) else "fail"


def cell(text):
    text = " / ".join(line.strip() for line in text.splitlines() if line.strip()).replace("|", "\\|")
    return text if len(text) <= CELL else text[:CELL - 1] + "…"


def row(label, kind, name, detail, cwd, timeout):
    if kind == "score":
        return label, name, "judged", "not run: a score is judged"
    if kind != "check":
        return label, name, "unclear", "not run: no kind"
    command, test = criteria_check.expectation(detail)
    if test[0] is None:
        return label, name, "unclear", f"not run: {test[1]}"
    status, out = run(command, cwd, timeout)
    return label, name, verdict(test, status, out), cell(out)


def criteria(text):
    for line in issue_state.ITEM.findall(text):
        _, kind, name, detail = issue_state.CRITERION.match(line).groups()
        yield kind or "", name or detail, detail if name else ""


def earlier_fails(task):
    """{name: {output, ...}} of the `fail` rows in earlier tables on the task, by trusted authors only."""
    found = {}
    for comment in task.get("comments", []):
        if issue_state.trusted(comment) and comment["body"].startswith(HEADER):
            for line in comment["body"].splitlines():
                cells = [part.strip() for part in re.split(r"(?<!\\)\|", line)[1:-1]]
                if len(cells) == 4 and cells[2] == "fail":
                    found.setdefault(cells[1], set()).add(cells[3])
    return found


def main(args):
    parser = usage_parser.parser(__doc__)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--base", "--main", action="store_true")
    parser.add_argument("--ref")
    parser.add_argument("--pass", dest="samples", action="append", default=[], metavar="N=FILE")
    parser.add_argument("task")
    options = parser.parse_args(args)
    file = pathlib.Path(options.task)
    task = {"body": file.read_text(), "comments": []} if (options.base or options.samples) and file.is_file() else runnable(read_task(options.task))
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or "."
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True).stdout.strip()
    if options.samples:
        if options.base:
            sys.exit("run-criteria: --pass and --base cannot run together")
        given = {}
        for sample in options.samples:
            position, _, sample_file = sample.partition("=")
            if not position.isdigit() or not sample_file:
                sys.exit(f"run-criteria: --pass wants <n>=<sample-file>, got {sample}")
            given[int(position)] = os.path.abspath(sample_file)
        found = list(criteria(issue_state.sections(task.get("body")).get("done", "")))
        if set(given) - set(range(1, len(found) + 1)):
            sys.exit(f"run-criteria: --pass names a criterion the task lacks; it has {len(found)}")
        rows = [pass_row(str(n), *criterion, given.get(n), root, options.timeout) for n, criterion in enumerate(found, 1)]
        print("REPORTED: pass outputs at " + head + "\n\n| # | criterion | result | output on sample |\n| --- | --- | --- | --- |")
        for table_row in rows:
            print("| " + " | ".join([table_row[0], table_row[1].replace("|", "\\|"), table_row[2], table_row[3]]) + " |")
        return 1 if any(table_row[2] == "wrong pass" for table_row in rows) else 0
    if options.base:
        ref = base_ref(options.ref)
        sha = subprocess.run(["git", "rev-parse", "--short", ref], cwd=root, capture_output=True, text=True).stdout.strip()
        rows = run_on_base(root, ref, list(criteria(issue_state.sections(task.get("body")).get("done", ""))), options.timeout)
        print(f"REPORTED: base outputs at {ref} {sha}\n\n| # | criterion | result | output on base |\n| --- | --- | --- | --- |")
        for table_row in rows:
            print("| " + " | ".join([table_row[0], table_row[1].replace("|", "\\|"), table_row[2], table_row[3]]) + " |")
        return 1 if any(table_row[2] == "wrong base" for table_row in rows) else 0
    standing = pathlib.Path(root, ".teamwork", "default-criteria.md")
    rows = [row(str(n), *criterion, root, options.timeout) for n, criterion in enumerate(criteria(issue_state.sections(task.get("body")).get("done", "")), 1)]
    rows += [row("standing", *criterion, root, options.timeout) for criterion in criteria(standing.read_text())] if standing.exists() else []
    print(f"{HEADER}{head}" + (" with uncommitted changes" if dirty else ""))
    print("\n| # | criterion | result | output |\n| --- | --- | --- | --- |")
    for table_row in rows:
        print("| " + " | ".join([table_row[0], table_row[1].replace("|", "\\|"), table_row[2], table_row[3]]) + " |")
    before = earlier_fails(task)
    for _, name, result, out in rows:
        if result == "fail" and out in before.get(name.replace("|", "\\|"), ()):
            print(f"\nBLOCKED due: {name} failed with the same output as in an earlier table; ask your manager by `BLOCKED:`.")
    return 1 if any(table_row[2] == "fail" for table_row in rows) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
