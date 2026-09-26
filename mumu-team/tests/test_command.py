"""`lib/command.py`: stdout of a command, or `RuntimeError` with its output.

Run: python3 -m unittest discover mumu-team/tests
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
from command import run  # noqa: E402


class Run(unittest.TestCase):
    def test_stdout_with_stdin_and_cwd(self):
        self.assertEqual(run("cat", stdin="hi\n"), "hi\n")
        self.assertEqual(run("pwd", cwd="/").strip(), "/")

    def test_failure_raises_with_stderr_and_stdout(self):
        with self.assertRaises(RuntimeError) as e:
            run(sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)")
        self.assertIn("err out", str(e.exception))

    def test_missing_command_raises(self):
        self.assertRaises(RuntimeError, run, "no-such-command-156")


if __name__ == "__main__":
    unittest.main()
