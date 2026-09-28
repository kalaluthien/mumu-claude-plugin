"""The eval graders: each passes the page it asks for and fails the page that only looks like it.

Run: uvx --with playwright pytest mumu-paperwork/tests -q
"""
import pathlib
import re
import unittest

EVALS = pathlib.Path(__file__).resolve().parents[1] / "evals"


def grader(case, name):
    """(pattern, flags) of a regex grader; its JavaScript pattern reads the same in Python, with no \\b or \\d."""
    front = (EVALS / case / "graders" / f"{name}.md").read_text()
    flags = re.search(r"^flags: (\w+)$", front, re.M).group(1)
    return re.search(r"^pattern: (.*)$", front, re.M).group(1), (re.S if "s" in flags else 0) | (re.I if "i" in flags else 0)


class Numbers(unittest.TestCase):
    """trend-chart's numbers: the prompt's 214 and 120 as text a reader sees inside <main>."""

    PAGE = "<html><head><title>가입</title></head><body><main>%s</main><script>var s = 1;</script></body></html>"

    def test_numbers_as_text_pass(self):
        pattern, flags = grader("trend-chart", "numbers")
        page = self.PAGE % "<h1>가입</h1><p>6월 앱은 214명이에요.</p><table><tr><td>120</td></tr></table>"
        self.assertTrue(re.search(pattern, page, flags))

    def test_numbers_out_of_view_fail(self):
        pattern, flags = grader("trend-chart", "numbers")
        for where, body in [("comment", "<h1>가입</h1><!-- 214 120 -->"),
                            ("script", "<h1>가입</h1><script>var d = [214, 120];</script>"),
                            ("attribute", '<h1>가입</h1><figure data-v="214 120"></figure>'),
                            ("one in a comment", "<p>214</p><!-- 120 -->"),
                            ("a longer number", "<p>2140 1200</p>")]:
            with self.subTest(where):
                self.assertIsNone(re.search(pattern, self.PAGE % body, flags))
        with self.subTest("outside main"):
            self.assertIsNone(re.search(pattern, "<p>214 120</p>" + self.PAGE % "<h1>가입</h1>", flags))


class Formal(unittest.TestCase):
    """Each page case's formal grader: a page in -습니다 passes, one sentence in -요 fails it."""

    def test_formal_register(self):
        for case in ("use-cases", "nested-chapters", "trend-chart"):
            pattern, flags = grader(case, "formal")
            with self.subTest(case):
                self.assertTrue(re.search(pattern, "<main><p>작업을 저장합니다.</p>\n<p>다시 시도합니다.</p></main>", flags))
                self.assertIsNone(re.search(pattern, "<main><p>작업을 저장합니다.</p>\n<p>다시 시도해요.</p></main>", flags))
