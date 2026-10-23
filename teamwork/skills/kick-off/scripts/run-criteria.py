#!/usr/bin/env python3
"""usage: run-criteria.py [--timeout <s>] [--base [--ref <ref>]] <task | body-file | ->

Run each `[check]` of a task's Definition of done at the head, in the worktree's root, then each `[check]` of an
optional `.teamwork/default-criteria.md` there as `standing`, and print a table to comment on the task, which the
judge reads instead of running each check again. `-` reads `gh issue view <task> --json body,comments` output.

A row is `pass` or `fail` by the output the criterion says it `prints`, or the status it `exits`; `unclear` when the
script cannot decide it, such as a `<placeholder>`, two commands or an expected text found inside other output, which the
judge runs; `judged` for a `[score]`. A timeout is a `fail`. Exit 1 on any `fail`. A `BLOCKED due: <name>` line follows
when a criterion fails with the output it had in an earlier table on the task: ask your manager by `BLOCKED:`, since
it has failed twice the same way.

`--base` runs each `[check]` in an export of the base instead, `--ref` or else `origin/HEAD`, and prints `base ok` when
its output equals the text quoted after `on base` (or `on main`, in tasks filed before), `wrong base` when it differs,
`unclear` when the quote is not one value; exit 1 on any `wrong base`; an `exits` or `more` check, a git check (the
export has no `.git`) and a check with a placeholder are `unclear`. The output is compared whole. It never fetches: run `git fetch` first. A body file reads criteria before the task exists, so run it before the first judge."""
import argparse
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import github_rest  # noqa: E402
import issue_state  # noqa: E402

HEADER = "REPORTED: criteria at "
PLACEHOLDER = re.compile(r"<[A-Za-z][\w .-]*>")
CELL = 160
# a code span, or an empty one, which SPAN skips
# an empty one only where the clause goes on to its end, so a padded `` echo `x` `` stays one span
SPANS = re.compile(r"(?<!`)``(?=\s*(?:$|[;.,)]|\bon\b|\bwhen\b))|" + issue_state.SPAN.pattern)
# a remark in parentheses is hidden too, since it may hold a `,` or `;`
HIDDEN = re.compile(SPANS.pattern + r"|\([^()]*\)")
NOTE = re.compile(r"\s*\0(\d+)\0$")


def hide(text):
    """(text with each code span a token no clause split matches inside, the spans), so a `when` or `;` in a quoted value never splits."""
    kept = []

    def stash(m):
        kept.append(m.group())
        return f"\0{len(kept) - 1}\0"
    return HIDDEN.sub(stash, text), kept


def show(text, kept):
    return re.sub(r"\0(\d+)\0", lambda m: kept[int(m.group(1))], text)


def is_remark(text):
    """A parenthesis that only explains; one with a code span or an `or` may add a second accepted value, so it stays."""
    return text.lstrip().startswith("(") and "`" not in text and not re.search(r"\bor\b", text)


def clause_of(rest):
    """(first clause of text after `prints` or `on base` with a remark in parentheses cut, the hidden text after it, the hidden spans)."""
    hidden, kept = hide(rest)
    clause, *parts = re.split(r"([;.](?:\s|$)|,\s+(?!\0)|\bwhen\b|\bon (?:base|main)\b)", hidden)
    clause = clause.strip()
    while (m := NOTE.search(clause)) and is_remark(kept[int(m.group(1))]):
        clause = clause[:m.start()]
    return show(clause, kept).strip(), "".join(parts), kept


def read_task(source):
    if source == "-":
        return json.load(sys.stdin)
    raw = github_rest.get(f"repos/issues/{source}", paginate=False)
    found = github_rest.get(f"repos/issues/{source}/comments?per_page=100")
    if raw is None or found is None:
        sys.exit(f"run-criteria: could not read task {source} from GitHub")
    return {"body": raw["body"] or "", "comments": [github_rest.comment(c) for c in found]}


def expectation(detail):
    """(command, test) of a `[check]`'s details, test ('prints', text), ('more', n), ('exits', n) or (None, why) when undecidable."""
    spans = list(SPANS.finditer(detail))
    if not spans or spans[0].group(2) is None:
        return None, (None, "no command")
    command, after = spans[0].group(2), detail[spans[0].end():]
    if detail[:spans[0].start()].strip():
        return command, (None, "words before the command")
    verb = re.search(r"\b(prints|exits)\b", after)
    if not verb or any(s.start() < spans[0].end() + verb.start() for s in spans[1:]):
        return command, (None, "two commands" if verb else "no prints or exits")
    if PLACEHOLDER.search(command) or "..." in command or "…" in command:
        return command, (None, "placeholder in the command")
    rest = after[verb.end():]
    # the expected text runs to the clause's end, so a second value such as `a` then `b` or `a`, `b` reads as undecidable
    clause, after_clause, kept = clause_of(rest)
    # a further command before the base's output is a second condition, which this value alone would pass; a `when` explains
    tail = re.split(r"\bon (?:base|main)\b", after_clause)[0]
    tail = show(re.sub(r"\bwhen\b.*?(?:[;.](?:\s|$)|$)", "", tail, flags=re.S), kept)
    if re.match(r"[,;]\s*and\b", tail) or any(re.search(r"\s", m.group(2)) for m in issue_state.SPAN.finditer(tail)):
        return command, (None, "more than one condition")
    if verb.group(1) == "exits":
        code = re.fullmatch(r"`?(\d+)`?", clause)
        return command, ("exits", int(code.group(1))) if code else (None, "expected status not one value")
    found = list(issue_state.SPAN.finditer(clause))
    span = found[0] if len(found) == 1 and found[0].span() == (0, len(clause)) else None
    more = re.fullmatch(r"`?(\d+)`? or more", clause)
    if clause == "nothing":
        return command, ("prints", "")
    if more:
        return command, ("more", int(more.group(1)))
    if clause == "``":
        return command, ("prints", "")
    if span and not PLACEHOLDER.search(span.group(2)):
        return command, ("prints", span.group(2))
    if re.fullmatch(r"[\w-]+", clause):
        return command, ("prints", clause)
    return command, (None, "expected output not one value")


def base_quote(detail):
    """The one value quoted after `on base` in a `[check]`'s details, or None when it is not one value."""
    # tasks filed before the base was named quote `on main`
    hidden, kept = hide(detail)
    _, found, rest = (re.split(r"\b(on (?:base|main))\b", hidden, maxsplit=1) + ["", ""])[:3]
    clause = clause_of(show(rest, kept))[0]
    clause = re.sub(r"^(?:it\s+)?prints\s+", "", clause)
    spans = list(issue_state.SPAN.finditer(clause))
    if len(spans) == 1 and spans[0].span() == (0, len(clause)):
        return spans[0].group(2)
    if clause in ("nothing", "``"):
        return ""
    return clause if found and re.fullmatch(r"[\w-]+", clause) else None


def base_row(label, kind, name, detail, archive, timeout):
    command, test = expectation(detail)
    quoted = base_quote(detail)
    # an `exits` or `more` check is decided by status or count, which the quoted text is not
    if kind != "check" or test[0] != "prints" or quoted is None:
        return label, name, "unclear", "not run: not a `prints` check with one value after `on base`"
    status, out = run(command, archive, timeout)
    if "not a git repository" in out:
        return label, name, "unclear", "git needs a checkout, which the export lacks"
    return label, name, "base ok" if status is not None and out == quoted else "wrong base", cell(out)


def base_ref(ref):
    found = ref or subprocess.run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], capture_output=True,
                                  text=True).stdout.strip()
    return found or sys.exit("run-criteria: origin/HEAD is not set; name the base with --ref")


def run_on_base(root, ref, rows, timeout):
    """Rows of every criterion run in a `git archive` copy of the base, so the head's files never answer."""
    with tempfile.TemporaryDirectory(prefix="run-criteria-base-") as copy:
        tar = subprocess.Popen(["git", "archive", ref], cwd=root, stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", copy], stdin=tar.stdout, check=True)
        if tar.wait():
            sys.exit(f"run-criteria: could not export {ref}; fetch it first")
        return [base_row(str(n), *c, copy, timeout) for n, c in enumerate(rows, 1)]


def run(command, cwd, timeout):
    """(exit status or None on a timeout, stdout and stderr as one text)."""
    p = subprocess.Popen(["bash", "-c", command], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         start_new_session=True)
    try:
        out, _ = p.communicate(timeout=timeout)
        return p.returncode, out.strip()
    except subprocess.TimeoutExpired:
        # the check's children share its session, so killing only bash would leave them running
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
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
    command, test = expectation(detail)
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
    for c in task.get("comments", []):
        if issue_state.trusted(c) and c["body"].startswith(HEADER):
            for line in c["body"].splitlines():
                cells = [x.strip() for x in re.split(r"(?<!\\)\|", line)[1:-1]]
                if len(cells) == 4 and cells[2] == "fail":
                    found.setdefault(cells[1], set()).add(cells[3])
    return found


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--timeout", type=int, default=300)
    args.add_argument("--base", "--main", action="store_true")
    args.add_argument("--ref")
    args.add_argument("task")
    a = args.parse_args()
    file = pathlib.Path(a.task)
    task = {"body": file.read_text(), "comments": []} if a.base and file.is_file() else read_task(a.task)
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or "."
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True).stdout.strip()
    if a.base:
        ref = base_ref(a.ref)
        sha = subprocess.run(["git", "rev-parse", "--short", ref], cwd=root, capture_output=True, text=True).stdout.strip()
        rows = run_on_base(root, ref, list(criteria(issue_state.sections(task.get("body")).get("done", ""))), a.timeout)
        print(f"REPORTED: base outputs at {ref} {sha}\n\n| # | criterion | result | output on base |\n| --- | --- | --- | --- |")
        for r in rows:
            print("| " + " | ".join([r[0], r[1].replace("|", "\\|"), r[2], r[3]]) + " |")
        sys.exit(1 if any(r[2] == "wrong base" for r in rows) else 0)
    standing = pathlib.Path(root, ".teamwork", "default-criteria.md")
    rows = [row(str(n), *c, root, a.timeout) for n, c in enumerate(criteria(issue_state.sections(task.get("body")).get("done", "")), 1)]
    rows += [row("standing", *c, root, a.timeout) for c in criteria(standing.read_text())] if standing.exists() else []
    print(f"{HEADER}{head}" + (" with uncommitted changes" if dirty else ""))
    print("\n| # | criterion | result | output |\n| --- | --- | --- | --- |")
    for r in rows:
        print("| " + " | ".join([r[0], r[1].replace("|", "\\|"), r[2], r[3]]) + " |")
    before = earlier_fails(task)
    for _, name, result, out in rows:
        if result == "fail" and out in before.get(name.replace("|", "\\|"), ()):
            print(f"\nBLOCKED due: {name} failed with the same output as in an earlier table; ask your manager by `BLOCKED:`.")
    sys.exit(1 if any(r[2] == "fail" for r in rows) else 0)


main()
