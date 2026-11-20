#!/usr/bin/env python3
"""Run each `[check]` of a task's Definition of done at the head, in the worktree's root, then each `[check]` of an
optional `.teamwork/default-criteria.md` there as `standing`, and print a table to comment on the task, which the
judge reads instead of running each check again.

usage: run-criteria.py [--timeout <s>] [--fresh] [--base [--ref <ref>] | --hunks [--each] [--ref <ref>] | --pass <n>=<sample-file>...] <task | body-file | ->

A task is its number, `#n` or url; `-` reads the task as JSON, its `body`, `trusted` and `comments`. A word that names no file and no task
on the board prints one line saying which, exit 1. `--timeout` is each check's limit, 900 s unless given.
A task, by number or JSON, whose author is not `trusted` is refused, exit 1, since its checks would run as commands; a body
file is the worker's own draft, so it runs.

A row is `pass` or `fail` by the output the criterion says it `prints`, or the status it `exits`; `unclear` when the
script cannot decide it, such as a `<placeholder>`, two commands or an expected text found inside other output, which the
judge runs; `judged` for a `[score]`. A timeout is a `fail`. Exit 1 on any `fail`. Each row's `sha-256` is the
first 16 hex digits of the hash of the criterion's kind, name and details, so a judge sees a criterion reworded after
its first judged table. A `[check]` that passed on the same files, not counting ignored ones, and the same commit, branch and index (or with `--base` the base's files) is not run again by any session of the
repository: its row is its earlier output, and `cached: <n> checks replayed` follows the table. `--fresh` runs every check again; a failed check always runs. A `BLOCKED due: <name>` line follows
when a criterion fails with the output it had in an earlier table on the task: ask your manager by `BLOCKED:`, since
it has failed twice the same way.

`--base` runs each `[check]` in an export of the base instead, `--ref` or else the first of `origin/HEAD`, `origin/main` and `main` that exists, and prints `base ok` when
its output equals the text quoted after `on base` (or `on main`, in tasks filed before), `wrong base` when it differs,
`text scan` when the quote matches only because a grep, `awk`, `sed` or another file read alone fails it, the rest of the command printing the passing output on base, `unclear` when the quote is not one value; exit 1 on any `wrong base` or `text scan`; an `exits` or `more` check, a git check (the
export has no `.git`) and a check with a placeholder are `unclear`. The output is compared whole. It never fetches: run `git fetch` first. A body file reads criteria before the task exists, so run it before the first judge.
A body file alone runs its criteria at the head.

A `[check]` whose first pipe stage runs `claude -p` and which says `watches: <path>...` is a live check: its first stage's
output is saved as a transcript, when the session exits 0, under the git common dir's `teamwork-live/`, keyed by that stage and the content of the
watched paths, and the stages after it run on the transcript. A run whose key has a saved transcript starts no session,
so a fix to the later stages, or to a file outside the watched paths, replays; each new session counts toward the cap, the
task's latest `decide --live-runs <n>` or else `LIVE_RUNS` (4), kept in the worktree's git dir, so a worktree's tasks share one count; a watched path
missing at the head fails the check. At the cap the live check fails
without running and a `BLOCKED due: live runs` line follows.

`--hunks` first runs the `[check]`s at the head and, when one fails, prints `<n>: fails at the head` for it and judges no hunk, exit 1; it then reverts each hunk of the change from the base (`--ref`, else as `--base`) to the head alone in an export of the head,
runs the `[check]`s there, and prints `<file>:<line>: unneeded hunk` for each hunk whose revert turns no row that passes at the
head into another result: a hunk whose revert fails no criterion is unneeded, or its criterion is vacuous. Exit 1 on any such
hunk; a git check, which the export cannot run, never counts. A file of more than 4 hunks is reverted whole, then by
halves, and a half whose revert fails a criterion is not judged hunk by hunk: `<file>: <n> hunks not judged one by one` is
printed, and `--each` reverts each hunk alone as every file of 4 hunks or fewer is. A hunk no check can
see, such as a `version` bump, a usage line, a docstring or a document, is always named: the judge reads it as needed. In a hunk
that is needed, the test of each `if` or `elif` statement it adds to a Python file is then made `False` alone, and `<file>:<line>: unneeded condition` is printed
for each whose branch no criterion reaches, exit 1 too, since a refusal no check reaches hides inside a hunk a check needs. It runs
the checks once per reverted group and per such line, so give a long check time with `--timeout`; it never fetches.

`--pass <n>=<sample-file>` (once per criterion, with a body file) runs criterion `n` at the head with its first pipe stage
replaced by `cat <sample-file>`, so the stages after it meet the input the pass would give. It prints `pass ok` when the
output equals the text after `prints` (or meets `exits` or `more`), `wrong pass` when it differs, `unclear` for a criterion with no sample or whose first
stage it cannot split surely: before its first pipe, outside quotes, only words, blanks and `. / = : , + @ % ~ < -`
may stand, and the first word is no `if`, `while`, `for` or other compound keyword; inside double quotes no `$(`, `${`, backtick
or backslash; exit 1 on any
`wrong pass`. It finds a check that can never pass, such as `check-schema.py check /dev/stdin`, which reads its input twice."""
import ast
import hashlib
import json
import os
import pathlib
import re
import shlex
import signal
import shutil
import stat
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402
import criteria_check  # noqa: E402
import decisions  # noqa: E402
import task_state  # noqa: E402
import usage_parser  # noqa: E402

HEADER = "REPORTED: criteria at "
CELL = 160
LIVE_RUNS = 4
FEW_HUNKS = 4  # a file with more hunks is reverted whole, then by halves
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


def git_output(*argv, cwd=None):
    return subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True).stdout.strip()


def read_file(file):
    try:
        return file.read_text()
    except (OSError, UnicodeDecodeError) as e:
        sys.exit(f"run-criteria: could not read {file}: {e}")


def read_task(source):
    if source == "-":
        task = json.load(sys.stdin)  # a comment the board adapter has not marked, as a board's own listing prints it, gets its mark here
        return {**task, "comments": [{**comment, "trusted": comment.get("trusted", board.trusted(comment))} for comment in task.get("comments", [])]}
    number = decisions.task_number(source)
    if number is None:
        sys.exit(f"run-criteria: {source} is no file here, and no task's number or url")
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


class Memory:
    """The `pass` of each check on one tree of files, kept in the git common dir's `teamwork-passes/`, so a check whose files did not change runs once for every session of the repository."""

    def __init__(self, root, tree, scope, fresh):
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


def git_state(root):
    """The commit, branch and index state of ROOT as text, since a check may read them and equal files do not make them equal."""
    status = subprocess.run(["git", "status", "--porcelain=v1", "-z"], cwd=root, capture_output=True, text=True).stdout
    return "\0".join([git_output("rev-parse", "HEAD", cwd=root), git_output("symbolic-ref", "-q", "HEAD", cwd=root), status])


def tree_of_files(root):
    """The git tree of every file in ROOT not ignored, as a sha, so equal files give an equal tree whoever wrote them; empty when git cannot say."""
    with tempfile.TemporaryDirectory(prefix="run-criteria-index-") as folder:
        environment = {**os.environ, "GIT_INDEX_FILE": str(pathlib.Path(folder, "index"))}
        added = subprocess.run(["git", "add", "-A"], cwd=root, env=environment, capture_output=True)
        written = subprocess.run(["git", "write-tree"], cwd=root, env=environment, capture_output=True, text=True)
        return written.stdout.strip() if not added.returncode and not written.returncode else ""


def execute(command, detail, cwd, timeout, live):
    """(status, output) of a check, its live first stage replayed from a saved transcript when it has one."""
    stages = criteria_check.live_stage(detail)
    return live.run(*stages, criteria_check.watched(detail), cwd, timeout) if stages else run(command, cwd, timeout)


def recalled(memory, detail, command, cwd, timeout, live, passes):
    """(status, output) of a check from MEMORY when it passed on these files, else from running it, kept when PASSES(status, output) holds."""
    found = memory.recall(detail) if memory else None
    if found:
        return found
    status, out = execute(command, detail, cwd, timeout, live)
    if memory and passes(status, out):
        memory.keep(detail, status, out)
    return status, out


def base_row(label, kind, name, detail, archive, timeout, live, memory):
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
    if status is not None and out == quoted:
        # what is left of the check once its file scans do nothing still prints the passing output on base, so a scan alone fails it there
        bare = criteria_check.without_scans(command)
        if bare and criteria_check.verdict(test, *run(bare, archive, timeout)) == "pass":
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
    with tempfile.TemporaryDirectory(prefix="run-criteria-base-") as copy:
        exported = subprocess.Popen(["git", "archive", ref], cwd=root, stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", copy], stdin=exported.stdout, check=True)
        if exported.wait():
            sys.exit(f"run-criteria: could not export {ref}; fetch it first")
        return [base_row(str(n), *criterion, copy, timeout, live, memory) for n, criterion in enumerate(rows, 1)]


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
        return None, f"timed out after {timeout} s; give a longer limit with --timeout <s>"


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


def added_conditions(file, line, patch, text):
    """Byte spans of the tests of the `if` and `elif` statements a Python hunk adds in TEXT, its first added line being LINE."""
    added = range(line, line + sum(1 for each in patch.split("\n@@", 1)[-1].splitlines()[1:] if each.startswith("+")))
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    starts = [0]
    for each in text.encode().splitlines(keepends=True):
        starts.append(starts[-1] + len(each))
    return sorted((node.lineno, starts[node.test.lineno - 1] + node.test.col_offset, starts[node.test.end_lineno - 1] + node.test.end_col_offset)
                  for node in ast.walk(tree) if isinstance(node, ast.If) and node.lineno in added)


def run_per_hunk(options, task, root, live):
    """Names each hunk of the change whose revert alone turns no passing row into another result; exit 1 on one."""
    ref = base_ref(options.ref)
    diff = subprocess.run(["git", "-c", "core.quotepath=false", "diff", "--no-renames", "--src-prefix=a/", "--dst-prefix=b/", "-U0", f"{ref}...HEAD"], cwd=root, capture_output=True).stdout
    hunks = split_hunks(diff.decode("latin-1"))
    found = [(str(n), criterion) for n, criterion in enumerate(task_criteria(task), 1)]

    def results(copy):
        """Label to result of each row in COPY; a git check, which the export cannot run, never passes."""
        return {label: row(label, *criterion, copy, options.timeout, live)[2] for label, criterion in found}

    with tempfile.TemporaryDirectory(prefix="run-criteria-hunks-") as copy:
        exported = subprocess.Popen(["git", "archive", "HEAD"], cwd=root, stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", copy], stdin=exported.stdout, check=True)
        if exported.wait():
            sys.exit("run-criteria: could not export HEAD")
        at_head = results(copy)
        failing = [label for label, result in at_head.items() if result == "fail"]
        if failing:
            print(*[f"{label}: fails at the head: make it pass first, since a hunk cannot be judged by a criterion that does not" for label in failing], sep="\n")
            print(live.report(), end="")
            return 1
        held = {label for label, result in at_head.items() if result == "pass"}
        unneeded, conditions, unjudged = [], 0, []

        def survives(group):
            """True when no passing row changes with every hunk of GROUP, all of one file or link, reverted together."""
            path = pathlib.Path(copy, group[0][0])
            link = os.readlink(path) if path.is_symlink() else None
            kept = path.read_bytes() if link is None and path.is_file() else None
            mode = path.stat().st_mode if kept is not None else None
            before = os.fsencode(link) + b"\n" if link is not None else kept
            text = take_back(before.decode("latin-1") if before is not None else "", [patch for _, _, patch in group])
            made = [folder for folder in reversed(path.parents) if not folder.exists()]
            path.unlink(missing_ok=True)
            if text or "\nnew file mode " not in group[0][2]:
                path.parent.mkdir(parents=True, exist_ok=True)
                if "120000" in group[0][2].split("\n@@", 1)[0]:
                    os.symlink(text.rstrip("\n").encode("latin-1"), path)
                else:
                    path.write_bytes(text.encode("latin-1"))
                    if mode is not None:
                        path.chmod(stat.S_IMODE(mode))
            still = {label for label, result in results(copy).items() if result == "pass"}
            path.unlink(missing_ok=True)
            for folder in made[:1]:
                shutil.rmtree(folder)
            if link is not None:
                os.symlink(link, path)
            elif kept is not None:
                path.write_bytes(kept)
                path.chmod(stat.S_IMODE(mode))
            return held <= still

        by_file = {}
        for hunk in hunks:
            by_file.setdefault(hunk[0], []).append(hunk)
        for file, group in by_file.items():
            if len(group) > FEW_HUNKS and not options.each:
                # a file of many hunks, such as a built page, is judged whole and by halves, so the rest of it is judged only when --each asks
                halves = [] if survives(group) else [group[:len(group) // 2], group[len(group) // 2:]]
                passing = [half for half in halves if survives(half)]
                alone = [hunk for half in passing for hunk in half] if halves else group
                failing = [half for half in halves if half not in passing]
                if failing:
                    unjudged.append((file, sum(len(half) for half in failing)))
            else:
                alone = [hunk for hunk in group if survives([hunk])]
            unneeded += [f"{file}:{line}: unneeded hunk: a hunk whose revert fails no criterion is unneeded, or its criterion is vacuous" for _, line, _ in alone]
            path = pathlib.Path(copy, file)
            text = path.read_text() if file.endswith(".py") and path.is_file() else ""
            for _, line, patch in (hunk for hunk in group if hunk not in alone):
                for number, start, end in added_conditions(file, line, patch, text):
                    data = text.encode()
                    path.write_bytes(data[:start] + b"False" + data[end:])
                    still = {label for label, result in results(copy).items() if result == "pass"}
                    path.write_text(text)
                    conditions += 1
                    if held <= still:
                        unneeded.append(f"{file}:{number}: unneeded condition: no criterion reaches this branch, so drop it or make a criterion refuse through it")
    print(f"hunks: {len(hunks)} reverted against {ref}, {conditions} conditions made False, {len(unneeded)} unneeded")
    print(*unneeded, sep="\n")
    print(*[f"{file}: {count} hunks not judged one by one, since reverting them together fails a criterion; --each judges each" for file, count in unjudged], sep="\n")
    print(live.report(), end="")
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


def main(args):
    parser = usage_parser.parser(__doc__)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--base", "--main", action="store_true")
    parser.add_argument("--hunks", action="store_true")
    parser.add_argument("--each", action="store_true")
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--ref")
    parser.add_argument("--pass", dest="samples", action="append", default=[], metavar="N=FILE")
    parser.add_argument("task")
    options = parser.parse_args(args)
    file = pathlib.Path(options.task)
    task = {"body": read_file(file), "comments": []} if file.is_file() else runnable(read_task(options.task))
    root = git_output("rev-parse", "--show-toplevel") or "."
    if options.samples:
        return run_with_samples(options, task, root)
    if options.hunks and options.base:
        usage_parser.refuse(__doc__)
    if options.hunks:
        return run_per_hunk(options, task, root, Live(root, task))
    if options.base:
        return run_against_base(options, task, root, Live(root, task))
    return run_at_head(options, task, root, Live(root, task))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
