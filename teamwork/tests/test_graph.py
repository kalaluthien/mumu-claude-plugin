"""teamwork's components as a graph of who registers, runs, reads or names whom, by checkerwork's shared check: it
fails on a file no root reaches, a reference to a missing file or section, and a term defined twice across the Domain
and Verbs.

Run: uvx pytest teamwork/tests -q; `python3 teamwork/tests/test_graph.py` prints the edges and each finding.
"""
import importlib.util
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT.parent / "checkerwork" / "skills" / "eval" / "scripts" / "instruction-graph.py"
spec = importlib.util.spec_from_file_location("instruction_graph", SCRIPT)
instruction_graph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(instruction_graph)


class Graph(unittest.TestCase):
    def seeded(self, change):
        """The findings of a copy of the plugin after `change(copy)`."""
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / "plugin"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__"))
            change(copy)
            return instruction_graph.check(copy)[3]

    def test_the_head_has_no_orphan_dangling_reference_or_duplicate_term(self):
        findings = instruction_graph.check(ROOT)[3]
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
            path.write_text(path.read_text() + "\nSee [lead-playbook.md](references/lead-playbook.md)'s Gone.\n")
        self.assertIn("dangling section: skills/kickoff/SKILL.md names skills/kickoff/references/lead-playbook.md's Gone",
                      self.seeded(change))

    def test_a_domain_term_defined_twice_fails(self):
        def change(copy):
            path = copy / "skills" / "kickoff" / "SKILL.md"
            path.write_text(path.read_text().replace("| project |", "| task | again |\n| project |", 1))
        self.assertIn("term defined twice: task (skills/kickoff/SKILL.md)", self.seeded(change))

    def test_a_verb_that_redefines_a_domain_term_fails(self):
        def change(copy):
            path = copy / "skills" / "kickoff" / "SKILL.md"
            path.write_text(path.read_text().replace("| `comment` |", "| `topic` | again |\n| `comment` |", 1))
        self.assertIn("term defined twice: topic (skills/kickoff/SKILL.md)", self.seeded(change))


if __name__ == "__main__":
    sys.exit(instruction_graph.main([str(ROOT), "--edges"]))
