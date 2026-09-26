"""The hook and monitor `scripts/`, each run as Claude Code runs it, against fakes on PATH and a written transcript.

Run: python3 -m unittest discover mumu-team/tests
"""
import datetime
import importlib.machinery
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

HOOK = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "bash-guard.py"
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

PR_URL = "https://github.com/o/r/pull/1"
MERGE = f"gh pr merge {PR_URL} --squash"

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
    f"sed -i '' 's/{MERGE}/merge.py/g' mumu-team/skills/kickoff/references/work-task.md",
]

MERGE_PASSED = [
    f"cat > /tmp/note.md <<'EOF'\nrun {MERGE} later\nEOF",
    f"gh issue comment 1 --body-file - <<'EOF'\nthe lead's {MERGE} was refused\nEOF",
    f'gh issue reopen 9 --comment "refused: {MERGE}"',
    f"gh pr create --title t --body \"$(cat <<'EOF'\nnever {MERGE} unpinned\nEOF\n)\"",
    'grep -n "pr merge" mumu-team/scripts/bash-guard.py',
    f"merge.py {PR_URL}",
]


# An assignment-only command before a redirect, heredoc or pipe: exit 2 with IndexError at 58dd603 (#87).
# The description names the merge, as a live payload's may, so the hook reads the command.
ASSIGNMENT_PASSED = [
    "S=/tmp/x\ncat >> $S/h.md <<'EOF'\ntext\nEOF",
    "S=/tmp/x\ncat > $S/h.md",
    "S=/tmp/x; cat $S/a | grep b",
    "S=/tmp/x T=y && git status",
    "S=/tmp/x | cat",
    "S=/tmp/x\ngit grep -n x",
    "S=/tmp/x\nsed -i '' 's/a/b/' f",
    "C=/x; gh pr view 96 --json state -q .state && git -C $C log -1",
]

def run(command, description=""):
    payload = json.dumps({"tool_input": {"command": command, "description": description}})
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


class AssignmentOnly(unittest.TestCase):
    def test_an_assignment_only_command_is_read_not_refused(self):
        for command in ASSIGNMENT_PASSED:
            with self.subTest(command):
                result = run(command, "append the merge notes")
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_merge_after_an_assignment_only_command_is_still_refused(self):
        result = run(f"S=/tmp/x\n{MERGE}")
        self.assertEqual(result.returncode, 2)
        self.assertIn("merge.py", result.stderr)

    def test_every_helper_reads_an_empty_and_an_assignment_only_word_list(self):
        guard = importlib.machinery.SourceFileLoader("bash_guard", str(HOOK)).load_module()
        whole = [guard.reader, guard.unredirected, guard.mentions, guard.bypasses]
        indexed = [guard.text_word, guard.config_value]
        for words in ([], ["S=/tmp/x"], ["S=/tmp/x", "T=y"]):
            for helper in whole:
                with self.subTest(helper=helper.__name__, words=words):
                    helper(words)
            for helper in indexed:
                for i in range(len(words)):
                    with self.subTest(helper=helper.__name__, words=words, i=i):
                        helper(words, i)


PLUGIN = pathlib.Path(__file__).resolve().parent.parent
READ_AT = datetime.datetime(2026, 9, 26, 6, 0, tzinfo=datetime.timezone.utc)


class Reread(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.plugin = self.tmp / "mumu-team"
        shutil.copytree(PLUGIN / "scripts", self.plugin / "scripts")
        shutil.copytree(PLUGIN / "hooks", self.plugin / "hooks")
        self.refs = self.plugin / "skills" / "kickoff" / "references"
        self.refs.mkdir(parents=True)
        for name in ("work-task.md", "task.md", "routing.md"):
            (self.refs / name).write_text("rules\n")
            self.touch(name, changed=False)

    def touch(self, name, changed):
        """Set a file's mtime an hour before the reads, or an hour after."""
        at = (READ_AT + datetime.timedelta(hours=1 if changed else -1)).timestamp()
        os.utime(self.refs / name, (at, at))

    def prompt(self, *calls):
        """Run the hook on a transcript of `calls`, each a (tool, input) made at READ_AT; return the injected context."""
        transcript = self.tmp / "t.jsonl"
        lines = [{"type": "user", "timestamp": READ_AT.isoformat(), "message": {"role": "user", "content": "go"}}]
        lines += [{"type": "assistant", "timestamp": READ_AT.isoformat().replace("+00:00", "Z"),
                   "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "t", "name": tool, "input": given}]}}
                  for tool, given in calls]
        transcript.write_text("".join(json.dumps(line) + "\n" for line in lines))
        payload = {"hook_event_name": "UserPromptSubmit", "session_id": "s", "transcript_path": str(transcript),
                   "cwd": str(self.tmp), "prompt": "see url"}
        commands = [h["command"] for entry in json.loads((self.plugin / "hooks" / "hooks.json").read_text())["hooks"]
                    .get("UserPromptSubmit", []) for h in entry["hooks"]]
        self.assertTrue(commands)
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(self.plugin))
        outs = [subprocess.run(c, shell=True, input=json.dumps(payload), env=env, capture_output=True, text=True, timeout=30)
                for c in commands]
        self.assertTrue(all(o.returncode == 0 for o in outs), outs)
        return "".join(json.loads(o.stdout)["hookSpecificOutput"]["additionalContext"] for o in outs if o.stdout.strip())

    def read(self, name):
        return "Read", {"file_path": str(self.refs / name)}

    def test_read_then_changed_names_that_file_once(self):
        self.touch("work-task.md", changed=True)
        context = self.prompt(self.read("work-task.md"))
        self.assertEqual(context.count(str(self.refs / "work-task.md")), 1, context)
        self.assertNotIn("routing.md", context)

    def test_read_by_bash_through_the_plugin_root_counts(self):
        self.touch("work-task.md", changed=True)
        command = f"cd {self.plugin}/skills/kickoff && cat references/work-task.md"
        self.assertIn("work-task.md", self.prompt(("Bash", {"command": command})))

    def test_read_and_unchanged_names_nothing(self):
        self.assertEqual(self.prompt(self.read("work-task.md"), self.read("routing.md")), "")

    def test_changed_but_never_read_names_nothing(self):
        self.touch("work-task.md", changed=True)
        self.touch("task.md", changed=True)
        self.assertEqual(self.prompt(self.read("routing.md")), "")
        self.assertEqual(self.prompt(), "")

    def test_a_name_inside_another_name_or_another_checkout_is_no_read(self):
        self.touch("task.md", changed=True)
        self.assertEqual(self.prompt(("Bash", {"command": f"cat {self.refs}/work-task.md"}),
                                     ("Bash", {"command": "cat /elsewhere/references/task.md"}),
                                     ("Read", {"file_path": "/elsewhere/references/task.md"})), "")

    def test_a_missing_transcript_names_nothing(self):
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(self.plugin))
        out = subprocess.run([str(self.plugin / "scripts" / "reread.py")], input=json.dumps({"transcript_path": "/nope"}),
                             env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual((out.returncode, out.stdout), (0, ""))



# `issue list` answers the issues of `held.json` whose kind its arguments name, as `kind:<kind>`.
STOP_GH = r'''#!/usr/bin/env python3
import json, os, pathlib, re, sys
d = pathlib.Path(os.environ["FAKE"])
with open(d / "calls", "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
a = sys.argv[1:]
f = d / "held.json"
kinds = set(re.findall(r"kind:(\w+)", " ".join(a)))
print(json.dumps([{"url": i["url"]} for i in json.loads(f.read_text() if f.exists() else "[]") if i["kind"] in kinds]))
'''

CLAUDE = 100
HELD_GOAL = "https://github.com/o/r/issues/7"
HELD_TASK = "https://github.com/o/r/issues/8"


class Hook(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "gh").write_text(STOP_GH)
        (self.tmp / "gh").chmod(0o755)
        self.tree = self.tmp / "repo" / ".claude" / "worktrees" / "stop-guard-19-2"
        self.tree.mkdir(parents=True)

    def stop(self, agent_type="mumu-team:worker", cwd=None, goals=(), tasks=(), watch=None):
        (self.tmp / "held.json").write_text(json.dumps([{"url": u, "kind": "goal"} for u in goals]
                                                       + [{"url": u, "kind": "task"} for u in tasks]))
        table = [(1, 0, "launchd"), (CLAUDE, 1, "claude"), (200, 1, "claude --name other")]
        if watch is not None:
            table += [(300, watch, "/bin/zsh -c '\"/p/scripts\"/team-watch.py'"), (301, 300, "python3 /p/scripts/team-watch.py")]
        (self.tmp / "table").write_text("".join(f"{p:>6} {pp:>6} {c}\n" for p, pp, c in table))
        (self.tmp / "ps").write_text(f"#!/bin/sh\ncat '{self.tmp / 'table'}'\n")
        (self.tmp / "ps").chmod(0o755)
        payload = {"hook_event_name": "Stop", "session_id": "s", "cwd": str(cwd or self.tree), "stop_hook_active": False}
        if agent_type:
            payload["agent_type"] = agent_type
        commands = [h["command"] for entry in json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"].get("Stop", [])
                    for h in entry["hooks"]]
        env = dict(os.environ, FAKE=str(self.tmp), CLAUDE_PLUGIN_ROOT=str(PLUGIN), PATH=f"{self.tmp}:{os.environ['PATH']}",
                   CLAUDE_PID=str(CLAUDE))
        outs = [subprocess.run(c, shell=True, input=json.dumps(payload), env=env, capture_output=True, text=True, timeout=30)
                for c in commands]
        calls = (self.tmp / "calls").read_text().splitlines() if (self.tmp / "calls").exists() else []
        return outs, calls

    def refused(self, outs):
        return any(o.returncode == 2 or o.stdout.strip() and json.loads(o.stdout).get("decision") == "block" for o in outs)

    def reason(self, outs):
        return "".join(json.loads(o.stdout)["reason"] for o in outs if o.stdout.strip())


class OtherStop(Hook):
    def test_worker_with_an_open_task_and_no_pull_request_stops_and_reads_nothing(self):
        outs, calls = self.stop(goals=[HELD_GOAL], tasks=[HELD_TASK])
        self.assertFalse(self.refused(outs), outs)
        self.assertTrue(outs and all(o.returncode == 0 for o in outs), outs)
        self.assertEqual(calls, [])

    def test_session_without_lead_agent_stops_and_reads_nothing(self):
        for agent_type in (None, "mumu-team:reviewer", "general-purpose"):
            with self.subTest(agent_type=agent_type):
                outs, calls = self.stop(agent_type=agent_type, goals=[HELD_GOAL])
                self.assertFalse(self.refused(outs), outs)
                self.assertEqual(calls, [])


class LeadStop(Hook):
    def lead(self, **kwargs):
        return self.stop(agent_type="mumu-team:lead", cwd=self.tmp / "repo", **kwargs)

    def test_open_root_goal_without_team_watch_is_refused_naming_the_command(self):
        for watch in (None, 200):  # none, or another session's
            with self.subTest(watch=watch):
                outs, calls = self.lead(goals=[HELD_GOAL], watch=watch)
                self.assertTrue(self.refused(outs))
                self.assertIn("team-watch.py", self.reason(outs))
                self.assertIn(HELD_GOAL, self.reason(outs))
                self.assertIn("no:parent-issue", " ".join(json.loads(calls[0])))

    def test_open_root_task_alone_without_team_watch_is_refused(self):
        outs, _ = self.lead(tasks=[HELD_TASK])
        self.assertTrue(self.refused(outs))
        self.assertIn(HELD_TASK, self.reason(outs))
        self.assertFalse(self.refused(self.lead(tasks=[HELD_TASK], watch=CLAUDE)[0]))

    def test_lead_stops_otherwise(self):
        for kwargs in ({"goals": [HELD_GOAL], "watch": CLAUDE}, {}, {"watch": CLAUDE}):
            with self.subTest(**kwargs):
                outs, _ = self.lead(**kwargs)
                self.assertFalse(self.refused(outs), outs)


SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"

# One fake for both tools: poll i reads `<tool>.<i>` (else the highest one below it); a file holding `FAIL` exits 1.
# gh answers only the issues whose kind its arguments name, as `kind:<kind>`.
WATCH_FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, re, sys
d, tool = pathlib.Path(os.environ["WATCH_FAKE"]), pathlib.Path(sys.argv[0]).name
count = d / f"{tool}.count"
i = int(count.read_text()) if count.exists() else 0
count.write_text(str(i + 1))
answer = max((p for p in d.glob(f"{tool}.[0-9]*") if int(p.suffix[1:]) <= i), key=lambda p: int(p.suffix[1:]), default=None)
text = answer.read_text() if answer else "[]"
if text.strip() == "FAIL":
    sys.exit(1)
if tool == "gh":
    a = sys.argv[1:]
    kinds = set(re.findall(r"kind:(\w+)", " ".join(a)))
    text = json.dumps([{"url": i["url"]} for i in json.loads(text) if i["kind"] in kinds])
print(text)
'''


class TeamWatch(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.checkout = self.tmp / "repo"
        (self.checkout / ".claude" / "worktrees").mkdir(parents=True)
        for tool in ("herdr", "gh"):
            (self.tmp / tool).write_text(WATCH_FAKE)
            (self.tmp / tool).chmod(0o755)

    def herdr(self, poll, *agents):
        """herdr's answer from poll `poll` on: `(name, status, in this checkout)` per agent, or `FAIL`."""
        text = "FAIL" if agents == ("FAIL",) else json.dumps({"result": {"agents": [
            {"name": n, "agent_status": s, "cwd": str(self.checkout / ".claude" / "worktrees" / n if mine else self.tmp / "other" / n)}
            for n, s, mine in agents]}})
        (self.tmp / f"herdr.{poll}").write_text(text)

    def goals(self, poll, *urls, kind="goal"):
        """The open parentless issues from poll `poll` on, each of `kind`, or `FAIL`."""
        (self.tmp / f"gh.{poll}").write_text("FAIL" if urls == ("FAIL",) else json.dumps([{"url": u, "kind": kind} for u in urls]))

    def run_watch(self, ticks, idle="1000", role=None):
        env = dict(os.environ, WATCH_FAKE=str(self.tmp), PATH=f"{self.tmp}:{os.environ['PATH']}",
                   MONITOR_POLL="0.01", MONITOR_TICKS=str(ticks), TEAM_WATCH_IDLE=idle)
        env.pop("MUMU_ROLE", None)
        if role:
            env["MUMU_ROLE"] = role
        done = subprocess.run([sys.executable, str(SCRIPTS / "team-watch.py")], cwd=self.checkout, env=env,
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.splitlines()

    def polls(self, tool):
        count = self.tmp / f"{tool}.count"
        return int(count.read_text()) if count.exists() else 0

    def test_no_goals_runs_every_poll_silently(self):
        self.herdr(0)
        self.goals(0)
        self.assertEqual(self.run_watch(ticks=30, idle="0"), [])
        self.assertEqual(self.polls("herdr"), 30)

    def test_a_failing_call_skips_one_poll_and_the_loop_goes_on(self):
        self.herdr(0, ("fix-a-12-1", "working", True))
        self.herdr(3, "FAIL")
        self.herdr(4, ("fix-a-12-1", "blocked", True))
        self.goals(0, "FAIL")
        self.assertEqual(self.run_watch(ticks=8, idle="0"), ["blocked fix-a-12-1"])
        self.assertEqual(self.polls("herdr"), 8)

    def test_each_worker_state_change_prints_one_line(self):
        self.herdr(0, ("fix-a-12-1", "working", True), ("other-lead-9-1", "idle", False), ("repo-lead", "idle", True))
        self.herdr(2, ("fix-a-12-1", "blocked", True), ("other-lead-9-1", "blocked", False))
        self.herdr(4, ("fix-a-12-1", "unknown", True))
        self.herdr(6, ("fix-a-12-1", "working", True))
        self.herdr(8)
        self.assertEqual(self.run_watch(ticks=10), ["blocked fix-a-12-1", "working fix-a-12-1", "gone fix-a-12-1"])

    def test_no_working_worker_for_the_idle_period_prints_one_idle_line(self):
        self.herdr(0, ("fix-a-12-1", "idle", True))
        self.goals(0, "https://github.com/o/r/issues/7")
        lines = self.run_watch(ticks=20, idle="0.05")
        self.assertEqual(lines[0], "idle fix-a-12-1")
        self.assertEqual(lines[1:], ["team idle 0m"])

    def test_a_root_task_alone_prints_the_idle_line(self):
        self.herdr(0, ("fix-a-12-1", "idle", True))
        self.goals(0, "https://github.com/o/r/issues/8", kind="task")
        self.assertEqual(self.run_watch(ticks=20, idle="0.05")[1:], ["team idle 0m"])
        self.goals(0, "https://github.com/o/r/issues/9", kind="backlog")
        self.assertEqual(self.run_watch(ticks=20, idle="0.05")[1:], [])

    def test_a_working_worker_prints_no_idle_line(self):
        self.herdr(0, ("fix-a-12-1", "working", True))
        self.goals(0, "https://github.com/o/r/issues/7")
        self.assertEqual(self.run_watch(ticks=20, idle="0"), [])

    def test_in_a_worker_session_it_exits_at_once(self):
        self.herdr(0, ("fix-a-12-1", "blocked", True))
        self.assertEqual(self.run_watch(ticks=0, role="worker"), [])
        self.assertEqual(self.polls("herdr"), 0)


if __name__ == "__main__":
    unittest.main()
