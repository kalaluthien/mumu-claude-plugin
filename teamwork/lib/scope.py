"""The gates a change needs, from the paths it changes and the mapping kept as data in `gates.json` at the repository's root,
and which of them a recorded pass carries to the head; it runs no command.

A gate is `judge`, a test file or an eval case folder. Each rule of the mapping names path globs and the gates they need;
`*` matches within one path segment, `**` across segments, and `{0}`, `{1}`... in a gate stand for the path's wildcards in
order. A path no rule matches, and the mapping itself, need `every` gate, so no change narrows its own scope; a repository
without the mapping has one gate, the judge.
"""
import re

MAPPING = "gates.json"
JUDGE = "judge"
JUDGE_MODEL = "sonnet"  # a pull request's judge at any size; a plan's runs on judge.md's own model
PASSED = re.compile(r"passed:?\s+([0-9a-f]{40})", re.I)


def pattern(glob):
    """A regex matching a whole path against `glob`, one group per wildcard."""
    return re.compile("".join("(.*)" if t == "**" else "([^/]*)" if t == "*" else re.escape(t) for t in re.split(r"(\*\*|\*)", glob)))


def expand(gates, wildcards, names):
    """Each gate of `gates` with `{n}` filled from `wildcards`, a glob among them expanded over `names`, the gates at the head."""
    found = set()
    for gate in gates:
        gate = gate.format(*wildcards)
        found |= {JUDGE} if gate == JUDGE else {n for n in names if pattern(gate).fullmatch(n)}
    return found


def assigned(path, mapping, names):
    """The gates the mapping assigns to `path`."""
    if mapping is None:
        return {JUDGE}
    if path == MAPPING:
        return expand(mapping["every"], (), names)
    hits = [(rule, m) for rule in mapping["rules"] for glob in rule["paths"] if (m := pattern(glob).fullmatch(path))]
    if not hits:
        return expand(mapping["every"], (), names)
    return set().union(*(expand(rule["gates"], m.groups(), names) for rule, m in hits))


def needs(paths, mapping, names):
    """The gates a change of `paths` needs, sorted with the judge first; an empty change needs every gate."""
    found = set().union(*(assigned(p, mapping, names) for p in paths or [MAPPING]))
    return sorted(found, key=lambda c: (c != JUDGE, c))


def changed(compare):
    """Each path a compare response's diff changes, a rename's old path included; GitHub lists at most 300 files, so a full
    list also names `gates.json`, which needs every gate."""
    files = compare.get("files") or []
    return {p for f in files for p in (f["filename"], f.get("previous_filename")) if p} | ({MAPPING} if len(files) >= 300 else set())


def lines(compare):
    """The changed lines of a compare response's diff: each file's additions plus deletions."""
    return sum(f.get("additions", 0) + f.get("deletions", 0) for f in compare.get("files") or [])


def binary(compare):
    """Each path a compare response's diff changes with no lines to count: added, changed or removed with no patch."""
    return [f["filename"] for f in compare.get("files") or []
            if f.get("status") in ("added", "modified", "removed") and "patch" not in f and not f.get("changes")]


def names(tree):
    """The path of each file and folder in a `git/trees` response: the gates that can run at that commit."""
    if tree.get("truncated"):
        raise RuntimeError("the tree listing is truncated")
    return {entry["path"] for entry in tree["tree"]}


def passes(notes):
    """`{gate: [sha, ...]}`, oldest first, from each note opening `PASSED: <sha>` whose later lines name the gates passed."""
    found = {}
    for note in notes:
        lines = (note.get("body") or "").strip().splitlines()
        if lines and (m := PASSED.fullmatch(lines[0].strip())):
            for line in lines[1:]:
                if gate := line.strip().removeprefix("- ").strip().strip("`"):
                    found.setdefault(gate, []).append(m[1].lower())
    return found


def carried(gate, since, mapping, names):
    """Whether a pass of `gate` at an earlier commit carries across `since`, the paths changed from it to the head, None
    when that commit is not an ancestor of the head."""
    return since is not None and not any(gate in assigned(p, mapping, names) for p in since)
