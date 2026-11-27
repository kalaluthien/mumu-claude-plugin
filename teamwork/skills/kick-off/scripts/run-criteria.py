#!/usr/bin/env python3
"""Run each `[check]` of a task's Definition of done at the head, in the worktree's root, then each `[check]` of an
optional `.teamwork/default-criteria.md` there as `standing`, and print a table to comment on the task, which the
judge reads instead of running each check again.

usage: run-criteria.py [--timeout <s>] [--run-timeout <s>] [--fresh] [--base [--ref <ref>] | --hunks [--each] [--jobs <n>] [--ref <ref>] [--since <sha>] | --since <sha> | --pass <n>=<sample-file>...] [--repository <folder>] <task | body-file | ->

`--repository` names the checkout, main or worktree, whose root the checks run in and whose board the task is read from, with no `cd`; a body-file path is read from that folder. A task is its number, `#n` or url; `-` reads the task as JSON, its `body`, `trusted` and `comments`. A word that names no file and no task
on the board prints one line saying which, exit 1. `--timeout` is each check's limit, 900 s unless given; a check past it is killed with every process it started. It bounds each git, tar
or ps call too: one past it is killed the same way, and the run exits 1 naming it. `--run-timeout` is the whole run's limit, 7200 s unless
given: the check or call running at it is killed the same way, and the run exits 1 naming that limit.
A task, by number or JSON, whose author is not `trusted` is refused, exit 1, since its checks would run as commands; a body
file is the worker's own draft, so it runs.

A row is `pass` or `fail` by the output the criterion says it `prints`, or the status it `exits`; `unclear` when the
script cannot decide it, such as a `<placeholder>`, two commands or an expected text found inside other output, which the
judge runs; `judged` for a `[score]`. A timeout is a `fail`. Exit 1 on any `fail`. Each row's `sha-256` is the
first 16 hex digits of the hash of the criterion's kind, name and details, so a judge sees a criterion reworded after
its first judged table. A `[check]` that passed on the same files, not counting ignored ones, and the same commit, branch and index (or with `--base` the base's files), and on the same files outside the repository that it names by an absolute or `~/` path (it always runs when it names such a folder), is not run again by any session of the
repository: its row is its earlier output, and `cached: <n> checks replayed` follows the table. `--fresh` runs every check again; a failed check always runs. A `BLOCKED due: <name>` line follows
when a criterion fails with the output it had in an earlier table on the task: ask your manager by `BLOCKED:`, since
it has failed twice the same way.

`--base` runs each `[check]` in an export of the base instead, `--ref` or else the first of `origin/HEAD`, `origin/main` and `main` that exists, and prints `base ok` when
its output equals the text quoted after `on base` (or `on main`, in tasks filed before), `wrong base` when it differs,
`text scan` when the quote matches only because a grep, `awk`, `sed` or another file read alone fails it, the rest of the command printing the passing output on base (a scan that reads a pipe, even one a scan feeds, or a file the check wrote is kept, so it is not named), `unclear` when the quote is not one value; a check whose every output line says a file is missing that the export lacks, such as a fixture the change adds, reads as `FAIL` when `FAIL` is quoted; exit 1 on any `wrong base` or `text scan`; an `exits` or `more` check, a git check (the
export has no `.git`) and a check with a placeholder are `unclear`. The output is compared whole. It never fetches: run `git fetch` first. A body file reads criteria before the task exists, so run it before the first judge.
A body file alone runs its criteria at the head.

A `[check]` whose first pipe stage runs `claude -p` and which says `watches: <path>...` is a live check: its first stage's
output is saved as a transcript, when the session exits 0, under the git common dir's `teamwork-live/`, keyed by that stage and the content of the
watched paths, and the stages after it run on the transcript. A run whose key has a saved transcript starts no session,
so a fix to the later stages, or to a file outside the watched paths, replays; each new session counts toward the cap, the
task's latest `decide --live-runs <n>` or else `LIVE_RUNS` (4), kept in the worktree's git dir, so a worktree's tasks share one count; a watched path
missing at the head fails the check. At the cap the live check fails
without running and a `BLOCKED due: live runs` line follows.

A check run in an export of `--base` or `--hunks` has every process still running a file of that export killed when it ends, since a monitor it starts in a session of its own would poll for ever.
`--hunks` holds beside the `[check]`s each fixture runner the change adds or edits, a `replay-*.py` or `replay-*.ts` directly in a `fixtures/` folder, run to exit 0,
so a task of `[score]`s alone is swept too; a runner that fails at the head is not held.
`--hunks` first runs the `[check]`s at the head and, when one fails there and in the checkout, prints `<n>: fails at the head` for it and judges no hunk, exit 1; it then reverts each hunk of the change from the base (`--ref`, else as `--base`) to the head alone in an export of the head,
runs the `[check]`s there, prints to stderr one progress line per reverted group and per mutant below, its count and the seconds since the run began, and prints `<file>:<line>: unneeded hunk` for each hunk whose revert turns no row that passes at the
head into another result: a hunk whose revert fails no criterion is unneeded, or its criterion is vacuous. Exit 1 on any such
hunk; a check that fails in the export but passes in the checkout, such as a git check, which the export cannot run, never counts:
`<n>: not swept` is printed for it. A file of more than 4 hunks is reverted whole, then by
halves, and a half whose revert fails a criterion is not judged hunk by hunk: `<file>: <n> hunks not judged one by one` is
printed, and `--each` reverts each hunk alone as every file of 4 hunks or fewer is. A hunk no check can
see, such as a `version` bump, a usage line, a docstring or a document, is always named: the judge reads it as needed. In a hunk
that is needed, the test of each `if` or `elif` statement it adds to a Python file is then made `False` alone, and `<file>:<line>: unneeded condition` is printed
for each whose branch no criterion reaches; each other comparison it adds is then negated alone, each number made 0, or 1 when it is 0, each codec
name given to `decode`, `encode` or `encoding=` made `latin-1`, or `utf-8` when it is that, and each element of a list or tuple and each operand of `and` or `or` dropped, each path call swapped for its sibling (`resolve` and `absolute` for each other, `realpath` for `abspath`,
`abspath` and `normpath` for each other, `is_dir` or `is_file` for `exists`, `exists` for `is_dir`) each `<side> == <text>` widened to `<text> in <side>` and each `sorted(<items>, ...)` made `list(<items>)`; once per Python file it sweeps, the file is
made to raise at its first line, which a criterion that only finds two runs equal lets survive, so make a criterion read what a run prints; and
`<file>:<line>: surviving mutant` is printed for each that fails no criterion; exit 1 on either, since a refusal, a bound, a weight, an argument or a codec no check
reaches hides inside a hunk a check needs, and a judge would find each in a round of its own; a file under a `fixtures/` folder
gets no mutant, since it is the check, not the change. It runs
the checks once per reverted group and per such mutant, stopping at the first that fails, the checks that failed most so far first,
in parallel, each job in its own export of the head, as many as `--jobs`, a count of 1 or more, or else the CPU count, and a live check starts one session at a time; give a long check time with `--timeout`; it never fetches.
A revert's or mutant's result is kept in the git common dir's `teamwork-sweeps/` and replayed, by any session, while the head's files, that file's text, the
passing criteria, the timeout and the files outside the repository they name are the same, unless a check timed out, met the live-run cap or a missing watched path, or started a live session: `cached: <n> reverts and
mutants replayed` follows, and `--fresh` sweeps them again.
With `--since <sha>`, the head of the last sweep, it reverts and mutates only the hunks a line of which changed between that sha and the head,
and counts the rest as `unchanged since <sha>, not swept`, since the last sweep already judged them; the checks at the head still run first.

`--since <sha>` runs nothing: it reads the hunks between the sha, the head a judge last judged, and the head, and prints for each criterion
`<n>: judge again` with the parts that changed, or `<n>: unchanged since <sha>: keep its verdict`. A criterion names its parts by a
`covers:` clause of backticked parts, each a path, a folder or `<path>#<section>`, a section being a Markdown heading's anchor (the part up to the next
heading as high) or an HTML element's `id` (the element's lines), so one middle section of a document is a part; a criterion with no
`covers:` covers every part and is always judged again. When every criterion names its parts, each changed line no part holds prints
`<file>:<line>: covered by no criterion`, and a section the head lacks prints a line saying so and counts as changed.
A changed file whose name holds a `"`, a tab or a backslash counts as changed whole, each of its sections with it.

`--pass <n>=<sample-file>` (once per criterion, with a body file) runs criterion `n` at the head with its first pipe stage
replaced by `cat <sample-file>`, so the stages after it meet the input the pass would give. It prints `pass ok` when the
output equals the text after `prints` (or meets `exits` or `more`), `wrong pass` when it differs, `unclear` for a criterion with no sample or whose first
stage it cannot split surely: before its first pipe, outside quotes, only words, blanks and `. / = : , + @ % ~ < -`
may stand, and the first word is no `if`, `while`, `for` or other compound keyword; inside double quotes no `$(`, `${`, backtick
or backslash; exit 1 on any
`wrong pass`. It finds a check that can never pass, such as `check-schema.py check /dev/stdin`, which reads its input twice."""
import ast
import codecs
import collections
import concurrent.futures
import hashlib
import html.parser
import json
import os
import pathlib
import queue
import re
import shlex
import signal
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402
import board_refs  # noqa: E402
import criteria_check  # noqa: E402
import data_folder  # noqa: E402
import task_state  # noqa: E402
import usage_parser  # noqa: E402

HEADER = "REPORTED: criteria at "
CELL = 160
LIVE_RUNS = 4
FEW_HUNKS = 4  # a file with more hunks is reverted whole, then by halves
# a path call and the sibling a mutant swaps it for, each pair differing on a link, a relative path or a file that is no folder
SIBLINGS = {"resolve": "absolute", "absolute": "resolve", "realpath": "abspath", "abspath": "normpath", "normpath": "abspath", "is_dir": "exists", "is_file": "exists",
            "exists": "is_dir"}
RUNNER = re.compile(r"(?:^|/)fixtures/replay-[^/]+\.(?:py|ts)$")
UNWATCHED = {".git", "__pycache__", ".DS_Store"}
TEXT_SCAN_FIX = """
To fix a `text scan` row, make a stage that runs the system fail on base: put the grep after a fixture run's pipe, or
drop it, since a rewrite that keeps its words would pass it."""
WRONG_BASE_FIX = """
To fix a `wrong base` row, quote after `on base` the output of running that exact line on the base, never a guess.
Pin what varies or matches too much: `LC_ALL=C` before a sorted list, a stub for a GitHub read the check does not
test, an anchored name that prefixes a sibling's. Read an exit status without a pipe, and put `2>&1` before a pipe
into `grep -c`, since this script merges stderr only after it."""
WRONG_PASS_FIX = """
To fix a `wrong pass` row, run the criterion's command on the sample by hand and make its output meet `prints`,
`exits` or `more`; a check that reads its input twice can never pass on a pipe."""


call_limit = None  # `--timeout`, which main sets before any call
run_limit, started = None, time.monotonic()  # `--run-timeout`, which main sets, and when the run began


def within(limit):
    """LIMIT cut to what is left of the whole run's limit; past that the run exits 1 naming it, since a limit per check never bounds a run of many checks."""
    left = run_limit - (time.monotonic() - started)
    if left <= 0:
        sys.exit(f"run-criteria: the run passed its whole limit of {run_limit} s; give a longer one with --run-timeout <s>, or run fewer checks, such as by --since <sha>")
    return min(limit, left)


def progress(text):
    """A line to stderr saying how far the run is, so a run that still moves reads apart from one that hangs."""
    print(f"run-criteria: {text}, {time.monotonic() - started:.0f} s", file=sys.stderr, flush=True)


def call(argv, cwd=None, env=None, text=False):
    """ARGV's finished process, its stdout and stderr read; past `call_limit` it is killed with every process it started and the run exits 1 naming it,
    since a git, tar or ps call that never answers would hang the run."""
    limit = within(call_limit)
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text, start_new_session=True)
    try:
        out, err = process.communicate(timeout=limit)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()  # never the output, which a process that left the group may hold open
        within(call_limit)
        sys.exit(f"run-criteria: `{' '.join(argv[:2])}` gave no answer in {call_limit} s; give a longer limit with --timeout <s>")
    return subprocess.CompletedProcess(argv, process.returncode, out, err)


def git_output(*argv, cwd=None):
    return call(["git", *argv], cwd=cwd, text=True).stdout.strip()


def export(root, ref, folder):
    """FOLDER/tree holding REF's files, or None when git or tar fails; the archive goes through a file, since a pipe between them is a read no limit bounds."""
    archive, copy = os.path.join(folder, "tree.tar"), os.path.join(folder, "tree")
    os.mkdir(copy)
    if call(["git", "archive", "--output", archive, ref], cwd=root).returncode or call(["tar", "-x", "-f", archive, "-C", copy]).returncode:
        return None
    return copy


def read_file(file):
    try:
        return file.read_text()
    except (OSError, UnicodeDecodeError) as e:
        sys.exit(f"run-criteria: could not read {file}: {e}")


def read_task(source):
    if source == "-":
        task = json.load(sys.stdin)  # a comment the board adapter has not marked, as a board's own listing prints it, gets its mark here
        return {**task, "comments": [{**comment, "trusted": comment.get("trusted", board.trusted(comment))} for comment in task.get("comments", [])]}
    try:
        number = board_refs.TaskRef.parse(source).number
    except board_refs.Refused as e:
        sys.exit(f"run-criteria: {source} is no file here, and {e}")
    try:
        found = board.fresh(number)
    except LookupError as e:
        sys.exit(f"run-criteria: {e}")
    return found or sys.exit(f"run-criteria: the board holds no task #{number}")


def runnable(task):
    """TASK when its author may write records; else exit, since an untrusted author's `[check]` would run as a command."""
    if not task_state.trusted(task):
        sys.exit("run-criteria: the task's author is not trusted, so its checks are not run; a trusted author must file the criteria")
    return task


PATH_WORD = r"""(~?/[^\s'"`;|&<>()$]+)"""
OUTSIDE_PATH = re.compile(r"(?<![\w.~/-])" + PATH_WORD)
WRITTEN_PATH = re.compile(r">>?\s*" + PATH_WORD)


def outside_files(command, root):
    """A sha-256 of every file outside ROOT that COMMAND names by an absolute or `~/` path, so a remembered pass holds only while they did not change;
    None when it names a folder outside ROOT, whose files are not read."""
    digest = hashlib.sha256()
    written = set(WRITTEN_PATH.findall(command))  # a file the check writes is its output, not its input
    for word in sorted(set(OUTSIDE_PATH.findall(command)) - written):
        path = pathlib.Path(os.path.expanduser(word))
        try:
            if path.resolve().is_relative_to(pathlib.Path(root).resolve()) or not path.exists():
                continue
            if not path.is_file():  # a folder's files are not read, and a pipe, a FIFO or a device would be read until its writer ends
                return None
            digest.update(str(path).encode() + b"\0" + path.read_bytes())
        except OSError:
            return None
    return digest.hexdigest()[:16]


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
        cap = task_state.live_runs(task)
        self.cap = LIVE_RUNS if cap is None else cap
        self.saved = pathlib.Path(git_output("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=root) or tempfile.gettempdir(), "teamwork-live")
        self.counted = pathlib.Path(git_output("rev-parse", "--absolute-git-dir", cwd=root) or tempfile.gettempdir(), "teamwork-live-runs")
        self.replayed = 0
        self.capped = False
        self.strict = True  # a watched path missing at the head is a typo that would pin the key; on the base it may not exist yet
        self.lock = threading.Lock()  # parallel sweep jobs start one session at a time, so the cap and a saved transcript hold

    def used(self):
        return len(self.counted.read_text().split()) if self.counted.exists() else 0

    def run(self, first, rest, paths, cwd, timeout):
        """(status, output) of the stages after FIRST on its transcript, which FIRST makes only when none is saved for its key and the cap allows."""
        with self.lock:
            return self.locked_run(first, rest, paths, cwd, timeout)

    def locked_run(self, first, rest, paths, cwd, timeout):
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


class Memory:
    """The `pass` of each check on one tree of files, kept in the git common dir's `teamwork-passes/`, so a check whose files did not change runs once for every session of the repository."""

    def __init__(self, root, tree, scope, fresh):
        self.root = root
        self.folder = pathlib.Path(git_output("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=root), "teamwork-passes")
        self.prefix = f"{tree}\0{scope}\0" if tree else None  # no tree, no memory
        self.fresh = fresh
        self.replayed = 0

    def entry(self, detail):
        return self.folder / hashlib.sha256((self.prefix + detail).encode()).hexdigest()[:32]

    def recall(self, detail):
        """(status, output) of the check's earlier pass on these files, or None."""
        if self.prefix is None or self.fresh:
            return None
        try:
            status, out = json.loads(self.entry(detail).read_text())
        except (OSError, ValueError):
            return None
        self.replayed += 1
        return status, out

    def keep(self, detail, status, out):
        if self.prefix is not None:
            try:
                self.folder.mkdir(parents=True, exist_ok=True)
                self.entry(detail).write_text(json.dumps([status, out]))
            except OSError:
                pass  # a git dir the run cannot write is no reason to lose the table

    def report(self):
        return f"\ncached: {self.replayed} checks replayed from an earlier pass on the same files; --fresh runs them again" if self.replayed else ""


class Sweep:
    """Whether the rows passing at the head all still pass with one file changed, the checks that failed most tried first, each result kept in the git common dir's `teamwork-sweeps/`."""

    def __init__(self, root, held, options, live):
        self.held = held
        self.options = options
        self.live = live
        self.kills = collections.Counter()
        self.lock = threading.Lock()
        self.folder = pathlib.Path(git_output("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=root), "teamwork-sweeps")
        outside = [outside_files(criteria_check.expectation(criterion[2])[0], root) for _, criterion in held]
        # a check that names a folder outside the repository reads files no key holds, so its results are never kept
        self.prefix = None if None in outside else json.dumps([git_output("rev-parse", "HEAD^{tree}", cwd=root), options.timeout, held, outside])
        self.replayed = 0

    def alive(self, copy, file, state, change, undo):
        """True when every held row passes in COPY with FILE made STATE by CHANGE, which UNDO takes back."""
        entry = self.folder / hashlib.sha256(f"{self.prefix}\0{file}\0".encode() + state).hexdigest()[:32] if self.prefix else None
        if entry and not self.options.fresh and entry.exists():
            with self.lock:
                self.replayed += 1
            return entry.read_text() == "alive"
        with self.lock:
            order = sorted(self.held, key=lambda held: -self.kills[held[0]])
        change()
        killer, settled = None, True
        try:
            for label, criterion in order:
                result, settled = self.judged(criterion, copy)
                if result != "pass":
                    killer = label
                    break
        finally:
            undo()
        if killer:
            with self.lock:
                self.kills[killer] += 1
        if entry and settled:
            try:
                self.folder.mkdir(parents=True, exist_ok=True)
                entry.write_text("killed" if killer else "alive")
            except OSError:
                pass  # a git dir the run cannot write is no reason to lose the sweep
        return killer is None

    def judged(self, criterion, copy):
        """(result, settled) of one held row in COPY; a timeout, the live-run cap or a missing watched path, whose status is None, and a live check,
        whose session may fail for a rate limit or a login, are not settled, so a later sweep runs them again instead of replaying them."""
        detail = criterion[2]  # a held row passed, so it is a `[check]` with a test
        command, test = criteria_check.expectation(detail)
        status, out = execute(command, detail, copy, self.options.timeout, self.live)
        return criteria_check.verdict(test, status, out), status is not None and not criteria_check.live_stage(detail)

    def report(self):
        return f"\ncached: {self.replayed} reverts and mutants replayed from an earlier sweep of the same files; --fresh sweeps them again" if self.replayed else ""


def git_state(root):
    """The commit, branch and index state of ROOT as text, since a check may read them and equal files do not make them equal."""
    status = call(["git", "status", "--porcelain=v1", "-z"], cwd=root, text=True).stdout
    return "\0".join([git_output("rev-parse", "HEAD", cwd=root), git_output("symbolic-ref", "-q", "HEAD", cwd=root), status])


def tree_of_files(root):
    """The git tree of every file in ROOT not ignored, as a sha, so equal files give an equal tree whoever wrote them; empty when git cannot say."""
    with tempfile.TemporaryDirectory(prefix="run-criteria-index-") as folder:
        environment = {**os.environ, "GIT_INDEX_FILE": str(pathlib.Path(folder, "index"))}
        added = call(["git", "add", "-A"], cwd=root, env=environment)
        written = call(["git", "write-tree"], cwd=root, env=environment, text=True)
        return written.stdout.strip() if not added.returncode and not written.returncode else ""


def execute(command, detail, cwd, timeout, live):
    """(status, output) of a check, its live first stage replayed from a saved transcript when it has one."""
    stages = criteria_check.live_stage(detail)
    return live.run(*stages, criteria_check.watched(detail), cwd, timeout) if stages else run(command, cwd, timeout)


def recalled(memory, detail, command, cwd, timeout, live, passes):
    """(status, output) of a check from MEMORY when it passed on these files, else from running it, kept when PASSES(status, output) holds."""
    outside = outside_files(command, memory.root) if memory else None  # read before the run, which may write a file it names
    key = f"{detail}\0{outside}"
    found = memory.recall(key) if memory and outside else None
    if found:
        return found
    status, out = execute(command, detail, cwd, timeout, live)
    if memory and outside and passes(status, out):
        memory.keep(key, status, out)
    return status, out


# only a program that runs the missing file says so: a read of it (`grep`, `cat`, `sed`) names its own program first
MISSING_FILE = re.compile(r"can't open file '(?P<python>[^']+)': \[Errno 2\]|^(?:ba|z)?sh(?:: line \d+)?: (?P<shell>[^:]+): No such file or directory$")


def absent_in_export(out, archive):
    """Whether every line of OUT says a file is missing that the export ARCHIVE lacks, as a check's script does that the change adds."""
    found = [MISSING_FILE.search(line) for line in out.splitlines()]
    paths = [pathlib.Path(archive, hit["python"] or hit["shell"]) for hit in found if hit]
    return bool(out) and all(found) and all(path.resolve().is_relative_to(pathlib.Path(archive).resolve()) and not path.exists() for path in paths)


def base_row(label, kind, name, detail, archive, timeout, live, memory, exported):
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
    status, out = recalled(memory, detail, command, archive, timeout, live, lambda status, out: status is not None and out == quoted)
    if "not a git repository" in out:
        return label, name, "unclear", "git needs a checkout, which the export lacks"
    if status is not None and out != quoted and absent_in_export(out, archive):
        out = "FAIL"  # a script the change adds is missing on base, which is the failure the criterion quotes
    if status is not None and out == quoted and criteria_check.verdict(test, status, out) != "pass":
        # what is left of the check once its file scans do nothing still prints the passing output on base, so a scan alone fails it there
        bare = criteria_check.without_scans(command, exported)
        if bare and criteria_check.verdict(test, *recalled(memory, detail + "\0no-scan", bare, archive, timeout, None, lambda status, out: status is not None)) == "pass":
            return label, name, "text scan", "a text scan alone fails it on base; the rest prints the passing output there"
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
    if ref:
        return ref
    known = [git_output("symbolic-ref", "--short", "refs/remotes/origin/HEAD"), *(name for name in ("origin/main", "main") if git_output("rev-parse", "--verify", "--quiet", name))]
    return next(filter(None, known), None) or sys.exit("run-criteria: found no origin/HEAD, origin/main or main; name the base with --ref")


def run_on_base(root, ref, rows, timeout, live, memory):
    """Rows of every criterion run in a `git archive` copy of the base, so the head's files never answer."""
    with tempfile.TemporaryDirectory(prefix="run-criteria-base-") as folder:
        copy = export(root, ref, folder) or sys.exit(f"run-criteria: could not export {ref}; fetch it first")
        # the list is made before any check runs, so a file a check writes is not taken for one the base holds
        with tempfile.NamedTemporaryFile("w", prefix="run-criteria-files-") as exported_files:
            exported_files.write("".join(f"./{path.relative_to(copy)}\n" for path in pathlib.Path(copy).rglob("*") if path.is_file()))
            exported_files.flush()
            return [base_row(str(n), *criterion, copy, timeout, live, memory, exported_files.name) for n, criterion in enumerate(rows, 1)]


def end_strays(folder):
    """Kill every process that runs a file of the temporary copy FOLDER, since a check may start a monitor in a session of its own that outlives it, and a copy with a hunk reverted can miss the call that ends it."""
    listed = call(["ps", "-A", "-o", "pid=,command="], text=True).stdout.splitlines()
    for line in listed:
        pid, _, command = line.strip().partition(" ")
        if pid.isdigit() and int(pid) != os.getpid() and str(folder) + os.sep in command:
            os.kill(int(pid), signal.SIGKILL)


def descendants(pid):
    """Every running process PID started, in its session or not."""
    children = {}
    for line in call(["ps", "-A", "-o", "pid=,ppid="], text=True).stdout.splitlines():
        child, parent = map(int, line.split())
        children.setdefault(parent, []).append(child)
    found, waiting = [], [pid]
    while waiting:
        started = children.get(waiting.pop(), [])
        found += started
        waiting += started
    return found


def run(command, cwd, timeout):
    """(exit status or None on a timeout, stdout and stderr as one text)."""
    limit = within(timeout)
    process = subprocess.Popen(["bash", "-c", command], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               start_new_session=True)
    try:
        out, _ = process.communicate(timeout=limit)
        return process.returncode, out.strip()
    except subprocess.TimeoutExpired:
        # read before the kill, since a child that left the check's session keeps its pipe open and is reparented once the session dies
        strays = descendants(process.pid)
        os.killpg(process.pid, signal.SIGKILL)
        for pid in strays:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:  # it ended with the session
                pass
        process.wait()  # never the output, which a process that left the tree before the timeout may hold open for good
        within(timeout)
        return None, f"timed out after {timeout} s; give a longer limit with --timeout <s>"
    finally:
        if pathlib.Path(cwd).resolve().is_relative_to(pathlib.Path(tempfile.gettempdir()).resolve()):
            end_strays(pathlib.Path(cwd).resolve())


def cell(text):
    text = " / ".join(line.strip() for line in text.splitlines() if line.strip()).replace("|", "\\|")
    return text if len(text) <= CELL else text[:CELL - 1] + "…"


def row(label, kind, name, detail, cwd, timeout, live, memory=None):
    if kind == "score":
        return label, name, "judged", "not run: a score is judged"
    if kind != "check":
        return label, name, "unclear", "not run: no kind"
    command, test = criteria_check.expectation(detail)
    if test[0] is None:
        return label, name, "unclear", f"not run: {test[1]}"
    status, out = recalled(memory, detail, command, cwd, timeout, live, lambda status, out: criteria_check.verdict(test, status, out) == "pass")
    return label, name, criteria_check.verdict(test, status, out), cell(out)


def table_line(cells):
    return "| " + " | ".join([cells[0], cells[1].replace("|", "\\|"), *cells[2:]]) + " |"


def fingerprint(criterion):
    """The first 16 hex digits of the sha-256 of a criterion's kind, name and details, so any rewording changes it."""
    return hashlib.sha256("\0".join(criterion).encode()).hexdigest()[:16]


def criteria(text):
    for line in task_state.ITEM.findall(text):
        _, kind, name, detail = task_state.CRITERION.match(line).groups()
        if kind != "task":  # a part is met by its own task's close, never by a command
            yield kind or "", name or detail, detail if name else ""


def task_criteria(task):
    return list(criteria(task_state.sections(task.get("body")).get("done", "")))


def earlier_fails(task):
    """{name: {output, ...}} of the `fail` rows in earlier tables on the task, by trusted authors only."""
    found = {}
    for comment in task.get("comments", []):
        if task_state.trusted(comment) and comment["body"].startswith(HEADER):
            for line in comment["body"].splitlines():
                cells = [part.strip() for part in re.split(r"(?<!\\)\|", line)[1:-1]]
                if len(cells) in (4, 5) and cells[2] == "fail":
                    found.setdefault(cells[1], set()).add(cells[3])
    return found


def split_hunks(diff):
    """[(file, line, patch)] of each hunk of a `git diff -U0` text read as latin-1, so each byte stays one character: the file's header lines and the one hunk."""
    found = []
    for section in re.split(r"(?m)^(?=diff --git )", diff):
        head, *hunks = re.split(r"(?m)^(?=@@ )", section)
        file = re.search(r"^\+\+\+ b/(.+?)\t?$|^--- a/(.+?)\t?$", head, re.M)
        for hunk in hunks:
            old, new = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)", hunk).groups()
            found.append((next(name for name in file.groups() if name).encode("latin-1").decode("utf-8", "replace"), int(new) or int(old), head + hunk.rstrip("\n") + "\n"))
    return found


def take_back(text, patches):
    """TEXT of a file read as latin-1 with the removed lines of each one-hunk PATCHES entry put back where the hunk added or changed them, last hunk first so each keeps its line number; lines end at `\\n` only, since a file may hold other line breaks."""
    lines = re.findall(r"[^\n]*\n|[^\n]+", text)
    spans = []
    for patch in patches:
        header, _, body = patch[re.search(r"(?m)^@@ ", patch).start():].partition("\n")
        start, count = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))?", header).groups()
        count = 1 if count is None else int(count)
        first = int(start) if count == 0 else int(start) - 1
        removed, before = [], ""
        for row in re.findall(r"[^\n]*\n|[^\n]+", body):
            if row[0] == "-":
                removed.append(row[1:])
            elif row[0] == "\\" and before == "-":
                removed[-1] = removed[-1].removesuffix("\n")
            before = row[0]
        spans.append((first, count, removed))
    for first, count, removed in sorted(spans, key=lambda span: -span[0]):
        lines[first:first + count] = removed
    return "".join(lines)


def added_mutants(line, patch, text):
    """(line, start, end, replacement, kind) of each mutant of the lines a Python hunk adds in TEXT, its first added line being LINE, as byte spans:
    each `if` or `elif` test made `False`, each other comparison negated, each number made 0, or 1 when it is 0, each codec name given to
    `decode`, `encode` or `encoding=` made `latin-1`, or `utf-8` when it is that, and each list or tuple written without one element and each
    `and` or `or` without one operand, each path call swapped for its sibling in SIBLINGS, each `<side> == <text>` widened to
    `<text> in <side>` and each `sorted(<items>, ...)` made `list(<items>)`; a mutant that is not valid Python is left out."""
    added = range(line, line + sum(1 for each in patch.split("\n@@", 1)[-1].splitlines()[1:] if each.startswith("+")))
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    starts = [0]
    data = text.encode()
    for each in data.splitlines(keepends=True):
        starts.append(starts[-1] + len(each))

    def span(node):
        return starts[node.lineno - 1] + node.col_offset, starts[node.end_lineno - 1] + node.end_col_offset

    tests = {id(node.test) for node in ast.walk(tree) if isinstance(node, ast.If)}
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and node.lineno in added:
            found.append((node.lineno, *span(node.test), b"False", "condition"))
        elif isinstance(node, ast.Compare) and node.lineno in added and id(node) not in tests:
            start, end = span(node)
            found.append((node.lineno, start, end, b"(not (" + data[start:end] + b"))", "comparison"))
        if isinstance(node, ast.Compare) and node.lineno in added and isinstance(node.ops[0], ast.Eq):
            text_side = node.comparators[0]
            if isinstance(text_side, ast.Constant) and isinstance(text_side.value, str):
                found.append((node.lineno, *span(node), ast.unparse(ast.Compare(text_side, [ast.In()], [node.left])).encode(), "equality"))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sorted" and node.args and node.lineno in added:
            found.append((node.lineno, *span(node), ast.unparse(ast.Call(ast.Name("list"), node.args[:1], [])).encode(), "sort"))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in SIBLINGS and node.func.end_lineno in added:
            end = span(node.func)[1]
            found.append((node.func.end_lineno, end - len(node.func.attr), end, SIBLINGS[node.func.attr].encode(), "path call"))
        elif isinstance(node, ast.Constant) and type(node.value) in (int, float) and node.lineno in added:
            found.append((node.lineno, *span(node), b"1" if node.value == 0 else b"0", "number"))
        elif isinstance(node, ast.Call):
            named = node.args[:1] if isinstance(node.func, ast.Attribute) and node.func.attr in ("decode", "encode") else []
            for codec in named + [keyword.value for keyword in node.keywords if keyword.arg == "encoding"]:
                if isinstance(codec, ast.Constant) and isinstance(codec.value, str) and codec.lineno in added:
                    try:
                        latin = codecs.lookup(codec.value).name == "iso8859-1"
                    except LookupError:
                        continue
                    found.append((codec.lineno, *span(codec), b'"utf-8"' if latin else b'"latin-1"', "codec"))
        parts = []
        if isinstance(node, (ast.List, ast.Tuple)) and isinstance(node.ctx, ast.Load):
            parts, kind = node.elts, type(node).__name__.lower()
        elif isinstance(node, ast.BoolOp):
            parts, kind = node.values, "operands"
        for index, part in enumerate(parts):
            if part.lineno in added:
                rest = parts[:index] + parts[index + 1:]
                # the rest is written out whole, since cutting the part's own bytes would leave its comma, operator or bracket behind
                found.append((part.lineno, *span(node), ast.unparse(ast.BoolOp(node.op, rest) if kind == "operands" else type(node)(rest)).encode(), kind))
    valid = []
    for line, start, end, replacement, kind in sorted(found):
        try:
            ast.parse(data[:start] + replacement + data[end:])
        except SyntaxError:
            continue
        valid.append((line, start, end, replacement, kind))
    return valid


def raised_at_start(text):
    """[(line, start, end, replacement, kind)] of the one mutant that makes the Python TEXT raise at its first line, so every run of it
    fails alike; none for a text that is empty, as that of a file the sweep does not mutate is, or no Python."""
    try:
        ast.parse(text)
    except SyntaxError:
        return []
    first = 0  # the mutant goes before the first byte, since a later place may sit inside a comment
    return [(1, first, first, b"raise RuntimeError\n", "start of the file")] if text else []


def run_per_hunk(options, task, root, live):
    """Names each hunk of the change whose revert alone turns no passing row into another result; exit 1 on one."""
    ref = base_ref(options.ref)
    diff = call(["git", "-c", "core.quotepath=false", "diff", "--no-renames", "--src-prefix=a/", "--dst-prefix=b/", "-U0", f"{ref}...HEAD"], cwd=root).stdout
    hunks = split_hunks(diff.decode("latin-1"))
    found = [(str(n), criterion) for n, criterion in enumerate(task_criteria(task), 1)]
    runners = sorted({file for file, _, _ in hunks if RUNNER.search(file)})
    if options.since:
        # a hunk no line of which moved since the last sweep keeps that sweep's result, so only the moved ones are swept
        moved = changed_lines(root, options.since)
        # a file changed with no hunk since, such as a binary, moved as a whole
        # the line before a hunk counts as its own, since a fix that removes the hunk's first lines touches that line
        kept = [hunk for hunk in hunks if hunk[0] not in moved or moved[hunk[0]] and not moved[hunk[0]] & {hunk_lines(hunk)[0] - 1, *hunk_lines(hunk)}]
        hunks = [hunk for hunk in hunks if hunk not in kept]
    found += [(file, ("check", file, f"`{'bun' if file.endswith('.ts') else 'python3'} {file}` exits 0")) for file in runners]

    # a check that passed on the head's files is replayed, so a second sweep of the same head runs none
    memory = Memory(root, git_output("rev-parse", "HEAD^{tree}", cwd=root), "hunks", options.fresh)

    def results(copy):
        """Label to result of each row in COPY; a git check, which the export cannot run, never passes."""
        return {label: row(label, *criterion, copy, options.timeout, live, memory)[2] for label, criterion in found}

    with tempfile.TemporaryDirectory(prefix="run-criteria-hunks-") as folder:
        # the head's export is never changed once its checks ran, so each job's copy is made from it while other jobs change theirs
        first = export(root, "HEAD", folder) or sys.exit("run-criteria: could not export HEAD")
        at_head = results(first)
        failing = [label for label, result in at_head.items() if result == "fail" and label not in runners]
        # a check that fails only in the export, such as one that reads the checkout's git, cannot judge a hunk there, so it is not held
        criterion_of = dict(found)
        exported_only = [label for label in failing if row(label, *criterion_of[label], root, options.timeout, live)[2] == "pass"]
        for label in exported_only:
            print(f"{label}: not swept: it fails in an export of the head and passes in the checkout, as a git check does")
        failing = [label for label in failing if label not in exported_only]
        if failing:
            print(*[f"{label}: fails at the head: make it pass first, since a hunk cannot be judged by a criterion that does not" for label in failing], sep="\n")
            print(live.report(), end="")
            return 1
        sweep = Sweep(root, [(label, criterion) for label, criterion in found if at_head[label] == "pass"], options, live)
        jobs = options.jobs or os.cpu_count()
        copies = queue.Queue()
        for n in range(jobs):
            # each job owns an export, since a check may write into the tree it runs in
            shutil.copytree(first, os.path.join(folder, str(n)), symlinks=True)
            copies.put(os.path.join(folder, str(n)))

        def in_a_copy(work, *argv):
            """WORK run on an idle export."""
            copy = copies.get()
            try:
                return work(copy, *argv)
            finally:
                copies.put(copy)

        def survives(copy, group):
            """True when no passing row changes with every hunk of GROUP, all of one file or link, reverted together."""
            progress(f"reverting {len(group)} hunks of {group[0][0]}, file {list(by_file).index(group[0][0]) + 1} of {len(by_file)}")
            path = pathlib.Path(copy, group[0][0])
            link = os.readlink(path) if path.is_symlink() else None
            kept = path.read_bytes() if link is None and path.is_file() else None
            mode = path.stat().st_mode if kept is not None else None
            before = os.fsencode(link) + b"\n" if link is not None else kept
            text = take_back(before.decode("latin-1") if before is not None else "", [patch for _, _, patch in group])
            absent = not text and "\nnew file mode " in group[0][2]
            symlink = "120000" in group[0][2].split("\n@@", 1)[0]
            made = [folder for folder in reversed(path.parents) if not folder.exists()]

            def revert():
                path.unlink(missing_ok=True)
                if not absent:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if symlink:
                        os.symlink(text.rstrip("\n").encode("latin-1"), path)
                    else:
                        path.write_bytes(text.encode("latin-1"))
                        if mode is not None:
                            path.chmod(stat.S_IMODE(mode))

            def restore():
                path.unlink(missing_ok=True)
                for folder in made[:1]:
                    shutil.rmtree(folder)
                if link is not None:
                    os.symlink(link, path)
                elif kept is not None:
                    path.write_bytes(kept)
                    path.chmod(stat.S_IMODE(mode))

            state = b"absent" if absent else (b"link\0" if symlink else b"file\0") + text.encode("latin-1")
            return sweep.alive(copy, group[0][0], state, revert, restore)

        def judged_file(copy, group):
            """(hunks needed by no row, hunks not judged one by one) of a file of many hunks, judged whole and by halves."""
            if survives(copy, group):
                return group, []
            halves = [group[:len(group) // 2], group[len(group) // 2:]]
            passing = [half for half in halves if survives(copy, half)]
            return [hunk for half in passing for hunk in half], [hunk for half in halves if half not in passing for hunk in half]

        finished, counting = collections.Counter(), threading.Lock()

        def mutant_survives(copy, file, text, start, end, replacement, where):
            path = pathlib.Path(copy, file)
            data = text.encode()
            mutated = data[:start] + replacement + data[end:]
            alive = sweep.alive(copy, file, b"file\0" + mutated, lambda: path.write_bytes(mutated), lambda: path.write_text(text))
            # jobs end in any order, so the count is of the file's mutants finished, which reaches the total last
            with counting:
                finished[file] += 1
                progress(f"mutant {finished[file]}{where}")
            return alive

        by_file = {}
        for hunk in hunks:
            by_file.setdefault(hunk[0], []).append(hunk)
        unneeded, conditions, mutants, unjudged = [], 0, 0, []
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            reverts = {}
            for file, group in by_file.items():
                if len(group) > FEW_HUNKS and not options.each:
                    # a file of many hunks, such as a built page, is judged whole and by halves, so the rest of it is judged only when --each asks
                    reverts[file] = pool.submit(in_a_copy, judged_file, group)
                else:
                    reverts[file] = [pool.submit(in_a_copy, survives, [hunk]) for hunk in group]
            alone, tried = {}, {}
            for place, (file, group) in enumerate(by_file.items(), 1):
                if isinstance(reverts[file], list):
                    alone[file] = [hunk for hunk, revert in zip(group, reverts[file]) if revert.result()]
                else:
                    alone[file], failing = reverts[file].result()
                    if failing:
                        unjudged.append((file, len(failing)))
                path = pathlib.Path(first, file)
                text = path.read_text() if file.endswith(".py") and path.is_file() and "fixtures" not in pathlib.PurePosixPath(file).parts else ""
                needed = [added_mutants(line, patch, text) for _, line, patch in (hunk for hunk in group if hunk not in alone[file])]
                # a file whose every hunk is unneeded is named already, so only one a criterion needs is made to raise
                made = [mutant for each in needed + [raised_at_start(text)] * bool(needed) for mutant in each]
                tried[file] = [(number, start, end, replacement, kind, text,
                                pool.submit(in_a_copy, mutant_survives, file, text, start, end, replacement, f" of {len(made)} in {file}, file {place} of {len(by_file)}"))
                               for number, start, end, replacement, kind in made]
            for file in by_file:
                unneeded += [f"{file}:{line}: unneeded hunk: a hunk whose revert fails no criterion is unneeded, or its criterion is vacuous" for _, line, _ in alone[file]]
                for number, start, end, replacement, kind, text, alive in tried[file]:
                    data = text.encode()
                    if kind == "condition":
                        conditions += 1
                    else:
                        mutants += 1
                    if alive.result() and kind == "condition":
                        unneeded.append(f"{file}:{number}: unneeded condition: no criterion reaches this branch, so drop it or make a criterion refuse through it")
                    elif alive.result():
                        unneeded.append(f"{file}:{number}: surviving mutant: no criterion fails when the {kind} `{' '.join(data[start:end].decode().split())[:80]}` becomes `{replacement.decode().strip()}`, so make a criterion fail on it or drop it")
    print(f"hunks: {len(hunks)} reverted against {ref}, {conditions} conditions made False, {mutants} mutants made, {len(unneeded)} unneeded"
          + (f", {len(kept)} unchanged since {options.since}, not swept" if options.since else ""))
    print(*unneeded, sep="\n")
    print(*[f"{file}: {count} hunks not judged one by one, since reverting them together fails a criterion; --each judges each" for file, count in unjudged], sep="\n")
    print(live.report() + memory.report() + sweep.report(), end="")
    return 1 if unneeded else 0


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
    memory = Memory(root, git_output("rev-parse", f"{ref}^{{tree}}", cwd=root), "base", options.fresh)
    rows = run_on_base(root, ref, task_criteria(task), options.timeout, live, memory)
    print(f"REPORTED: base outputs at {ref} {sha}\n\n| # | criterion | result | output on base |\n| --- | --- | --- | --- |")
    for table_row in rows:
        print(table_line(table_row))
    if any(table_row[2] == "wrong base" for table_row in rows):
        print(WRONG_BASE_FIX)
    if any(table_row[2] == "text scan" for table_row in rows):
        print(TEXT_SCAN_FIX)
    print(live.report() + memory.report(), end="")
    return 1 if any(table_row[2] in ("wrong base", "text scan") for table_row in rows) else 0


def run_at_head(options, task, root, live):
    """The table of the criteria, then the standing ones, run at the head; exit 1 on any `fail`."""
    standing = pathlib.Path(root, ".teamwork", "default-criteria.md")
    found = [(str(n), criterion) for n, criterion in enumerate(task_criteria(task), 1)]
    found += [("standing", criterion) for criterion in criteria(standing.read_text())] if standing.exists() else []
    memory = Memory(root, tree_of_files(root), f"{root}\0{git_state(root)}", options.fresh)
    rows = [(*row(label, *criterion, root, options.timeout, live, memory), fingerprint(criterion)) for label, criterion in found]
    print(f"{HEADER}{git_output('rev-parse', 'HEAD', cwd=root)}" + (" with uncommitted changes" if git_output("status", "--porcelain", cwd=root) else ""))
    print("\n| # | criterion | result | output | sha-256 |\n| --- | --- | --- | --- | --- |")
    for table_row in rows:
        print(table_line(table_row))
    before = earlier_fails(task)
    for _, name, result, out, _ in rows:
        if result == "fail" and out in before.get(name.replace("|", "\\|"), ()):
            print(f"\nBLOCKED due: {name} failed with the same output as in an earlier table; ask your manager by `BLOCKED:`.")
    print(live.report() + memory.report(), end="")
    return 1 if any(table_row[2] == "fail" for table_row in rows) else 0


COVERS = re.compile(r"\bcovers:\s*(?P<parts>(?:`[^`]+`\s*,?\s*)+)")
HEADING = re.compile(r"^(?P<level>#{1,6})\s+(?P<title>.*?)\s*#*\s*$")


def covered_parts(detail):
    """The parts a criterion's `covers:` clause names, each a path, a folder or `<path>#<section>`; none means all."""
    match = COVERS.search(detail)
    return re.findall(r"`([^`]+)`", match["parts"]) if match else []


def slug(heading):
    """A Markdown heading's anchor as GitHub writes it: lower case, punctuation dropped, each space a `-`."""
    return re.sub(r" ", "-", re.sub(r"[^\w\- ]", "", heading.lower()))


PARSED = ("handle_starttag", "handle_endtag")  # html.parser calls these by name


class ElementSpans(html.parser.HTMLParser):
    """Line spans of each element with an `id`, from its start tag's line to its end tag's; an element never closed has none, and of two with one `id` the first to end keeps it."""

    def __init__(self):
        super().__init__()
        self.spans, self.open = {}, []

    def handle_starttag(self, tag, attributes):
        line, _ = self.getpos()
        self.open.append((tag, dict(attributes).get("id"), line))

    def handle_endtag(self, tag):
        inner = [index for index, (name, _, _) in enumerate(self.open) if name == tag]
        if inner:
            index = max(inner)  # the innermost open element of that tag; any opened inside it close with it
            last, _ = self.getpos()
            for _, found, line in self.open[index:]:
                self.spans.setdefault(found, (line, last))
            del self.open[index:]


def section_span(text, path, section):
    """(first, last) line of SECTION in TEXT: a Markdown heading's slug up to the next heading as high, or an HTML element's `id`; None when absent."""
    if path.endswith((".html", ".htm")):
        parser = ElementSpans()
        parser.feed(text)
        return parser.spans.get(section)
    lines, fenced = text.splitlines(), False
    headings = []
    for line in lines:
        fenced ^= line.lstrip().startswith(("```", "~~~"))
        headings.append(None if fenced else HEADING.match(line))  # a `#` line inside a code fence is no heading
    for number, match in enumerate(headings, 1):
        if match and slug(match["title"]) == section:
            # enumerate from NUMBER gives each later line the number of the line before it, the section's last
            return number, next((before for before, other in enumerate(headings[number:], number)
                                 if other and len(other["level"]) <= len(match["level"])), len(lines))
    return None


def hunk_lines(hunk):
    """The head lines a one-hunk patch spans; one that only removes spans the line before it."""
    start, count = re.search(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))?", hunk[2]).groups()
    return range(int(start), int(start) + int(count or "1")) or [int(start)]


def changed_lines(root, since):
    """{file: set of head lines} each hunk between SINCE and the head touches; a hunk that only removes touches the line before it, and a file changed with no hunk, or whose name git quotes, maps to an empty set."""
    diff = call(["git", "-c", "core.quotepath=false", "diff", "--no-renames", "--src-prefix=a/", "--dst-prefix=b/", "-U0", since, "HEAD"], cwd=root)
    if diff.returncode:
        sys.exit(f"run-criteria: --since {since} names no commit here")
    names = call(["git", "diff", "--no-renames", "--name-only", "-z", since, "HEAD"], cwd=root, text=True)
    found = {file: set() for file in names.stdout.split("\0") if file}  # a file with no hunk keeps an empty set: it changed as a whole
    # a name git quotes in a header, one with a `"`, a tab or a backslash, gets no hunk read, so it changed as a whole
    named = "".join(part for part in re.split(r"(?m)^(?=diff --git )", diff.stdout.decode("latin-1")) if not part.startswith('diff --git "'))
    for hunk in split_hunks(named):
        found[hunk[0]].update(hunk_lines(hunk))
    return found


def run_since(options, task, root):
    """Names each criterion whose covered parts changed between `--since` and the head, to be judged again, and each changed line no criterion covers."""
    changed = changed_lines(root, options.since)
    found = task_criteria(task)
    standing = pathlib.Path(root, ".teamwork", "default-criteria.md")
    wholes, sections, missing, touched = set(), {}, [], {}
    for n, (_, _, detail) in enumerate(found, 1):
        for part in covered_parts(detail):
            path, _, section = part.partition("#")
            path = path.rstrip("/")
            if not section:
                wholes.add(path)
                touched.setdefault(n, []).extend(part for file in changed if file == path or file.startswith(path + "/"))
                continue
            # the head commit's file, since the hunks are the head commit's and an uncommitted edit would shift its lines
            head = call(["git", "show", f"HEAD:{path}"], cwd=root)
            span = section_span(head.stdout.decode(errors="replace"), path, section)  # a file the head lacks prints nothing, so it holds no section
            if span is None:
                missing.append(f"{n}: covers `{part}`, which the head lacks: name a section by its Markdown heading's anchor or an HTML element's `id`")
                touched.setdefault(n, []).append(part)
                continue
            first, last = span
            sections.setdefault(path, set()).update(range(first, last + 1))
            # a file with no hunk, such as a binary or a mode change, changed as a whole, so every section of it did
            if path in changed and (not changed[path] or any(first <= line <= last for line in changed[path])):
                touched.setdefault(n, []).append(part)
    short = git_output("rev-parse", "--short", options.since, cwd=root)
    print(f"since {short}: {len(changed)} files changed")
    whole = [n for n, (_, _, detail) in enumerate(found, 1) if not covered_parts(detail)]
    for n, (_, name, _) in enumerate(found, 1):
        if n in whole:
            print(f"{n}: judge again: it names no `covers:`, so it covers every part")
        elif touched.get(n):
            print(f"{n}: judge again: {', '.join(f'`{part}`' for part in dict.fromkeys(touched[n]))} changed")
        else:
            print(f"{n}: unchanged since {short}: keep its verdict")
    for n, _ in enumerate(criteria(standing.read_text()) if standing.exists() else [], 1):
        print(f"standing {n}: judge again: a standing criterion of the repository runs every round")
    for line in missing:
        print(line)
    if not whole:
        for file, lines in changed.items():
            if any(file == path or file.startswith(path + "/") for path in wholes):
                continue
            outside = lines - sections.get(file, set()) if lines else (set() if file in sections else {1})
            if outside:
                print(f"{file}:{min(outside)}: covered by no criterion: judge this change, and name its part in a `covers:`")
    return 0


def main(args):
    parser = usage_parser.parser(__doc__)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--run-timeout", type=int, default=7200)
    parser.add_argument("--base", "--main", action="store_true")
    parser.add_argument("--hunks", action="store_true")
    parser.add_argument("--each", action="store_true")
    parser.add_argument("--jobs", type=int)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--ref")
    parser.add_argument("--since")
    parser.add_argument("--pass", dest="samples", action="append", default=[], metavar="N=FILE")
    parser.add_argument("task")
    options = parser.parse_args(data_folder.enter(args, __doc__))
    global call_limit, run_limit
    call_limit, run_limit = options.timeout, options.run_timeout
    file = pathlib.Path(options.task)
    task = {"body": read_file(file), "comments": []} if file.is_file() else runnable(read_task(options.task))
    root = git_output("rev-parse", "--show-toplevel") or "."
    if options.samples:
        return run_with_samples(options, task, root)
    if options.hunks and options.base or options.since and options.base or options.jobs is not None and options.jobs < 1:
        usage_parser.refuse(__doc__)
    if options.since and not options.hunks:
        return run_since(options, task, root)
    if options.hunks:
        return run_per_hunk(options, task, root, Live(root, task))
    if options.base:
        return run_against_base(options, task, root, Live(root, task))
    return run_at_head(options, task, root, Live(root, task))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
