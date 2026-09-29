"""The plugin's own hooks allow the literal form of each routine step, so the owner's settings need no allow rule for
it, and give no allow to any other form of the same step, which keeps today's path (#355).

Run: uvx pytest mumu-teamwork/tests -q
"""
import fnmatch
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOK = ROOT / "scripts" / "bash-guard.py"
JUDGE = ROOT / "scripts" / "judge-allow.py"
PR = "https://github.com/kalaluthien/mumu-claude-plugin/pull/355"
U = "https://github.com/kalaluthien/mumu-claude-plugin/issues/355"
N = "sample-topic-12-1"
HOOKS = "/Users/me/workspace/plugins/.git/hooks"
# each rule the owner's settings.json held (kalaluthien/dotclaude settings.json:10-32), and a literal command it matches
LITERAL = {
    "herdr agent prompt *": f'herdr agent prompt plugins-lead "see {U}"',
    "herdr agent rename *": f"herdr agent rename w1:p2 {N}",
    "herdr agent read *": f"herdr agent read {N}",
    "herdr tab rename *": f"herdr tab rename w1:t2 {N}",
    "herdr agent send-keys *": f"herdr agent send-keys {N} enter",
    "worker-start.py *": f"worker-start.py /Users/me/workspace/plugins sample-topic low {U} --lead plugins-lead",
    "lead-start.py *": f"lead-start.py /Users/me/workspace/plugins {U} --folder mumu-teamwork",
    "pr-merge.py https://github.com/*": f"pr-merge.py {PR}",
    "decision-post.py https://github.com/*": f"decision-post.py {U} < /tmp/decision.md",
    "session-close.py *": f"session-close.py {N}",
    "git worktree remove .claude/worktrees/*": f"git worktree remove .claude/worktrees/{N}",
    "git worktree remove --force .claude/worktrees/*": f"git worktree remove --force .claude/worktrees/{N}",
    "git worktree remove --force --force .claude/worktrees/*": f"git worktree remove --force --force .claude/worktrees/{N}",
    "git worktree unlock .claude/worktrees/*": f"git worktree unlock .claude/worktrees/{N}",
    "git worktree prune": "git worktree prune",
    "git branch -D *": f"git branch -D {N}",
    "git push origin --delete *": f"git push origin --delete {N}",
    "git pull --ff-only": "git pull --ff-only",
    "git pull --ff-only -q": "git pull --ff-only -q",
    "rm -rf .claude/worktrees/*": f"rm -rf .claude/worktrees/{N}",
    "rm */.git/hooks/pre-commit": f"rm {HOOKS}/pre-commit",
}


def others(command):
    """Other forms of the same step: compound, `&&`, `;`, `$(...)`, `git -C`, a path prefix, a loop, and more."""
    word = command.split()[0]
    forms = [f"cd /tmp && {command}", f"{command}; ls", f"ls; {command}", f"{command} | cat", f"{command} > /tmp/out",
             f"{command} $(echo x)", f"X=1 {command}", f"bash -c '{command}'", f"for x in a b; do {command}; done",
             f"{command} *", f"{command}\nls", f"time {command}"]
    if word == "git":
        forms.append(command.replace("git ", "git -C /Users/me/workspace/plugins ", 1))
    elif word.endswith(".py"):
        forms += [f"/Users/me/plugins/mumu-teamwork/bin/{command}", f"python3 {command}"]
    else:
        forms.append(f"/opt/homebrew/bin/{command}")
    return forms


def run(hook, payload):
    return subprocess.run([sys.executable, str(hook)], input=json.dumps(payload), capture_output=True, text=True)


def decision(result):
    """The hook's `permissionDecision`, or None when it gives none."""
    out = result.stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else None


class Allow(unittest.TestCase):
    def guard(self, command, agent=None):
        payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": tempfile.mkdtemp()}
        if agent:
            payload["agent_type"] = f"mumu-teamwork:{agent}"
        return run(HOOK, payload)

    def test_each_rule_s_literal_form_is_allowed(self):
        for rule, command in LITERAL.items():
            self.assertTrue(fnmatch.fnmatchcase(command, rule), (rule, command))
            for agent in (None, "lead"):
                with self.subTest(command=command, agent=agent):
                    result = self.guard(command, agent)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(decision(result), "allow")

    def test_other_forms_of_each_step_get_no_allow(self):
        for command in LITERAL.values():
            for other in others(command):
                with self.subTest(command=other):
                    self.assertIsNone(decision(self.guard(other)))

    def test_near_misses_get_no_allow(self):
        for command in [f"pr-merge.py http://evil/{PR}", f"decision-post.py {U} > /tmp/x", f"pr-merge.py {PR} < /tmp/x",
                        "rm -rf .claude/worktrees/../..", "rm -rf .claude/worktrees/*", "rm -rf /x/.claude/worktrees/a",
                        f"git branch -D {N} ~", "git pull --ff-only origin main", "git worktree remove /tmp/x",
                        "herdr pane close w1:p2", "gh pr view 1", "ls"]:
            with self.subTest(command=command):
                self.assertIsNone(decision(self.guard(command)))

    def test_a_refusal_wins_over_the_allow(self):
        result = self.guard("herdr agent prompt plugins-lead \"please merge now\"", "worker")
        self.assertEqual(result.returncode, 2)
        self.assertIsNone(decision(result))


class JudgeAllow(unittest.TestCase):
    def test_only_the_judge_launch_is_allowed(self):
        for agent, expected in [("mumu-teamwork:judge", "allow"), ("general-purpose", None), ("judge", None), (None, None)]:
            with self.subTest(agent=agent):
                tool_input = {"prompt": f"see {PR}", "description": "judge"}
                if agent:
                    tool_input["subagent_type"] = agent
                result = run(JUDGE, {"tool_name": "Agent", "tool_input": tool_input})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(decision(result), expected)

    def test_the_agent_matcher_runs_it(self):
        hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text())["hooks"]["PreToolUse"]
        agent = [h for h in hooks if h["matcher"] == "Agent"]
        self.assertEqual([h["hooks"][0]["command"] for h in agent], ['"${CLAUDE_PLUGIN_ROOT}"/scripts/judge-allow.py'])


if __name__ == "__main__":
    unittest.main()
