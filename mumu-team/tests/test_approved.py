"""approved.py: real bypasses and unpinned merges refused, text only naming them passed.

Run: python3 -m unittest discover mumu-team/tests
"""
import json
import pathlib
import shlex
import subprocess
import sys
import unittest

HOOK = pathlib.Path(__file__).resolve().parent.parent / "bin" / "approved.py"
KEY = "core.hooksPath"

REFUSED = [
    f"git -c {KEY}=x commit -m m",
    f"git -c '{KEY}=x' commit -m m",
    f"git config {KEY} /tmp/h",
    f"git config --global {KEY} /tmp/h",
    f"git config --local {KEY} /tmp/h",
    f"git -C /r config {KEY} /tmp/h",
    f"git config --file .git/config {KEY} /tmp/h",
    f"git config set {KEY} /tmp/h",
    f"git --config-env={KEY}=VAR commit -m m",
    f"GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0={KEY} GIT_CONFIG_VALUE_0=x git commit -m m",
    "git commit --no-verify -m m",
    "git commit --no-verif -m m",
    "git commit -n -m m",
    "git commit -an -m m",
]

PASSED = [
    f"gh issue create --title t --body-file - <<'EOF'\nset {KEY} here\nEOF",
    f"gh issue create --title t --body-file - <<'EOF'\nthe owner's {KEY} guard\nEOF",
    f'gh pr comment 1 --body "do not set {KEY} here"',
    f'git commit -m "mention {KEY}"',
    f"echo {KEY}",
    f"grep -rn {KEY} .",
    f"git config {KEY}",
    f"git config --get {KEY}",
]

URL = "https://github.com/o/r/pull/1"
MERGE = f"gh pr merge {URL} --squash"

MERGE_REFUSED = [
    MERGE,
    f"bash -c '{MERGE}'",
    f'bash -c "echo hi && {MERGE}"',
    f"eval '{MERGE}'",
    f"eval {MERGE}",
    f'echo "$({MERGE})"',
    f"echo `{MERGE}`",
    f"bash <<'EOF'\n{MERGE}\nEOF",
    f"cat <<EOF | sh\n{MERGE}\nEOF",
    f"cat <<EOF\n$({MERGE})\nEOF",
    f"cat <<'EOF'\nnot closed\n{MERGE}",
]

MERGE_PASSED = [
    f"cat > /tmp/note.md <<'EOF'\nrun {MERGE} later\nEOF",
    f"gh issue comment 1 --body-file - <<'EOF'\nthe lead's {MERGE} was refused\nEOF",
    f'gh issue reopen 9 --comment "refused: {MERGE}"',
    f"gh pr create --title t --body \"$(cat <<'EOF'\nnever {MERGE} unpinned\nEOF\n)\"",
    'grep -n "pr merge" mumu-team/bin/approved.py',
    f'git commit -m "gate {MERGE}"',
]


def run(command):
    payload = json.dumps({"tool_input": {"command": command}})
    return subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True)


class HookBypass(unittest.TestCase):
    def test_every_bypass_is_refused_plain_and_inside_bash_c(self):
        for command in REFUSED:
            for form in (command, f"bash -c {shlex.quote(command)}"):
                with self.subTest(form):
                    result = run(form)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("hook bypass refused", result.stderr)

    def test_text_naming_the_hooks_path_passes(self):
        for command in PASSED:
            with self.subTest(command):
                result = run(command)
                self.assertEqual(result.returncode, 0, result.stderr)


class MergeGate(unittest.TestCase):
    def test_every_unpinned_merge_is_refused(self):
        for command in MERGE_REFUSED:
            with self.subTest(command):
                self.assertEqual(run(command).returncode, 2)

    def test_merge_at_an_unapproved_sha_is_refused(self):
        pr = "https://github.com/kalaluthien/mumu-claude-plugin/pull/23"
        result = run(f"gh pr merge {pr} --squash --match-head-commit {'0' * 40}")
        self.assertEqual(result.returncode, 2)
        self.assertIn("is not the PR head", result.stderr)  # past the text gate, at the PR check

    def test_text_naming_the_merge_passes(self):
        for command in MERGE_PASSED:
            with self.subTest(command):
                result = run(command)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
