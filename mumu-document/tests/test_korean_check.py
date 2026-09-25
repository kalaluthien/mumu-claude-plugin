"""`korean-check.py` renders a page in Chrome and reads its text: each rule can fail (run as in test_skill_check)."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECK = ROOT / "bin" / "korean-check.py"
CHROME = pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
GOOD = """<!doctype html><html lang="ko"><meta charset="utf-8"><title>작업 큐 구조</title>
<main><h1>작업 큐는 파일 세 개로 이루어져 있습니다</h1>
<p>큐(queue)는 <code>POST /jobs with a body</code>로 일을 받아요. 저장소는 SQLite입니다.</p>
<pre>git log --oneline main</pre>
<svg><title>흐름: 일 하나를 넣기</title><text>작업자</text><text>큐</text><text>저장소</text></svg>
<div id="c"></div></main>
<script>document.getElementById('c').textContent = '재생';</script></html>"""


def run(html):
    with tempfile.TemporaryDirectory() as d:
        page = pathlib.Path(d) / "page.html"
        page.write_text(html)
        r = subprocess.run([sys.executable, str(CHECK), str(page)], capture_output=True, text=True)
        return r.returncode, r.stdout


@unittest.skipUnless(CHROME.exists(), "no Chrome")
class KoreanCheck(unittest.TestCase):
    def test_korean_page_passes(self):
        self.assertEqual(run(GOOD), (0, "pass\n"))

    def test_missing_lang_fails(self):
        code, out = run(GOOD.replace(' lang="ko"', ""))
        self.assertEqual(code, 1)
        self.assertIn('lang is "", not "ko"', out)

    def test_english_lang_fails(self):
        code, out = run(GOOD.replace('lang="ko"', 'lang="en"'))
        self.assertEqual(code, 1)
        self.assertIn('lang is "en"', out)

    def test_three_english_words_in_prose_fail(self):
        code, out = run(GOOD.replace("저장소는 SQLite입니다.", "It stores jobs."))
        self.assertEqual(code, 1)
        self.assertIn("English: It stores jobs.", out)

    def test_two_english_words_pass(self):
        self.assertEqual(run(GOOD.replace("SQLite입니다", "Job Store입니다"))[0], 0)

    def test_run_across_inline_tags_fails(self):
        code, out = run(GOOD.replace("저장소는 SQLite입니다.", "the <strong>job</strong> store"))
        self.assertEqual(code, 1)
        self.assertIn("English: the job store", out)

    def test_script_written_control_is_read(self):
        code, out = run(GOOD.replace("'재생'", "'Play the steps'"))
        self.assertEqual(code, 1)
        self.assertIn("English: Play the steps", out)

    def test_svg_title_is_read(self):
        code, out = run(GOOD.replace("흐름: 일 하나를 넣기", "Flow: add a job"))
        self.assertEqual(code, 1)
        self.assertIn("English: Flow: add a job", out)

    def test_alt_and_aria_label_are_read(self):
        for attr in ("alt", "aria-label"):
            code, out = run(GOOD.replace('<div id="c">', f'<img {attr}="the job queue" src="x.png"><div id="c">'))
            self.assertEqual(code, 1, attr)
            self.assertIn("English: the job queue", out)

    def test_plain_ending_fails(self):
        code, out = run(GOOD.replace("SQLite입니다.", "SQLite이다."))
        self.assertEqual(code, 1)
        self.assertIn("plain ending: 저장소는 SQLite이다.", out)

    def test_polite_endings_pass(self):
        self.assertEqual(run(GOOD.replace("SQLite입니다.", "SQLite예요. 끝났습니다."))[0], 0)


if __name__ == "__main__":
    unittest.main()
