"""run-evals.py: every page case gets a check.py grader, which fails a run whose page check.py FAILs.

Run: uvx --with playwright pytest mumu-paperwork/tests -q
"""
import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSEMBLE = ROOT / "skills" / "typesetting" / "scripts" / "assemble.py"
CHROME = pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
spec = importlib.util.spec_from_file_location("run_evals", ROOT / "scripts" / "run-evals.py")
run_evals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_evals)

BODY = "<h1>작은 쪽</h1>\n<p>이 쪽은 시험용이에요.</p>\n"


def result(root, *bodies):
    """An eval result for one page case whose runs each wrote one of `bodies`, assembled, to page.html, in a kept
    directory sealed as the eval leaves it; a body of None writes no page."""
    runs = []
    for i, body in enumerate(bodies):
        kept = root / f"e-{i}"
        cwd = kept / "sealed" / "home" / "cwd"
        cwd.mkdir(parents=True)
        (kept / "out").mkdir()
        if body is not None:
            (cwd / "body.html").write_text(body)
            subprocess.run([sys.executable, str(ASSEMBLE), str(cwd / "body.html"), str(cwd / "page.html")], check=True,
                           capture_output=True)
        os.chmod(kept / "sealed", 0)
        runs.append({"score": 1, "passed": True, "tracePath": str(kept / "out" / "trace.jsonl"),
                     "graders": [{"name": "shape", "passed": True, "weight": 1, "scored": True}]})
    return {"cases": [{"name": "page", "graders": [{"name": "shape", "type": "regex",
                                                     "config": {"target": {"source": "file", "path": "page.html"}}}],
                       "arms": {"with": runs}, "aggregates": {"score": 1, "passRate": 1}},
                      {"name": "chat", "graders": [{"name": "said", "type": "regex", "config": {"target": "last_message"}}],
                       "arms": {"with": [{"score": 1, "passed": True, "graders": []}]}, "aggregates": {"score": 1, "passRate": 1}}]}


@unittest.skipUnless(CHROME.exists(), "no Chrome")
class RunEvals(unittest.TestCase):
    def test_page_case_runs_graded_by_check(self):
        with tempfile.TemporaryDirectory() as d:
            graded = run_evals.grade(result(pathlib.Path(d), BODY, BODY.replace("작은 쪽", "{{title}}"), None), run_evals.check)
            runs = graded["cases"][0]["arms"]["with"]
            verdicts = [next(g for g in r["graders"] if g["name"] == "check.py page.html") for r in runs]
            self.assertEqual([g["passed"] for g in verdicts], [True, False, False], verdicts)
            self.assertEqual([r["passed"] for r in runs], [True, False, False])
            self.assertIn("{{", verdicts[1]["explanation"])
            self.assertEqual(verdicts[2]["explanation"], "no page.html")
            self.assertAlmostEqual(graded["cases"][0]["aggregates"]["passRate"], 1 / 3)
            self.assertEqual(graded["cases"][1]["arms"]["with"][0]["graders"], [], "a case with no page gets no check.py")
            run_evals.remove(graded)
            self.assertEqual(list(pathlib.Path(d).iterdir()), [])

