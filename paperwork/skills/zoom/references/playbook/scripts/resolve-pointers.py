#!/usr/bin/env python3
"""zoom: resolve a Schema document's metadata pointers against a repository at one commit.

  resolve-pointers.py evidence doc.json --root DIR --sha SHA
      each `meta.evidence` pointer must be `path:line` or `path:line-line` inside that file at SHA; a url or a sha
      counts as unresolved, since only a line can be read back. Prints `evidence: <n> resolved, <k> unresolved`.
  resolve-pointers.py constraints doc.json --root DIR --sha SHA
      each `meta.constraint` `<path>#<rule>` must name a bold rule (`**Rule name**`, matched as `rule-name` too) in
      that file at SHA. Prints `constraints: <n> traced, <k> untraced`.
  resolve-pointers.py faults doc.json --root DIR --sha SHA
      each `meta.note` written `<Word>: <text>` is a fault; it is named when <Word> is Missing, Illegal, Redundant or
      Overloaded and its element's evidence all resolves. Prints `faults: <n> named, <k> unresolved`.
  resolve-pointers.py drift doc.json --root DIR --sha SHA [--to NEW]
      each `meta.evidence` `path:line` pointer read at SHA is `changed` when a commit up to NEW (HEAD by default)
      touched one of its lines, or `gone` when its file is not at NEW; a line that only moved stays unchanged. Prints
      `drift: <n> unchanged, <k> changed`, `gone` counted as changed; a url or a sha is skipped, and a `path:line`
      that does not resolve at SHA is printed `unresolved` and fails the run, since a wrong SHA or root reads as no
      drift.

Each failing pointer is printed above the count. Exit status 0 when the count is 1 or more and nothing failed, 1
otherwise, 2 on a usage error.
"""
import json
import re
import subprocess
import sys

FAULTS = ("Missing", "Illegal", "Redundant", "Overloaded")


def metas(x, path="$"):
    """(path, meta) for every element of the document that carries metadata."""
    if isinstance(x, dict):
        if isinstance(x.get("meta"), dict):
            yield path, x["meta"]
        for k, v in x.items():
            yield from metas(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from metas(v, f"{path}[{i}]")


class Repo:
    def __init__(self, root, sha):
        self.root, self.sha, self.cache = root, sha, {}

    def text(self, path):
        if path not in self.cache:
            got = subprocess.run(["git", "-C", self.root, "show", f"{self.sha}:{path}"], capture_output=True, text=True)
            self.cache[path] = got.stdout if got.returncode == 0 else None
        return self.cache[path]

    def line(self, pointer):
        """Why a `path:line` pointer does not resolve, or None when it does."""
        m = re.fullmatch(r"([^\s:#]+):([0-9]+)(?:-([0-9]+))?", pointer)
        if not m:
            return "not a path:line"
        text = self.text(m[1])
        if text is None:
            return f"no {m[1]} at {self.sha}"
        last, n = int(m[3] or m[2]), len(text.splitlines())
        return None if 1 <= int(m[2]) <= last <= n else f"{m[1]} has {n} lines"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def evidence(doc, repo):
    # the document's own evidence is the commit it was read at, not a pointer
    ms = [m for where, m in metas(doc) if where != "$"]
    bad = [f"unresolved {p}: {why}" for m in ms for p in m.get("evidence", []) if (why := repo.line(p))]
    good = sum(len(m.get("evidence", [])) for m in ms) - len(bad)
    return bad, f"evidence: {good} resolved, {len(bad)} unresolved", good


def constraints(doc, repo):
    bad, good = [], 0
    for _, m in metas(doc):
        for c in m.get("constraint", []):
            path, _, rule = c.partition("#")
            text = repo.text(path)
            names = {slug(b) for b in re.findall(r"\*\*([^*]+)\*\*", text or "")}
            if slug(rule) in names:
                good += 1
            else:
                bad.append(f"untraced {c}: " + (f"no {path} at {repo.sha}" if text is None else f"no bold rule {rule} in {path}"))
    return bad, f"constraints: {good} traced, {len(bad)} untraced", good


def faults(doc, repo):
    bad, good = [], 0
    for where, m in metas(doc):
        word = re.match(r"([A-Z][a-z]+): ", m.get("note", ""))
        if not word:
            continue
        if word[1] not in FAULTS:
            bad.append(f"unresolved {where}: {word[1]} is none of {', '.join(FAULTS)}")
        elif not m.get("evidence"):
            bad.append(f"unresolved {where}: a {word[1]} fault with no evidence")
        elif why := next((f"{p}: {w}" for p in m["evidence"] if (w := repo.line(p))), None):
            bad.append(f"unresolved {where}: {why}")
        else:
            good += 1
    return bad, f"faults: {good} named, {len(bad)} unresolved", good


def touched(root, sha, to, path):
    """The lines of `path` at `sha` that the diff to `to` removes or replaces, or None when `path` is gone at `to`."""
    if subprocess.run(["git", "-C", root, "cat-file", "-e", f"{to}:{path}"], capture_output=True).returncode:
        return None
    diff = subprocess.run(["git", "-C", root, "diff", "-U0", sha, to, "--", path], capture_output=True, text=True).stdout
    lines = set()
    for start, count in re.findall(r"^@@ -([0-9]+)(?:,([0-9]+))? ", diff, re.M):
        n = 1 if count == "" else int(count)
        # a pure insertion (count 0) lands between two lines, so it touches the one above it
        lines |= set(range(int(start), int(start) + n)) if n else {int(start)}
    return lines


def drift(doc, repo, to):
    bad, unresolved, good = [], [], 0
    for _, m in metas(doc):
        for p in m.get("evidence", []):
            if why := repo.line(p):
                if why != "not a path:line":
                    unresolved.append(f"unresolved {p}: {why}")
                continue
            path, a, b = re.fullmatch(r"([^\s:#]+):([0-9]+)(?:-([0-9]+))?", p).groups()
            hit = touched(repo.root, repo.sha, to, path)
            if hit is None:
                bad.append(f"{p}: gone at {to}")
            elif hit & set(range(int(a), int(b or a) + 1)):
                bad.append(f"{p}: changed by {to}")
            else:
                good += 1
    return unresolved + bad, f"drift: {good} unchanged, {len(bad)} changed", good


def main(args):
    modes = {"evidence": evidence, "constraints": constraints, "faults": faults}
    if len(args) == 8 and args[0] == "drift" and args[6] == "--to":
        to, args = args[7], args[:6]
    elif len(args) == 6 and args[0] == "drift":
        to = "HEAD"
    if args[:1] == ["drift"]:
        modes["drift"] = lambda doc, repo: drift(doc, repo, to)
    if len(args) != 6 or args[0] not in modes or args[2] != "--root" or args[4] != "--sha":
        print(__doc__)
        return 2
    try:
        doc = json.load(open(args[1], encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"{args[1]}: {e}", file=sys.stderr)
        return 2
    bad, count, good = modes[args[0]](doc, Repo(args[3], args[5]))
    print("\n".join(bad + [count]))
    return 0 if good and not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
