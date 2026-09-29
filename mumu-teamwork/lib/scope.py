"""The checks a change needs, from the paths it changes and the mapping kept as data in `checks.json` at the repository's root,
and which of them a recorded pass carries to the head; it runs no command.

A check is `judge`, a test file or an eval case folder. Each rule of the mapping names path globs and the checks they need;
`*` matches within one path segment, `**` across segments, and `{0}`, `{1}`... in a check stand for the path's wildcards in
order. A path no rule matches, and the mapping itself, need `every` check, so no change narrows its own scope; a repository
without the mapping has one check, the judge.
"""
import re

MAPPING = "checks.json"
JUDGE = "judge"
PASSED = re.compile(r"passed:?\s+([0-9a-f]{40})", re.I)


def pattern(glob):
    """A regex matching a whole path against `glob`, one group per wildcard."""
    return re.compile("".join("(.*)" if t == "**" else "([^/]*)" if t == "*" else re.escape(t) for t in re.split(r"(\*\*|\*)", glob)))


def expand(checks, wildcards, names):
    """Each check of `checks` with `{n}` filled from `wildcards`, a glob among them expanded over `names`, the checks at the head."""
    found = set()
    for check in checks:
        check = check.format(*wildcards)
        found |= {JUDGE} if check == JUDGE else {n for n in names if pattern(check).fullmatch(n)}
    return found


def assigned(path, mapping, names):
    """The checks the mapping assigns to `path`."""
    if mapping is None:
        return {JUDGE}
    if path == MAPPING:
        return expand(mapping["every"], (), names)
    hits = [(rule, m) for rule in mapping["rules"] for glob in rule["paths"] if (m := pattern(glob).fullmatch(path))]
    if not hits:
        return expand(mapping["every"], (), names)
    return set().union(*(expand(rule["checks"], m.groups(), names) for rule, m in hits))


def needs(paths, mapping, names):
    """The checks a change of `paths` needs, sorted with the judge first; an empty change needs every check."""
    found = set().union(*(assigned(p, mapping, names) for p in paths or [MAPPING]))
    return sorted(found, key=lambda c: (c != JUDGE, c))


def changed(compare):
    """Each path a compare response's diff changes, a rename's old path included; GitHub lists at most 300 files, so a full
    list also names `checks.json`, which needs every check."""
    files = compare.get("files") or []
    return {p for f in files for p in (f["filename"], f.get("previous_filename")) if p} | ({MAPPING} if len(files) >= 300 else set())


def lines(compare):
    """The changed lines of a compare response's diff: each file's additions plus deletions."""
    return sum(f.get("additions", 0) + f.get("deletions", 0) for f in compare.get("files") or [])


def model(lines):
    """The judge's model: `sonnet` for at most 20 changed lines, else `opus`."""
    return "sonnet" if lines <= 20 else "opus"


def names(tree):
    """The path of each file and folder in a `git/trees` response: the checks that can run at that commit."""
    if tree.get("truncated"):
        raise RuntimeError("the tree listing is truncated")
    return {entry["path"] for entry in tree["tree"]}


def passes(notes):
    """`{check: [sha, ...]}`, oldest first, from each note opening `PASSED: <sha>` whose later lines name the checks passed."""
    found = {}
    for note in notes:
        lines = (note.get("body") or "").strip().splitlines()
        if lines and (m := PASSED.fullmatch(lines[0].strip())):
            for line in lines[1:]:
                if check := line.strip().removeprefix("- ").strip().strip("`"):
                    found.setdefault(check, []).append(m[1].lower())
    return found


def carried(check, since, mapping, names):
    """Whether a pass of `check` at an earlier commit carries across `since`, the paths changed from it to the head, None
    when that commit is not an ancestor of the head."""
    return since is not None and not any(check in assigned(p, mapping, names) for p in since)
