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
judge runs; `judged` for a `[score]`. A timeout is a `fail`. Exit 1 on any `fail`. Each row's `sha-256` is the
first 16 hex digits of the hash of the criterion's kind, name and details, so a judge sees a criterion reworded after
its first judged table. A `BLOCKED due: <name>` line follows
when a criterion fails with the output it had in an earlier table on the task: ask your manager by `BLOCKED:`, since
it has failed twice the same way.

`--base` runs each `[check]` in an export of the base instead, `--ref` or else `origin/HEAD`, and prints `base ok` when
its output equals the text quoted after `on base` (or `on main`, in tasks filed before), `wrong base` when it differs,
`unclear` when the quote is not one value; exit 1 on any `wrong base`; an `exits` or `more` check, a git check (the
export has no `.git`) and a check with a placeholder are `unclear`. The output is compared whole. It never fetches: run `git fetch` first. A body file reads criteria before the task exists, so run it before the first judge.
A body file alone runs its criteria at the head.

A `[check]` whose first pipe stage runs `claude -p` and which says `watches: <path>...` is a live check: its first stage's
output is saved as a transcript, when the session exits 0, under the git common dir's `teamwork-live/`, keyed by that stage and the content of the
watched paths, and the stages after it run on the transcript. A run whose key has a saved transcript starts no session,
so a fix to the later stages, or to a file outside the watched paths, replays; each new session counts toward the cap, the
task's latest `live runs: <n>` or else `LIVE_RUNS`, kept in the worktree's git dir, so a worktree's tasks share one count; a watched path
missing at the head fails the check. At the cap the live check fails
without running and a `BLOCKED due: live runs` line follows.

`--pass <n>=<sample-file>` (once per criterion, with a body file) runs criterion `n` at the head with its first pipe stage
replaced by `cat <sample-file>`, so the stages after it meet the input the pass would give. It prints `pass ok` when the
output equals the text after `prints` (or meets `exits` or `more`), `wrong pass` when it differs, `unclear` for a criterion with no sample or whose first
stage it cannot split surely: before its first pipe, outside quotes, only words, blanks and `. / = : , + @ % ~ < -`
may stand, and the first word is no `if`, `while`, `for` or other compound keyword; inside double quotes no `$(`, `${`, backtick
or backslash; exit 1 on any
`wrong pass`. It finds a check that can never pass, such as `check-schema.py check /dev/stdin`, which reads its input twice."""
import hashlib
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
LIVE_RUNS = 10
UNWATCHED = {".git", "__pycache__", ".DS_Store"}
WRONG_BASE_FIX = """
To fix a `wrong base` row, quote after `on base` the output of running that exact line on the base, never a guess.
Pin what varies or matches too much: `LC_ALL=C` before a sorted list, a stub for a GitHub read the check does not
test, an anchored name that prefixes a sibling's. Read an exit status without a pipe, and put `2>&1` before a pipe
into `grep -c`, since this script merges stderr only after it."""
WRONG_PASS_FIX = """
To fix a `wrong pass` row, run the criterion's command on the sample by hand and make its output meet `prints`,
`exits` or `more`; a check that reads its input twice can never pass on a pipe."""


def git_output(*argv, cwd=None):
    return subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True).stdout.strip()


def read_task(source):
    if source == "-":
        task = json.load(sys.stdin)  # a comment the board adapter has not marked, as a board's own listing prints it, gets its mark here
        return {**task, "comments": [{**comment, "trusted": comment.get("trusted", board.trusted(comment))} for comment in task.get("comments", [])]}
    found = board.fresh(source) if source.lstrip("#").isdigit() else None
    if found is None:
        print(f"run-criteria: could not read {source} as a task on the board, a body file or `-`", file=sys.stderr)
        usage_parser.refuse(__doc__)
    return found


def runnable(task):
    """TASK when its author may write records; else exit, since an untrusted author's `[check]` would run as a command."""
    if not issue_state.trusted(task):
        sys.exit("run-criteria: the task's author is not trusted, so its checks are not run; a trusted author must file the criteria")
    return task


def content_key(first, paths, cwd):
    """A sha-256 of the first stage and every file under PATHS in CWD, so a saved transcript holds only while neither changed."""
    digest = hashlib.sha256(first.encode())
    for path in paths:
        top = pathlib.Path(cwd, path)
        files = [top] if top.is_file() else sorted(file for file in top.rglob("*") if file.is_file() and not UNWATCHED & set(file.parts))
        for file in files:
            digest.update(str(file.relative_to(cwd)).encode() + b"\0" + file.read_bytes())
    return digest.hexdigest()[:16]


class Live:
    """The saved transcripts and the count of live sessions this worktree started, against the task's cap."""

    def __init__(self, root, task):
        cap = issue_state.live_runs(task)
        self.cap = LIVE_RUNS if cap is None else cap
        self.saved = pathlib.Path(git_output("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=root) or tempfile.gettempdir(), "teamwork-live")
        self.counted = pathlib.Path(git_output("rev-parse", "--absolute-git-dir", cwd=root) or tempfile.gettempdir(), "teamwork-live-runs")
        self.replayed = 0
        self.capped = False
        self.strict = True  # a watched path missing at the head is a typo that would pin the key; on the base it may not exist yet

    def used(self):
        return len(self.counted.read_text().split()) if self.counted.exists() else 0

    def run(self, first, rest, paths, cwd, timeout):
        """(status, output) of the stages after FIRST on its transcript, which FIRST makes only when none is saved for its key and the cap allows."""
        missing = [path for path in paths if self.strict and not pathlib.Path(cwd, path).exists()]
        if missing:
            return None, f"watched path not found: {' '.join(missing)}"
        self.saved.mkdir(parents=True, exist_ok=True)
        transcript = self.saved / content_key(first, paths, cwd)
        status = 0
        if transcript.exists():
            self.replayed += 1
        elif self.used() >= self.cap:
            self.capped = True
            return None, f"live-run cap of {self.cap} reached"
        else:
            status, out = run(first, cwd, timeout)
            with self.counted.open("a") as counted:
                counted.write(transcript.name + "\n")
            if status is None:
                return status, out
            transcript.write_text(out)
        result = run(f"cat {shlex.quote(str(transcript))} |{rest}", cwd, timeout)
        if status:  # a failed session (a rate limit, a login) is judged once and never replayed
            transcript.unlink()
        return result

    def report(self):
        """The lines that follow a table, empty when no live check ran."""
        if not (self.replayed or self.used() or self.capped):
            return ""
        line = f"\nlive runs: {self.used()} of {self.cap} started, {self.replayed} replayed from a saved transcript"
        due = f"\nBLOCKED due: live runs reached the cap of {self.cap}; ask your manager by `BLOCKED:` to raise it." if self.capped else ""
        return line + due


def execute(command, detail, cwd, timeout, live):
    """(status, output) of a check, its live first stage replayed from a saved transcript when it has one."""
    stages = criteria_check.live_stage(detail)
    return live.run(*stages, criteria_check.watched(detail), cwd, timeout) if stages else run(command, cwd, timeout)


def base_row(label, kind, name, detail, archive, timeout, live):
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
    status, out = execute(command, detail, archive, timeout, live)
    if "not a git repository" in out:
        return label, name, "unclear", "git needs a checkout, which the export lacks"
    return label, name, "base ok" if status is not None and out == quoted else "wrong base", cell(out)


def pass_row(label, kind, name, detail, sample, cwd, timeout):
    command, test = criteria_check.expectation(detail)
    if kind != "check" or test[0] is None:
        return label, name, "unclear", "not run: not a `[check]` with a decidable pass"
    rest = criteria_check.after_first_pipe(command)
    if sample is None or rest is None:
        return label, name, "unclear", "not run: no sample, or no pipe to put it before"
    status, out = run(f"cat {shlex.quote(sample)} |{rest}", cwd, timeout)
    return label, name, {"pass": "pass ok", "fail": "wrong pass", "unclear": "unclear"}[criteria_check.verdict(test, status, out)], cell(out)


def base_ref(ref):
    found = ref or git_output("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    return found or sys.exit("run-criteria: origin/HEAD is not set; name the base with --ref")


def run_on_base(root, ref, rows, timeout, live):
    """Rows of every criterion run in a `git archive` copy of the base, so the head's files never answer."""
    with tempfile.TemporaryDirectory(prefix="run-criteria-base-") as copy:
        exported = subprocess.Popen(["git", "archive", ref], cwd=root, stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", copy], stdin=exported.stdout, check=True)
        if exported.wait():
            sys.exit(f"run-criteria: could not export {ref}; fetch it first")
        return [base_row(str(n), *criterion, copy, timeout, live) for n, criterion in enumerate(rows, 1)]


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


def cell(text):
    text = " / ".join(line.strip() for line in text.splitlines() if line.strip()).replace("|", "\\|")
    return text if len(text) <= CELL else text[:CELL - 1] + "…"


def row(label, kind, name, detail, cwd, timeout, live):
    if kind == "score":
        return label, name, "judged", "not run: a score is judged"
    if kind != "check":
        return label, name, "unclear", "not run: no kind"
    command, test = criteria_check.expectation(detail)
    if test[0] is None:
        return label, name, "unclear", f"not run: {test[1]}"
    status, out = execute(command, detail, cwd, timeout, live)
    return label, name, criteria_check.verdict(test, status, out), cell(out)


def table_line(cells):
    return "| " + " | ".join([cells[0], cells[1].replace("|", "\\|"), *cells[2:]]) + " |"


def fingerprint(criterion):
    """The first 16 hex digits of the sha-256 of a criterion's kind, name and details, so any rewording changes it."""
    return hashlib.sha256("\0".join(criterion).encode()).hexdigest()[:16]


def criteria(text):
    for line in issue_state.ITEM.findall(text):
        _, kind, name, detail = issue_state.CRITERION.match(line).groups()
        if kind != "task":  # a part is met by its own task's close, never by a command
            yield kind or "", name or detail, detail if name else ""


def task_criteria(task):
    return list(criteria(issue_state.sections(task.get("body")).get("done", "")))


def earlier_fails(task):
    """{name: {output, ...}} of the `fail` rows in earlier tables on the task, by trusted authors only."""
    found = {}
    for comment in task.get("comments", []):
        if issue_state.trusted(comment) and comment["body"].startswith(HEADER):
            for line in comment["body"].splitlines():
                cells = [part.strip() for part in re.split(r"(?<!\\)\|", line)[1:-1]]
                if len(cells) in (4, 5) and cells[2] == "fail":
                    found.setdefault(cells[1], set()).add(cells[3])
    return found


def run_with_samples(options, task, root):
    """The table of the criteria run at the head with a sample for the first stage of each; exit 1 on any `wrong pass`."""
    if options.base:
        sys.exit("run-criteria: --pass and --base cannot run together")
    given = {}
    for sample in options.samples:
        position, _, sample_file = sample.partition("=")
        if not position.isdigit() or not sample_file:
            sys.exit(f"run-criteria: --pass wants <n>=<sample-file>, got {sample}")
        given[int(position)] = os.path.abspath(sample_file)
    found = task_criteria(task)
    if set(given) - set(range(1, len(found) + 1)):
        sys.exit(f"run-criteria: --pass names a criterion the task lacks; it has {len(found)}")
    rows = [pass_row(str(n), *criterion, given.get(n), root, options.timeout) for n, criterion in enumerate(found, 1)]
    print("REPORTED: pass outputs at " + git_output("rev-parse", "HEAD", cwd=root) + "\n\n| # | criterion | result | output on sample |\n| --- | --- | --- | --- |")
    for table_row in rows:
        print(table_line(table_row))
    if any(table_row[2] == "wrong pass" for table_row in rows):
        print(WRONG_PASS_FIX)
        return 1
    return 0


def run_against_base(options, task, root, live):
    """The table of the criteria run in an export of the base; exit 1 on any `wrong base`."""
    live.strict = False
    ref = base_ref(options.ref)
    sha = git_output("rev-parse", "--short", ref, cwd=root)
    rows = run_on_base(root, ref, task_criteria(task), options.timeout, live)
    print(f"REPORTED: base outputs at {ref} {sha}\n\n| # | criterion | result | output on base |\n| --- | --- | --- | --- |")
    for table_row in rows:
        print(table_line(table_row))
    if any(table_row[2] == "wrong base" for table_row in rows):
        print(WRONG_BASE_FIX)
    print(live.report(), end="")
    return 1 if any(table_row[2] == "wrong base" for table_row in rows) else 0


def run_at_head(options, task, root, live):
    """The table of the criteria, then the standing ones, run at the head; exit 1 on any `fail`."""
    standing = pathlib.Path(root, ".teamwork", "default-criteria.md")
    found = [(str(n), criterion) for n, criterion in enumerate(task_criteria(task), 1)]
    found += [("standing", criterion) for criterion in criteria(standing.read_text())] if standing.exists() else []
    rows = [(*row(label, *criterion, root, options.timeout, live), fingerprint(criterion)) for label, criterion in found]
    print(f"{HEADER}{git_output('rev-parse', 'HEAD', cwd=root)}" + (" with uncommitted changes" if git_output("status", "--porcelain", cwd=root) else ""))
    print("\n| # | criterion | result | output | sha-256 |\n| --- | --- | --- | --- | --- |")
    for table_row in rows:
        print(table_line(table_row))
    before = earlier_fails(task)
    for _, name, result, out, _ in rows:
        if result == "fail" and out in before.get(name.replace("|", "\\|"), ()):
            print(f"\nBLOCKED due: {name} failed with the same output as in an earlier table; ask your manager by `BLOCKED:`.")
    print(live.report(), end="")
    return 1 if any(table_row[2] == "fail" for table_row in rows) else 0


def main(args):
    parser = usage_parser.parser(__doc__)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--base", "--main", action="store_true")
    parser.add_argument("--ref")
    parser.add_argument("--pass", dest="samples", action="append", default=[], metavar="N=FILE")
    parser.add_argument("task")
    options = parser.parse_args(args)
    file = pathlib.Path(options.task)
    task = {"body": file.read_text(), "comments": []} if file.is_file() else runnable(read_task(options.task))
    root = git_output("rev-parse", "--show-toplevel") or "."
    if options.samples:
        return run_with_samples(options, task, root)
    if options.base:
        return run_against_base(options, task, root, Live(root, task))
    return run_at_head(options, task, root, Live(root, task))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
