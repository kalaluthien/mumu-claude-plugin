#!/usr/bin/env python3
"""Print a judge's verdict for the classes of its gaps, or whether a fix made after an approval needs another judge.

usage: pick-verdict.py --gaps [<class>...]
usage: pick-verdict.py --since <sha> [--ref <ref>]

`--gaps` takes the class of each gap the round found: `code-fault` (the code does what its task or callers do not expect),
`failed-scenario` (a scenario or probe fails at the head, or passes at the base), `not-run` (a check approval rests on did not run),
`fixture-gap` (a surviving mutant or an input no criterion tries), `document`, `form`, `scope`, `release` or `other` (a gap none of these names). It prints `fix` when any is
one of the first three, else `approve` and, with a gap, a line telling the judge to list them for the worker.
`--since` lists the files the head changes against <sha>, the head a judge approved, committed or not, from any folder of the
repository, a moved file under both its names; when the head was rebased, so <sha> is not its ancestor, only the files whose patch from
the merge base with `--ref` (default `main`) differs from that file's patch at <sha>, so a file main gained is never named. It prints
`merge` when each is a document (`*.md`), a file under a `fixtures/` folder or a plugin's `plugin.json` that differs in its `version`
alone, else `judge again` with the other files and the other way: merge <sha> as approved and file each such fix as a task.
Exits 0 after a verdict, 1 naming the cause when git cannot read <sha> or <ref>, 2 with this text for a class it does not know or a call it
cannot read. Standard library only, Python 3.9."""

import fnmatch
import json
import pathlib
import subprocess
import sys

BLOCKING = ("code-fault", "failed-scenario", "not-run")
LISTED = ("fixture-gap", "document", "form", "scope", "release", "other")
# what a fix of a listed gap may change with no judge reading it: a soft gap's fix lands here, and a later fault was made elsewhere
UNJUDGED = ("*.md", "fixtures/*", "*/fixtures/*")
MANIFEST = "*/.claude-plugin/plugin.json"


def git(root, *words):
    return subprocess.run(["git", "-C", root, "-c", "core.quotepath=false", *words], capture_output=True, text=True)


def changed_files(root, sha):
    """The files the head and the work tree of the repository at ROOT change against SHA, each from ROOT."""
    listed = git(root, "diff", "--name-only", "--no-renames", sha, "--")
    if listed.returncode:
        sys.exit(f"pick-verdict: git cannot read {sha}: {listed.stderr.strip()}")
    return sorted(set(listed.stdout.splitlines() + git(root, "ls-files", "--others", "--exclude-standard").stdout.splitlines()))


def patches(root, *words):
    """{file: its patch} of `git diff WORDS`, without the index and hunk lines, which a rebase moves while the change stays the same."""
    found = {}
    for part in git(root, "diff", "--no-renames", "--src-prefix=a/", "--dst-prefix=b/", *words, "--").stdout.split("\ndiff --git "):
        lines = part.removeprefix("diff --git ").split("\n")
        if lines[0]:
            found[lines[0].rsplit(" b/", 1)[-1]] = [line for line in lines[1:] if not line.startswith(("index ", "@@"))]
    return found


def moved_files(root, sha, ref):
    """The files whose patch from the head's merge base with REF, work tree included, differs from their patch at SHA from its fork point."""
    fork = git(root, "merge-base", sha, "HEAD").stdout.strip()
    base = git(root, "merge-base", "HEAD", ref).stdout.strip()
    if not fork or not base:
        sys.exit(f"pick-verdict: git cannot read {ref}: no merge base with the head")
    before, after = patches(root, fork, sha), patches(root, base)
    untracked = git(root, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    return sorted({file for file in set(before) | set(after) if before.get(file) != after.get(file)} | set(untracked))


def only_version(root, sha, file):
    """Whether the manifest FILE differs from its text at SHA in nothing but its `version`."""
    try:
        before, after = json.loads(git(root, "show", f"{sha}:{file}").stdout), json.loads(pathlib.Path(root, file).read_text())
        return {**before, "version": None} == {**after, "version": None}
    except (OSError, ValueError, TypeError):
        return False


def unjudged(root, sha, file):
    return any(fnmatch.fnmatchcase(file, pattern) for pattern in UNJUDGED) or fnmatch.fnmatchcase(file, MANIFEST) and only_version(root, sha, file)


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    gaps = args[1:]
    if args[:1] == ["--gaps"] and all(name in BLOCKING + LISTED for name in gaps):
        blocking = sorted({name for name in gaps if name in BLOCKING})
        if blocking:
            print(f"fix\nA gap of class {', '.join(blocking)} sends the change back.")
        elif gaps:
            print(f"approve\nList the {len(gaps)} gaps under `Fix before merging:`; the worker fixes them and runs `pick-verdict.py --since <this head>` before it merges.")
        else:
            print("approve")
        return 0
    ref = dict(zip(args[2::2], args[3::2])).get("--ref", "main")
    if args[:1] == ["--since"] and len(args) in (2, 4) and not any(word.startswith("-") for word in args[1::2]) and args[2:3] in ([], ["--ref"]):
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if top.returncode:
            sys.exit(f"pick-verdict: git cannot read {args[1]}: {top.stderr.strip()}")
        root = top.stdout.rstrip("\n")
        changed = changed_files(root, args[1])
        if git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode:
            sys.exit(f"pick-verdict: git cannot read {ref}: no such commit")
        if git(root, "merge-base", "--is-ancestor", args[1], "HEAD").returncode:
            changed = moved_files(root, args[1], ref)
        judged = [file for file in changed if not unjudged(root, args[1], file)]
        if judged:
            print(f"judge again\nThe fix changes what no judge read: {', '.join(judged)}. Brief the judge with `Last judged: {args[1]}`;"
                  f" or, for a gap the approval listed, merge {args[1]} as approved and file each such fix as a task with the same parent.")
        else:
            print("merge\nThe fix changes only documents, fixtures and the version, so the approval holds.")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
