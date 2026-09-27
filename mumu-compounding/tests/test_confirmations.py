"""`scripts/confirmations.py`: a lesson found again, and the lessons never found again.

Run: python3 -m unittest discover mumu-compounding/tests
"""
import os
import pathlib
import subprocess
import tempfile
import unittest
from datetime import date, datetime, timedelta

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "confirmations.py"
TODAY = date.today().isoformat()


def run(*args):
    return subprocess.run(["python3", str(SCRIPT), *args], capture_output=True, text=True, check=True).stdout


class Pool(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.config = pathlib.Path(tmp.name)
        self.pool = self.config / "projects" / "-repo" / "memory"
        self.pool.mkdir(parents=True)

    def write(self, name, text, days_old=0):
        path = self.pool / name
        path.write_text(text)
        at = (datetime.now() - timedelta(days=days_old)).timestamp()
        os.utime(path, (at, at))
        return path

    def snapshot(self):
        return {p.name: p.read_text() for p in self.pool.iterdir()}


class Confirm(Pool):
    def test_found_again_raises_the_count_and_date_and_nothing_else(self):
        lesson = self.write("pitfall-a.md", "---\nname: a\nmetadata:\n  type: feedback\nconfirmed: 1\n"
                                             "last-confirmed: 2026-01-02\n---\n\nWhen x, do y, because z.\n")
        self.write("fact-b.md", "---\nname: b\n---\n\nThe port is 5173.\n")
        self.write("MEMORY.md", "- [A](pitfall-a.md)\n- [B](fact-b.md)\n")
        before = self.snapshot()
        run("confirm", str(lesson))
        after = self.snapshot()
        self.assertEqual({k: v for k, v in after.items() if k != "pitfall-a.md"},
                         {k: v for k, v in before.items() if k != "pitfall-a.md"})
        changed = [(a, b) for a, b in zip(before["pitfall-a.md"].splitlines(), after["pitfall-a.md"].splitlines()) if a != b]
        self.assertEqual(changed, [("confirmed: 1", "confirmed: 2"), ("last-confirmed: 2026-01-02", f"last-confirmed: {TODAY}")])

    def test_a_file_without_the_fields_gets_them(self):
        lesson = self.write("fact-c.md", "---\nname: c\n---\n\nBody.\n")
        run("confirm", str(lesson))
        self.assertEqual(lesson.read_text(), f"---\nname: c\nconfirmed: 2\nlast-confirmed: {TODAY}\n---\n\nBody.\n")

    def test_a_file_without_frontmatter_gets_one(self):
        lesson = self.write("fact-d.md", "Body.\n")
        run("confirm", str(lesson))
        self.assertEqual(lesson.read_text(), f"---\nconfirmed: 2\nlast-confirmed: {TODAY}\n---\nBody.\n")


class Stale(Pool):
    def test_only_an_old_lesson_never_found_again_is_listed_and_none_is_deleted(self):
        old = (date.today() - timedelta(days=61)).isoformat()
        self.write("stale.md", f"---\nconfirmed: 1\nlast-confirmed: {old}\n---\n\nOld.\n")
        self.write("fresh.md", f"---\nconfirmed: 1\nlast-confirmed: {TODAY}\n---\n\nNew.\n")
        self.write("often.md", f"---\nconfirmed: 3\nlast-confirmed: {old}\n---\n\nKept.\n")
        self.write("unstamped.md", "Old, no fields.\n", days_old=90)
        self.write("MEMORY.md", "- index\n", days_old=90)
        before = self.snapshot()
        out = run("stale", str(self.config))
        self.assertEqual(sorted(pathlib.Path(line.split(":")[0]).name for line in out.splitlines()),
                         ["stale.md", "unstamped.md"])
        self.assertIn("2 files, 7 lines", out)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
