"""approved.py: real bypasses and every raw merge refused, text only naming them passed.

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
    "gh issue create --title t --body-file - <<'EOF'\nthe hook refuses git commit --no-verify and git commit -n\nEOF",
]

URL = "https://github.com/o/r/pull/1"
MERGE = f"gh pr merge {URL} --squash"

MERGE_REFUSED = [
    MERGE,
    f"{MERGE} --match-head-commit {'a' * 40}",
    f"gh -R o/r pr merge 1 --squash --match-head-commit {'a' * 40}",
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
    f'echo "<<EOF"\n{MERGE}\nEOF',
    f"echo '<<EOF'\n{MERGE}\nEOF",
    f". /dev/stdin <<'EOF'\n{MERGE}\nEOF",
    f"source /dev/stdin <<'EOF'\n{MERGE}\nEOF",
    f"python3 - <<'EOF'\nimport os; os.system('{MERGE}')\nEOF",
    f"cat <<'EOF' |\n{MERGE}\nEOF\nsh",
    f"bash -c \"$(cat <<'EOF'\n{MERGE}\nEOF\n)\"",
    f"watch -n1 '{MERGE}'",
    f"git -c alias.x='!{MERGE}' x",
    f"echo '{MERGE}' | sh",
    f"git -c alias.x='!sh' x <<'EOF'\n{MERGE}\nEOF",
    f"git -c alias.x='!f(){{ eval \"$2\"; }};f' x -m '{MERGE}'",
    f"gh x --body '{MERGE}'",
    f"GIT_EDITOR=sh git commit --allow-empty -e -F - <<'EOF'\n{MERGE}\nEOF",
    f"GIT_EDITOR=sh git commit --allow-empty -e -m '{MERGE}'",
    f"git commit --allow-empty --edit -m '{MERGE}'",
    f"export GIT_EDITOR=sh\ngit commit --allow-empty -eF - <<'EOF'\n{MERGE}\nEOF",
    f"export GH_EDITOR=sh\ngh issue create -eb '{MERGE}'",
    f"export GH_EDITOR=sh\ngh issue create --editor --body '{MERGE}'",
    f"git commit -m '{MERGE}'",
    f"grep -q x f && sh -c '{MERGE}'",
    f"git grep -O'{MERGE}' x",
    f"git grep --open-files-in-pager='{MERGE}' x",
    f"git -c core.pager=sh grep -O -e '{MERGE}'",
    f"GIT_PAGER='{MERGE}' git grep -O x",
    f"sed -n '1e {MERGE}' f",
    f"sed -i '' 's/x/{MERGE}/e' f",
    f"sed -i '' -e'e {MERGE}' f",
    f"sed -n 's/.*/{MERGE}/p' f | sh",
    f"sed -i '' -ne'e {MERGE}' f",
    f"sed -i '' 's/x/{MERGE}/ge' f",
    f"sed -i '' 's/.*/{MERGE}/w /dev/stdout' f | sh",
    f"sed -i '' 's/.*/{MERGE}/W /dev/stdout' f | sh",
    f"sed -i '' -e 's/.*/{MERGE}/' -e 'W /dev/stdout' f | sh",
]

# Text only naming the merge in a pattern or an in-place edit: refused on main (#87).
TEXT_MERGE_PASSED = [
    "git grep -n 'pr merge' mumu-team",
    f"git grep -e '{MERGE}' -- '*.md'",
    "sed -i '' 's/gh pr merge/merge.py/' AGENTS.md",
    f"sed -i.bak -e '/{MERGE}/d' notes.md",
    f"sed -i '' 's/{MERGE}/merge.py/g' mumu-team/skills/kickoff/references/work.md",
]

MERGE_PASSED = [
    f"cat > /tmp/note.md <<'EOF'\nrun {MERGE} later\nEOF",
    f"gh issue comment 1 --body-file - <<'EOF'\nthe lead's {MERGE} was refused\nEOF",
    f'gh issue reopen 9 --comment "refused: {MERGE}"',
    f"gh pr create --title t --body \"$(cat <<'EOF'\nnever {MERGE} unpinned\nEOF\n)\"",
    'grep -n "pr merge" mumu-team/bin/approved.py',
    f"merge.py {URL}",
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
    def test_every_raw_merge_is_refused_pinned_or_not(self):
        for command in MERGE_REFUSED:
            with self.subTest(command):
                result = run(command)
                self.assertEqual(result.returncode, 2)
                self.assertIn("merge.py", result.stderr)

    def test_text_naming_the_merge_passes(self):
        for command in MERGE_PASSED + TEXT_MERGE_PASSED:
            with self.subTest(command):
                result = run(command)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
