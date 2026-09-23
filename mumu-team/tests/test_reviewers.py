"""The reviewer each pull request gets by its size, and the one body both reviewer agents share.

Run: python3 -m unittest discover mumu-team/tests
"""
import importlib.machinery
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
size = importlib.machinery.SourceFileLoader("review_size", str(ROOT / "bin" / "review-size.py")).load_module()


def git(repo, *args):
    subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True)


class ReviewSize(unittest.TestCase):
    def test_twenty_changed_lines_is_small_and_twenty_one_is_not(self):
        with tempfile.TemporaryDirectory() as repo:
            git(repo, "init", "-q", "-b", "main")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base")
            git(repo, "checkout", "-q", "-b", "topic")
            path = pathlib.Path(repo, "f.txt")
            printed = []
            for n in (20, 21):
                path.write_text("".join(f"{i}\n" for i in range(n)))
                git(repo, "add", "f.txt")
                git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", str(n))
                out = subprocess.run([str(ROOT / "bin" / "review-size.py"), "main", "HEAD"], cwd=repo, capture_output=True, text=True, check=True)
                printed.append(out.stdout.strip())
                git(repo, "reset", "-q", "--hard", "main")
            self.assertEqual(printed, ["reviewer-small (20 changed lines)", "reviewer (21 changed lines)"])

    def test_insertions_and_deletions_both_count(self):
        self.assertEqual(size.changed(" 2 files changed, 10 insertions(+), 2 deletions(-)"), 12)
        self.assertEqual(size.changed(" 1 file changed, 1 deletion(-)"), 1)
        self.assertEqual(size.changed(""), 0)
        self.assertEqual(size.agent_for(12), "reviewer-small")


class ReviewerAgents(unittest.TestCase):
    def split(self, name):
        _, front, body = (ROOT / "agents" / f"{name}.md").read_text().split("---\n", 2)
        return dict(line.split(": ", 1) for line in front.strip().splitlines()), body

    def test_the_two_agents_share_one_body_and_differ_in_model_and_effort(self):
        big, big_body = self.split("reviewer")
        small, small_body = self.split("reviewer-small")
        self.assertEqual(big_body, small_body)
        self.assertEqual((big["model"], big["effort"]), ("opus", "low"))
        self.assertEqual((small["model"], small["effort"]), ("sonnet", "medium"))


if __name__ == "__main__":
    unittest.main()
