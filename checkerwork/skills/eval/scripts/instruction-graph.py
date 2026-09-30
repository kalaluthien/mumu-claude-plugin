#!/usr/bin/env python3
"""Check a repository's agent-instruction files as a graph of who registers, runs, reads or names whom: each file a
node, each Markdown heading a node of its file. It names each reference to a missing file or section, each instruction
file no root reaches, and each term two term tables define, with no setup.

Roots are what the harness loads by where it sits: `CLAUDE.md`, `AGENTS.md`, `.claude/` settings, skills, agents,
commands and rules, and in each plugin folder (one holding `.claude-plugin/plugin.json`) its manifest, hooks,
monitors, agents, skills, commands, eval cases and tests. Instruction files are the files of `.claude/` and of each
plugin folder, `tests/` and `evals/` left out; a document they link is read for references too. A reference in or to
`evals/` is never reported, since an eval prompt names example files. A term table is a Markdown table whose first
header cell is one of TERM_HEADERS, or any table under a heading holding one of GLOSSARY.

An optional `.instruction-graph.json` at the repository's root adds `roots` and `ignore` globs and `outside` names.

usage: instruction-graph.py [<path>] [--edges]; exits 1 on a finding.
"""
import io
import json
import pathlib
import posixpath
import re
import subprocess
import sys
import tokenize

CONFIG = ".instruction-graph.json"
PLUGIN_ROOT = "${CLAUDE_PLUGIN_ROOT}"
PLUGIN_ROOTS = (".claude-plugin/plugin.json", "hooks/hooks.json", "monitors/monitors.json", ".mcp.json", "agents/*.md",
                "commands/*.md", "skills/*/SKILL.md", "evals/*/prompt.md", "evals/*/graders/*.md", "tests/test_*.py")
LOADED = {"CLAUDE.md", "AGENTS.md", "CLAUDE.local.md", ".mcp.json"}  # at any depth
REPO_ROOTS = (".claude/settings.json", ".claude/skills/*/SKILL.md", ".claude/agents/*.md", ".claude/commands/*.md",
              ".claude/rules/*.md", ".claude-plugin/marketplace.json")
TERM_HEADERS = {"term", "terms", "keyword", "keywords", "verb", "verbs", "word", "words", "concept", "concepts",
                "용어", "개념", "동사", "키워드", "낱말"}
GLOSSARY = {"glossary", "domain", "terminology", "vocabulary", "용어", "용어집"}
TOKEN = re.compile(r"(?<![\w.$/{}<>~@:*%=+-])(?:\$\{CLAUDE_PLUGIN_ROOT\}/|\$\{?CLAUDE_PROJECT_DIR\}?/)?"
                   r"[\w.@-]+(?:/[\w.@-]+)*/?")
EXT = re.compile(r"\.[A-Za-z][A-Za-z0-9]{0,4}$")
LINK = re.compile(r"!?\[[^\]]*\]\(<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\)(?:'s ([A-Z][a-z]+(?: (?!says|below|above)[a-z]+)?))?"
                  r"|^\s*\[[^\]]+\]:\s*<?([^\s>]+)", re.M)
QUOTED = re.compile(r"\"([A-Z][^\"\n]{1,60})\" (?:below|above)")
SECTION = re.compile(r"(?<=[a-z,] )([A-Z][a-z]+(?: [a-z]+)?) (?:says|below|above)\b")  # `as Filing says`
AFTER = re.compile(r"\s*§ ?([^\s.,;:)]+(?: [^\s.,;:)]+){0,5})")  # `README.md` § Start
IMPORT = re.compile(r"^\s*(?:from (\w+) import|import (\w+))", re.M)


def glob_match(path, pattern):
    """`pathlib` match anchored at the start: `*` stays within one folder."""
    return len(pathlib.PurePosixPath(path).parts) == len(pathlib.PurePosixPath(pattern).parts) and \
        pathlib.PurePosixPath(path).match(pattern)


def listing(root):
    """The files under `root`, relative to it: git's tracked and untracked ones minus what it ignores, or every file
    outside a dot folder when `root` is no git checkout."""
    out = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
                         capture_output=True, text=True)
    if out.returncode == 0:
        return sorted({f for f in out.stdout.splitlines() if (root / f).is_file()})
    rel = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
    return sorted(f for f in rel if not any(s.startswith(".") and s not in (".claude", ".claude-plugin")
                                            for s in f.split("/")[:-1]) and "__pycache__" not in f)


def toplevel(root):
    out = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return pathlib.Path(out.stdout.strip()) if out.returncode == 0 else root


def headings(text):
    """Each Markdown heading's words, fences left out."""
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced and (m := re.match(r"#{1,6} +(.+?)[\s#]*$", line)):
            out.append(m[1])
    return out


def slug(heading):
    """GitHub's anchor for a heading."""
    return re.sub(r"[^\w\- ]", "", heading.replace("`", "").lower()).replace(" ", "-")


def tokens(text):
    """Each path-like word: one holding a `/` or ending in an extension, placeholders and globs left out."""
    for m in TOKEN.finditer(text):
        tok = m[0].rstrip(".")
        after = text[m.start() + len(tok):m.start() + len(tok) + 1]
        tok = tok.removeprefix("@")  # `@AGENTS.md` imports a file into CLAUDE.md
        if after in ("<", "*", "{", "$") or "//" in tok or "..." in tok or tok.startswith("-"):
            continue
        if "/" in tok or EXT.search(tok):
            yield tok


def mentions(source, text):
    """(reference, edge kind) for each file `source` names: a manifest registers its commands; code runs what it
    names in a string, and only names one in a comment or docstring; a document reads a document and runs a command."""
    if source.endswith(".json"):
        text = re.sub(r'\\?"(\$\{?CLAUDE_(?:PLUGIN_ROOT|PROJECT_DIR)\}?)\\?"', r"\1", text)
        return [(t, "registers") for t in tokens(text)]
    if source.endswith(".md"):
        return [(t, "reads" if t.endswith(".md") else "runs") for t in tokens(LINK.sub(" ", text))]
    if source.endswith(".sh") or "." not in pathlib.PurePosixPath(source).name:
        return [(t, "names" if line.lstrip().startswith("#") else "runs")
                for line in text.splitlines() for t in tokens(line)]
    if not source.endswith(".py"):
        return []
    out, start = [], True  # a string that opens a statement is a docstring
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type in (tokenize.STRING, tokenize.COMMENT):
                said = "names" if tok.type == tokenize.COMMENT or start else "runs"
                out += [(t, said) for t in tokens(tok.string)]
            if tok.type not in (tokenize.NL, tokenize.COMMENT):
                start = tok.type in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT)
    except (tokenize.TokenError, SyntaxError):
        pass
    return out


def term_tables(text):
    """(term, line) for each first-column cell of each term table."""
    out, heading, table, fenced = [], "", None, False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        if fenced:
            continue
        if m := re.match(r"#{1,6} +(.+?)[\s#]*$", line):
            heading = m[1]
        if not line.lstrip().startswith("|"):
            table = None
            continue
        first = re.sub(r"[`*]", "", line.strip().strip("|").split("|")[0]).strip().lower()
        if table is None:
            words = set(re.findall(r"\w+", heading.lower()))
            table = first in TERM_HEADERS or bool(words & GLOSSARY)
        elif table and first and not set(first) <= set("-: "):
            out.append((first, n))
    return out


def load_config(top):
    path = top / CONFIG
    return json.loads(path.read_text()) if path.is_file() else {}


def check(root, config=None):
    """(files, sections, edges, findings) of the repository or folder at `root`: edges as (source, kind, target),
    findings as lines, every path relative to `root`."""
    root = pathlib.Path(root).resolve()
    top = toplevel(root)
    config = load_config(top) if config is None else config
    prefix = root.relative_to(top).as_posix() + "/" if root != top else ""
    ignore = config.get("ignore", [])
    tree = [f for f in listing(root) if not any(glob_match(prefix + f, g) or glob_match(f, g) for g in ignore)]
    index = set(tree)
    texts = {}

    def text(f):
        if f not in texts:
            texts[f] = (root / f).read_text(errors="replace")
        return texts[f]

    plugins = sorted({f[:-len(".claude-plugin/plugin.json")] for f in tree if f.endswith(".claude-plugin/plugin.json")},
                     key=len, reverse=True)
    if not plugins and any((p / ".claude-plugin" / "plugin.json").is_file() for p in [root, *root.parents]):
        plugins = [""]

    def plugin_of(f):
        return next((p for p in plugins if f.startswith(p)), None)

    def instruction(f):
        parts = f.split("/")
        if "tests" in parts or "evals" in parts:
            return False
        return plugin_of(f) is not None or ".claude" in parts[:-1]

    candidates = [f for f in tree if instruction(f)]

    def command(f):
        """A script whose opening lines give its own command line, run by hand."""
        name = pathlib.PurePosixPath(f).name
        if not f.endswith((".py", ".sh")) and "/bin/" not in "/" + f:
            return False
        head = "\n".join(text(f).splitlines()[:30])
        return bool(re.search(r"usage:|^\s*" + re.escape(name) + r" [\[<-]", head, re.M))

    def is_root(f):
        plugin = plugin_of(f)
        if plugin is not None and any(glob_match(f[len(plugin):], r) for r in PLUGIN_ROOTS):
            return True
        name, at = pathlib.PurePosixPath(f).name, f.find(".claude")
        return name in LOADED or at >= 0 and (at == 0 or f[at - 1] == "/") and any(
            glob_match(f[at:], r) for r in REPO_ROOTS) or f.startswith(".claude/rules/") or any(
            glob_match(prefix + f, r) or glob_match(f, r) for r in config.get("roots", [])) or command(f)

    roots = {f for f in tree if is_root(f)}
    base = {}
    for f in tree:
        base.setdefault(pathlib.PurePosixPath(f).name, []).append(f)
    skills = {}
    for f in tree:
        if m := re.search(r"(?:^|/)skills/([^/]+)/SKILL\.md$", f):
            skills.setdefault(m[1], []).append(f)
    outside = set(config.get("outside", []))
    sections, edges, findings, scanned = {}, set(), [], set()

    def heads(f):
        if f not in sections:
            sections[f] = headings(text(f)) if f.endswith(".md") and f in index else []
        return sections[f]

    def exists(path):
        return path in index or (root / path).exists()

    def quiet(source, ref):
        return "evals" in source.split("/") or "evals" in ref.split("/") or pathlib.PurePosixPath(ref).name in outside

    def near(source, hits):
        """The one of `hits` closest to `source`: under its folder, then under its plugin."""
        if len(hits) == 1:
            return hits[0]
        for scope in (posixpath.dirname(source), plugin_of(source)):
            if scope is not None:
                inside = [h for h in hits if h.startswith(scope + "/" if scope else "")]
                if len(inside) == 1:
                    return inside[0]
        return None

    def resolve(source, ref, strict):
        """(target, missing): the file `ref` names from `source`, None when it names none in the tree; missing is
        True for a reference that should resolve and does not."""
        here = posixpath.dirname(source)
        for var, at in ((PLUGIN_ROOT + "/", plugin_of(source)), ("${CLAUDE_PROJECT_DIR}/", "/"),
                        ("$CLAUDE_PROJECT_DIR/", "/")):
            if ref.startswith(var):
                if at is None:
                    return None, False
                path = ref[len(var):]
                if at == "/":
                    rel = posixpath.relpath(path, prefix) if prefix and path.startswith(prefix) else path
                    return (rel if rel in index else None), not (top / path).exists()
                path = posixpath.normpath(posixpath.join(at, path)) if at else path
                return (path if path in index else None), not exists(path)
        ref = ref.rstrip("/").removeprefix("./")
        if ref.startswith("/"):
            rel = ref.lstrip("/")
            return (rel if rel in index else None), strict and not (top / rel).exists()
        if strict or ref.startswith("../"):
            path = posixpath.normpath(posixpath.join(here, ref))
            if path.startswith("../"):
                return None, not (root / path).exists()
            return (path if path in index else None), not exists(path)
        if "/" not in ref:
            return near(source, base.get(ref, [])), False
        bases = [b for b in dict.fromkeys((here, plugin_of(source), "")) if b is not None]
        for b in bases:
            path = posixpath.normpath(posixpath.join(b, ref))
            if path in index:
                return path, False
            if exists(path):
                return None, False
        if (top / ref).exists():
            return None, False
        if target := near(source, [f for f in tree if f.endswith("/" + ref)]):  # `scripts/verify.sh` of a skill
            return target, False
        first = ref.split("/")[0]
        known = any((root / b / first).is_dir() for b in bases)
        return None, bool(EXT.search(ref)) and known and first not in (".", "..")

    def section(source, target, name, how):
        """A heading reference: a finding when `target` has no heading `name` (words) or anchor `name`."""
        if how == "anchor":
            if any(slug(h) == name for h in heads(target)):
                edges.add((source, "reads", f"{target}#{name}"))
            else:
                findings.append(f"dangling section: {source} links {target}#{name}")
            return
        words = name.split(" ")
        hit = next((h for k in range(len(words), 0, -1) for h in heads(target)
                    if h.lower() == " ".join(words[:k]).lower()), None)
        if hit is None and how == "prefix":
            hit = next((h for h in heads(target) if h.lower().startswith(name.lower())), None)
        if hit is None:
            findings.append(f"dangling section: {source} names {target}'s {name}")
        else:
            edges.add((source, "reads", f"{target}#{hit}"))

    def scan(source):
        scanned.add(source)
        body = text(source)
        md = source.endswith(".md")
        if md:
            for m in LINK.finditer(body):
                ref = m[1] or m[3]
                if re.match(r"[a-z][\w+.-]*:", ref) or ref.startswith(("<", "{")) or "$" in ref.split("#")[0][1:]:
                    continue
                path, _, anchor = ref.partition("#")
                if quiet(source, path) or path and not re.search(r"[./]", path):  # `[text](url)`
                    continue
                target, missing = (source, False) if not path else resolve(source, path, True)
                if missing:
                    findings.append(f"dangling link: {source} links {ref}")
                    continue
                if target:
                    if target != source:
                        edges.add((source, "reads" if target.endswith(".md") else "runs", target))
                    if target.endswith(".md"):
                        if anchor:
                            section(source, target, anchor, "anchor")
                        if m[2]:
                            section(source, target, m[2], "words")
                tail = AFTER.match(body, m.end())
                if target and tail and target.endswith(".md"):
                    section(source, target, tail[1], "words")
        for ref, said in mentions(source, body):
            if quiet(source, ref) or pathlib.PurePosixPath(ref).name.startswith("<"):
                continue
            target, missing = resolve(source, ref, False)
            if missing:
                findings.append(f"dangling reference: {source} names {ref}")
            elif target and target != source:
                edges.add((source, said, target))
        if md:
            here = posixpath.dirname(source) + "/" if "/" in source else ""
            for m in re.finditer(r"`([\w-]+)`", body):  # a file of its folder named bare: `Brewfile`, `chart`
                hits = [f for f in tree if f.startswith(here) and m[1] in (pathlib.PurePosixPath(f).name,
                                                                           pathlib.PurePosixPath(f).stem)]
                if len(hits) == 1 and hits[0] != source:
                    edges.add((source, "reads", hits[0]))
            for m in re.finditer(r"`([^`\s]+\.md)` § ?", body):
                target, _ = resolve(source, m[1], False)
                if target and (tail := AFTER.match(body, m.end() - 2)):
                    section(source, target, tail[1], "words")
            if skills:
                aliased = r"\b(" + "|".join(map(re.escape, skills)) + r")(?: skill)?'s ([A-Z][a-z]+)\b"
                for m in re.finditer(aliased, body):
                    if (target := near(source, skills[m[1]])) is not None:
                        section(source, target, m[2], "words")
            for m in QUOTED.finditer(body):
                section(source, source, m[1], "words")
            for m in SECTION.finditer(body):
                if any(h.startswith(m[1]) for f in scanned | {source} for h in heads(f)):
                    continue
                if not any(h.startswith(m[1]) for f in index if f.endswith(".md") and f in candidates
                           for h in heads(f)):
                    findings.append(f"dangling section: {source} names {m[1]}")
        if source.endswith(".py"):
            plugin = plugin_of(source)
            for m in IMPORT.finditer(body):
                name = m[1] or m[2]
                hits = [f for f in base.get(name + ".py", []) if plugin is None or f.startswith(plugin)]
                if len(hits) == 1 and hits[0] != source:
                    edges.add((source, "runs", hits[0]))

    for f in candidates + sorted(roots - set(candidates)):
        if "tests" not in f.split("/"):
            scan(f)
    reached, todo = set(roots), list(roots)
    while todo:
        at = todo.pop()
        if at not in scanned and at.endswith(".md") and "tests" not in at.split("/"):
            scan(at)  # a document an instruction file links
        for s, k, t in sorted(edges):
            if s == at and k != "names" and (t := t.split("#")[0]) not in reached:
                reached.add(t)
                todo.append(t)
    findings += [f"orphan: {f}, which no root reaches" for f in candidates if f not in reached]
    defined = {}
    for f in sorted(scanned):
        if f.endswith(".md"):
            for term, _ in term_tables(text(f)):
                defined.setdefault(term, []).append(f)
    findings += [f"term defined twice: {t} ({', '.join(dict.fromkeys(fs))})"
                 for t, fs in defined.items() if len(fs) > 1]
    return tree, {f: s for f, s in sections.items() if s}, sorted(edges), list(dict.fromkeys(findings))


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    tree, sections, edges, findings = check(pathlib.Path(args[0] if args else "."))
    if "--edges" in argv:
        print(f"nodes: {len(tree)} files, {sum(len(s) for s in sections.values())} sections; edges: {len(edges)}")
        for kind in ("registers", "runs", "reads", "names"):
            rows = [(s, t) for s, k, t in edges if k == kind]
            print(f"\n{kind} ({len(rows)}):")
            for s, t in rows:
                print(f"  {s} -> {t}")
        print()
    print(f"findings ({len(findings)}):")
    for f in findings:
        print(f"  {f}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
