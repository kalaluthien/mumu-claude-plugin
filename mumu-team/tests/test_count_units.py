"""`scripts/count-units.py`: the code counts on a small plugin, and the Sonnet counts against a fake `claude`
on PATH that answers each ask with a fixed reply (#326).

Run: python3 -m pytest mumu-team/tests -q
"""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "count-units.py"
spec = importlib.util.spec_from_file_location("count_units", SCRIPT)
count_units = importlib.util.module_from_spec(spec)
spec.loader.exec_module(count_units)

FILES = {
    "skills/one/SKILL.md": "# One\n\nDo this; never that.\n",
    "agents/boss.md": "---\nname: boss\n---\nRead the rules.\n",
    "hooks/hooks.json": json.dumps({"hooks": {"Stop": [{"hooks": [{"command": "${CLAUDE_PLUGIN_ROOT}/scripts/stop.py"}]}],
                                              "PreToolUse": [{"matcher": "Bash", "hooks": [{"command": "\"${X}\"/scripts/g.py a"}]}]}}),
    "monitors/monitors.json": json.dumps([{"name": "watch", "command": "w"}]),
    "bin/go.py": "print(1)\nprint(2)\n",
    "evals/case-a/prompt.md": "hi\n",
    "tests/test_x.py": "pass\n",
    "scripts/__pycache__/x.pyc": "",
}

# The fake answers by what the ask names: a file's counts, then the duplicate and variant passes.
FAKE = r'''#!/usr/bin/env python3
import sys
ask = sys.stdin.read()
if ask.startswith("Count the file skills/one/SKILL.md"):
    body = '{"instructions": [{"line": 3, "text": "do this"}, {"line": 3, "text": "never that"}], "elaboration": [], "terms": [{"line": 1, "name": "One"}]}'
elif ask.startswith("Count the file agents/boss.md"):
    body = '{"instructions": [{"line": 4, "text": "read the rules"}], "elaboration": [{"line": 2, "text": "name"}], "terms": [{"line": 2, "name": "boss"}, {"line": 4, "name": "One"}]}'
elif "every instruction" in ask:
    body = '{"groups": [["i0", "i2"], ["i1"]]}'
else:
    body = '{"variants": [["One", "boss"], ["ghost"]]}'
print("thinking\n```json\n" + body + "\n```")
'''


class Code(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        for rel, text in FILES.items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(text)

    def test_features_list_each_kind_by_name(self):
        self.assertEqual(count_units.features(self.root), {
            "skills": ["one"], "agents": ["boss"],
            "hook registrations": ["Stop stop.py", "PreToolUse[Bash] g.py"],
            "monitors": ["watch"], "bin executables": ["go.py"], "eval cases": ["case-a"]})

    def test_files_and_lines_leave_caches_out(self):
        files = count_units.tree(self.root)
        self.assertEqual(len(files), len(FILES) - 1)
        by, total = count_units.lines(files, self.root)
        self.assertEqual((by[".py"], total), (3, sum(len(t.splitlines()) for t in FILES.values())))

    def test_sonnet_reads_only_md_outside_tests_and_evals(self):
        self.assertEqual(sorted(p.relative_to(self.root).as_posix() for p in count_units.texts(self.root)),
                         ["agents/boss.md", "skills/one/SKILL.md"])

    def test_counts_by_the_fake_and_prints_each_item_with_its_path_line(self):
        fakes = pathlib.Path(tempfile.mkdtemp())
        (fakes / "claude").write_text(FAKE)
        (fakes / "claude").chmod(0o755)
        env = dict(os.environ, PATH=f"{fakes}:{os.environ['PATH']}")
        out = subprocess.run([sys.executable, str(SCRIPT), str(self.root), "--json", str(fakes / "r.json")],
                             capture_output=True, text=True, env=env)
        self.assertEqual(out.returncode, 0, out.stderr)
        for line in ["files 7", "features 7", "instructions 3", "duplicates 1", "elaboration 1", "terms 2, variants 1",
                     "  agents/boss.md:4 read the rules = skills/one/SKILL.md:3 never that",
                     "  One agents/boss.md:4 = boss agents/boss.md:2",
                     "  elaboration agents/boss.md:2 name", "  term agents/boss.md:4 One"]:
            self.assertIn(line, out.stdout.splitlines())
        self.assertEqual(len(json.loads((fakes / "r.json").read_text())["instructions"]), 3)

    def test_no_json_reply_exits_2(self):
        fakes = pathlib.Path(tempfile.mkdtemp())
        (fakes / "claude").write_text("#!/bin/sh\necho no json\n")
        (fakes / "claude").chmod(0o755)
        env = dict(os.environ, PATH=f"{fakes}:{os.environ['PATH']}")
        out = subprocess.run([sys.executable, str(SCRIPT), str(self.root)], capture_output=True, text=True, env=env)
        self.assertEqual(out.returncode, 2)
        self.assertIn("could not count", out.stderr)


if __name__ == "__main__":
    unittest.main()
