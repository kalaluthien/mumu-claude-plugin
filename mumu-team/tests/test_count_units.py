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
    "skills/one/SKILL.md": "# One\n\nDo this; never that. It is `One`.\n",
    "agents/boss.md": "---\nname: boss\ndescription: The boss.\n---\nRead the rules with `gh issue view`.\n",
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
    body = '{"sentences": {"3.1": [1, 0], "3.2": [1, 0], "3.3": [0, 1]}, "terms": [{"name": "`One`", "line": "3.3"}]}'
elif ask.startswith("Count the file agents/boss.md"):
    body = '{"sentences": {"3.1": [0, 1], "5.1": [1, 0]}, "terms": [{"name": "boss (the agent)", "line": 2}, {"name": "gh issue view <url>", "line": 5}]}'
elif "states an instruction" in ask:
    body = '{"groups": [["agents/boss.md#5.1", "skills/one/SKILL.md#3.1"], ["skills/one/SKILL.md#3.2"]]}'
else:
    body = '{"variants": [["One", "Boss"], ["ghost"]]}'
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
        by, total = count_units.lines(files)
        self.assertEqual((by[".py"], total), (3, sum(len(t.splitlines()) for t in FILES.values())))

    def test_sonnet_reads_only_md_outside_tests_and_evals(self):
        self.assertEqual(sorted(p.relative_to(self.root).as_posix() for p in count_units.texts(self.root)),
                         ["agents/boss.md", "skills/one/SKILL.md"])

    def test_sentences_skip_headings_fences_and_front_matter_but_its_description(self):
        text = "---\nname: x\ndescription: Says x. Then y.\n---\n# H\n\n```\ncode. More.\n```\n| a | b |\n| --- | --- |\nOne. Two? `three` too; four.\n"
        self.assertEqual(count_units.sentences(text), [
            ("3.1", 3, "Says x."), ("3.2", 3, "Then y."), ("10.1", 10, "| a | b |"),
            ("12.1", 12, "One."), ("12.2", 12, "Two?"), ("12.3", 12, "`three` too;"), ("12.4", 12, "four.")])

    def test_counts_by_the_fake_and_prints_each_item_with_its_path_line(self):
        fakes = pathlib.Path(tempfile.mkdtemp())
        (fakes / "claude").write_text(FAKE)
        (fakes / "claude").chmod(0o755)
        env = dict(os.environ, PATH=f"{fakes}:{os.environ['PATH']}")
        out = subprocess.run([sys.executable, str(SCRIPT), str(self.root), "--json", str(fakes / "r.json")],
                             capture_output=True, text=True, env=env)
        self.assertEqual(out.returncode, 0, out.stderr)
        for line in ["files 7", "features 7", "instructions 3", "duplicates 1", "elaboration 2", "terms 3, variants 1",
                     "  agents/boss.md:5 Read the rules with `gh issue view`. = skills/one/SKILL.md:3 Do this;",
                     "  one skills/one/SKILL.md:3 = boss agents/boss.md:2",
                     "  elaboration 1 agents/boss.md:3 The boss.", "  term agents/boss.md:5 gh issue view",
                     "  instruction 1 skills/one/SKILL.md:3 never that."]:
            self.assertIn(line, out.stdout.splitlines())
        self.assertEqual(json.loads((fakes / "r.json").read_text())["totals"]["instructions"], 3)

    def test_majority_keeps_pairs_grouped_in_more_than_half_the_samples(self):
        self.assertEqual(count_units.majority([[["a", "b", "c"]], [["a", "b"], ["c", "d"]], [["b", "a"], ["d", "c"]]], 3),
                         [["a", "b"], ["c", "d"]])
        self.assertEqual(count_units.majority([[["a", "b"]], [], []], 3), [])

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
