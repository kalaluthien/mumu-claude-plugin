"""What `instruction-graph.py` prints for a seeded repository with no config file: each seeded defect named, nothing
for a missing file an eval names, and exit 0 on the clean seed.

Run: uvx pytest checkerwork/tests
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "skills" / "eval" / "scripts" / "instruction-graph.py"

CLEAN = {
    "CLAUDE.md": "@AGENTS.md\n",
    "AGENTS.md": """# Agents

Read [the guide](docs/guide.md#setup) before a change, and run `scripts/build.sh`.

## Domain

| term | meaning |
| --- | --- |
| widget | one part the app draws |
| gadget | a widget with a state |
""",
    "docs/guide.md": "# Guide\n\n## Setup\n\nRun `scripts/build.sh` once.\n",
    "scripts/build.sh": "#!/bin/sh\necho built\n",
    ".claude/skills/deploy/SKILL.md": """---
name: deploy
description: Use when shipping a build.
---

# Deploy

Follow [steps.md](references/steps.md)'s Release, then `Brewfile`.

| keyword | form |
| --- | --- |
| `SHIPPED:` | the version shipped |
""",
    ".claude/skills/deploy/references/steps.md": "# Steps\n\n## Release\n\nTag it.\n",
    ".claude/skills/deploy/Brewfile": "brew \"jq\"\n",
    "tools/.claude-plugin/plugin.json": '{"name": "tools"}\n',
    "tools/skills/ship/SKILL.md": "---\nname: ship\ndescription: Use when shipping.\n---\n\n# Ship\n\nRun `scripts/build.sh`.\n",
    "tools/evals/ship/prompt.md": "Ship the build in `skills/ship/sample.md`.\n",
}


def run(files):
    """What the check prints for a git repository holding `files`."""
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for name, text in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(text)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        return subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True)


class InstructionGraph(unittest.TestCase):
    def test_the_clean_seed_exits_0_with_no_finding(self):
        out = run(CLEAN)
        self.assertEqual((out.returncode, out.stdout.strip()), (0, "findings (0):"), out.stdout + out.stderr)

    def test_each_seeded_defect_is_named(self):
        files = dict(CLEAN)
        files["AGENTS.md"] += "\nSee [the old guide](docs/gone.md) and [the guide](docs/guide.md#teardown).\n"
        files[".claude/skills/deploy/references/unused.md"] = "# Unused\n"
        files[".claude/skills/deploy/SKILL.md"] += "| widget | defined again |\n"
        files["AGENTS.md"] += "Cases such as `tools/evals/ship/missing.md` show it.\n"
        files["tools/evals/ship/graders/named.md"] = "Passes when the reply names `skills/ship/example.md`.\n"
        out = run(files)
        self.assertEqual(out.returncode, 1, out.stdout)
        found = out.stdout.splitlines()[1:]
        self.assertEqual(sorted(f.strip() for f in found), sorted([
            "dangling link: AGENTS.md links docs/gone.md",
            "dangling section: AGENTS.md links docs/guide.md#teardown",
            "orphan: .claude/skills/deploy/references/unused.md, which no root reaches",
            "term defined twice: widget (.claude/skills/deploy/SKILL.md, AGENTS.md)",
        ]), out.stdout)

    def test_a_missing_file_a_prose_path_names_and_a_missing_heading_are_named(self):
        files = dict(CLEAN)
        files[".claude/skills/deploy/SKILL.md"] = files[".claude/skills/deploy/SKILL.md"].replace(
            "'s Release", "'s Rollback") + "\nThen run `scripts/publish.sh`.\n"
        out = run(files)
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertIn("dangling section: .claude/skills/deploy/SKILL.md names "
                      ".claude/skills/deploy/references/steps.md's Rollback", out.stdout)
        self.assertIn("dangling reference: .claude/skills/deploy/SKILL.md names scripts/publish.sh", out.stdout)


if __name__ == "__main__":
    unittest.main()
