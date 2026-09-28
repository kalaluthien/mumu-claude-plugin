"""mumu-teamwork's components as a graph of who registers, runs, reads or names whom: each file a node, each Markdown
heading a node of its file. The check fails on a file no root reaches, a reference to a missing file or section, and a
Domain term defined twice.

Run: uvx pytest mumu-teamwork/tests -q; `python3 mumu-teamwork/tests/test_graph.py` prints the edges and each finding.
"""
import io
import json
import pathlib
import posixpath
import re
import shutil
import sys
import tempfile
import tokenize
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN_ROOT = "${CLAUDE_PLUGIN_ROOT}"
# the harness, pytest and the eval runner find these by where they sit; the owner runs `count-units.py` by hand (#326)
ROOTS = (".claude-plugin/plugin.json", "hooks/hooks.json", "monitors/monitors.json", "agents/*.md", "skills/*/SKILL.md",
         "evals/*/prompt.md", "evals/*/graders/*.md", "tests/test_*.py", "scripts/count-units.py")
# files outside the plugin a file may name
OUTSIDE = {"AGENTS.md", "settings.json", "plugin-authoring.md", "repos.txt", "marketplace.json", "sync.sh"}
# a skill named bare in prose, as `kickoff's Domain`
ALIASES = {"kickoff": "skills/kickoff/SKILL.md", "handoff": "skills/handoff/SKILL.md"}
FILE = re.compile(r"(?<![\w.$/{}-])((?:\$\{CLAUDE_PLUGIN_ROOT\}/)?[\w./-]*[\w-]+\.(?:py|md|sh|json))\b")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)(?:'s ([A-Z][a-z]+(?: (?!says|below|above)[a-z]+)?))?")
ALIASED = re.compile(r"\b(kickoff|handoff)(?: skill)?'s ([A-Z][a-z]+)\b")
SECTION = re.compile(r"(?<=[a-z,] )([A-Z][a-z]+(?: [a-z]+)?) (?:says|below|above|\d\b)")  # `as Filing says`, `at Lead 4`
IMPORT = re.compile(r"^\s*(?:from (\w+) import|import (\w+))", re.M)


def files(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def headings(text):
    """Each Markdown heading's words, fences left out."""
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and (m := re.match(r"#{1,6} +(.+?)\s*$", line)):
            out.append(m[1])
    return out


def mentions(source, text):
    """(file reference, edge kind) for each file `source` names: a manifest registers its commands; code runs what it
    imports or names in a string, and only names one in a comment or docstring; a document reads a document and runs a
    command; a test only names."""
    if source.endswith(".json"):
        text = text.replace('\\"' + PLUGIN_ROOT + '\\"', PLUGIN_ROOT).replace('"' + PLUGIN_ROOT + '"', PLUGIN_ROOT)
        return [(m[1], "registers") for m in FILE.finditer(text)]
    if source.endswith(".md"):
        return [(m[1], "reads" if m[1].endswith(".md") else "runs") for m in FILE.finditer(LINK.sub(" ", text))]
    if source.endswith(".sh"):
        return [(m[1], "names" if line.lstrip().startswith("#") else "runs")
                for line in text.splitlines() for m in FILE.finditer(line)]
    if not source.endswith(".py"):
        return []
    out, start = [], True  # a string that opens a statement is a docstring
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type in (tokenize.STRING, tokenize.COMMENT):
            said = "names" if tok.type == tokenize.COMMENT or start or source.startswith("tests/") else "runs"
            out += [(m[1], said) for m in FILE.finditer(tok.string)]
        if tok.type not in (tokenize.NL, tokenize.COMMENT):
            start = tok.type in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT)
    return out


def graph(root):
    """(files, sections, edges, findings): edges as (source, kind, target), findings as lines."""
    tree = files(root)
    texts = {f: (root / f).read_text(errors="replace") for f in tree}
    sections = {f: headings(t) for f, t in texts.items() if f.endswith(".md")}
    base = {}
    for f in tree:
        base.setdefault(pathlib.PurePosixPath(f).name, []).append(f)
    modules = {pathlib.PurePosixPath(f).stem: f for f in tree if f.startswith("lib/") and f.endswith(".py")}
    edges, findings = set(), []

    def resolve(source, ref):
        """The plugin file `ref` names from `source`, None for one outside it, or "" when it names nothing there."""
        if ref.startswith(PLUGIN_ROOT + "/"):
            path = ref[len(PLUGIN_ROOT) + 1:]
            return path if path in texts else ""
        rel = posixpath.normpath(posixpath.join(posixpath.dirname(source), ref))
        if rel in texts or ref in texts:
            return rel if rel in texts else ref
        name = pathlib.PurePosixPath(ref).name
        if name in OUTSIDE:
            return None
        hits = [f for f in base.get(name, []) if f.endswith(ref)]
        return hits[0] if len(hits) == 1 else None if hits else ""  # a bare name several files share, such as `SKILL.md`

    def section(source, target, name):
        if name not in sections.get(target, []):
            findings.append(f"dangling section: {source} names {target}'s {name}")
        else:
            edges.add((source, "reads", f"{target}#{name}"))

    for source, text in texts.items():
        if source.startswith("tests/"):
            continue
        for m in LINK.finditer(text):
            if re.match(r"https?:", m[1]):
                continue
            target = resolve(source, m[1])
            if target == "":
                findings.append(f"dangling link: {source} links {m[1]}")
            elif target:
                edges.add((source, "reads" if target.endswith(".md") else "runs", target))
                if m[2]:
                    section(source, target, m[2])
        for ref, said in mentions(source, text):
            if pathlib.PurePosixPath(ref).name.startswith(("test_", "<")):
                continue
            target = resolve(source, ref)
            if target == "":
                findings.append(f"dangling reference: {source} names {ref}")
            elif target and target != source:
                edges.add((source, said, target))
        if source.endswith(".md"):
            for m in ALIASED.finditer(text):
                section(source, ALIASES[m[1]], m[2])
            for m in SECTION.finditer(text):
                if not any(m[1] in s for s in sections.values()):
                    findings.append(f"dangling section: {source} names {m[1]}")
                elif m[1] in sections[source]:
                    edges.add((source, "reads", f"{source}#{m[1]}"))
        if source.endswith(".py"):
            for m in IMPORT.finditer(text):
                if (name := m[1] or m[2]) in modules and modules[name] != source:
                    edges.add((source, "runs", modules[name]))
    for source in (f for f in tree if f.startswith("tests/") and f.endswith(".py")):
        for ref, _ in mentions(source, texts[source]):
            if (target := resolve(source, ref)) and target != source:
                edges.add((source, "names", target))
    roots = {f for f in tree if any(pathlib.PurePosixPath(f).match(r) for r in ROOTS)}
    reached, todo = set(roots), list(roots)
    while todo:
        at = todo.pop()
        for s, k, t in edges:
            if s == at and k != "names" and (t := t.split("#")[0]) not in reached:
                reached.add(t)
                todo.append(t)
    findings += [f"orphan: {f}, which no root reaches" for f in tree if f not in reached]
    findings += [f"Domain term defined twice: {t}" for t in duplicates(texts.get("skills/kickoff/SKILL.md", ""))]
    return tree, sections, sorted(edges), findings


def duplicates(skill):
    """Each first-column term the Domain's `term` and `keyword` tables define more than once."""
    domain = re.search(r"^# Domain\n(.*?)(?=^# |\Z)", skill, re.M | re.S)
    seen, twice, table = set(), [], False
    for line in (domain[1] if domain else "").splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if not cells:
            table = False
        elif cells[0] in ("term", "keyword"):
            table = True
        elif table and not set(cells[0]) <= set("-: "):
            if cells[0] in seen:
                twice.append(cells[0])
            seen.add(cells[0])
    return twice


class Graph(unittest.TestCase):
    def seeded(self, change):
        """The findings of a copy of the plugin after `change(copy)`."""
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / "plugin"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__"))
            change(copy)
            return graph(copy)[3]

    def test_the_head_has_no_orphan_dangling_reference_or_duplicate_term(self):
        findings = graph(ROOT)[3]
        print(f"\n{sum(f.startswith('dangling') for f in findings)} dangling references")
        self.assertEqual(findings, [])

    def test_a_seeded_orphan_file_fails(self):
        found = self.seeded(lambda c: (c / "lib" / "unused.md").write_text("# Unused\n"))
        self.assertIn("orphan: lib/unused.md, which no root reaches", found)

    def test_a_reference_to_a_missing_file_fails(self):
        def change(copy):
            path = copy / "agents" / "worker.md"
            path.write_text(path.read_text() + "\nRead `${CLAUDE_PLUGIN_ROOT}/skills/kickoff/references/gone.md`.\n")
        self.assertIn("dangling reference: agents/worker.md names ${CLAUDE_PLUGIN_ROOT}/skills/kickoff/references/gone.md",
                      self.seeded(change))

    def test_a_reference_to_a_missing_section_fails(self):
        def change(copy):
            path = copy / "skills" / "kickoff" / "SKILL.md"
            path.write_text(path.read_text() + "\nSee [lead-goal.md](references/lead-goal.md)'s Gone.\n")
        self.assertIn("dangling section: skills/kickoff/SKILL.md names skills/kickoff/references/lead-goal.md's Gone",
                      self.seeded(change))

    def test_a_domain_term_defined_twice_fails(self):
        def change(copy):
            path = copy / "skills" / "kickoff" / "SKILL.md"
            path.write_text(path.read_text().replace("| project |", "| task | again |\n| project |", 1))
        self.assertIn("Domain term defined twice: task", self.seeded(change))


def main():
    tree, sections, edges, findings = graph(ROOT)
    print(f"nodes: {len(tree)} files, {sum(len(s) for s in sections.values())} sections; edges: {len(edges)}")
    for kind_ in ("registers", "runs", "reads", "names"):
        rows = [(s, t) for s, k, t in edges if k == kind_]
        print(f"\n{kind_} ({len(rows)}):")
        for s, t in rows:
            print(f"  {s} -> {t}")
    print(f"\nfindings ({len(findings)}):")
    for f in findings:
        print(f"  {f}")
    return json.dumps(len(findings))


if __name__ == "__main__":
    sys.exit(0 if main() == "0" else 1)
