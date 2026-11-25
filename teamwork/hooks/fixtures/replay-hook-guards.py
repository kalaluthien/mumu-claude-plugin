#!/usr/bin/env python3
"""Send a worker's Bash commands through route-event.py and print `ok <case>` or `fail <case>: <what differed>` per case, then `PASS hook guards` as the last line when every
case holds, else `FAIL hook guards`, and exit 1 on any failure.

usage: replay-hook-guards.py
- missing: a script of this plugin that does not exist is denied naming the plugin's script of that name wherever it stands as a word, in any command, `if`, `while`, `else`, `sh -c '...'`, `eval`, a substitution or
  a backtick included, by `${CLAUDE_PLUGIN_ROOT}`, `$CLAUDE_PLUGIN_ROOT` or `~/`; the same path as the target of `mv`, `cp` or a redirect, an operand of `git` or `ls`, in a quoted message, a heredoc body
  or a comment, the code of `python3 -c`, behind another variable or a substitution, or as an existing script, passes; a relative path is read from the event's `cwd`, not the hook's folder
- github: each spelling of a `gh` issue write, with `gh` quoted, escaped or by its path, or a bundled `-fbody=x` or `-iXPOST`, is denied; reads, a quoted `gh` that is only an
  argument, an empty word, and a write to a pull request pass, with no error on stderr
- quotes: a call with no command, a null one or a command of 30000 quotes, and a command with an escaped quote inside quotes, or any of a few hundred generated from quotes, escapes, heredocs and joiners, ends 0 with nothing on stderr, never raises or hangs
- order: a session whose name ends in no role gets no answer and no `ps` run, by the hook or by `list-sessions.py --me`, while the worker's own run does call `ps`"""
import json
import os
import random
import pathlib
import shutil
import subprocess
import sys
import tempfile

TIMEOUT = 20  # seconds a hook call may take, since a hook that loops must fail the runner, not hang it
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import replay_probe  # noqa: E402

PLUGIN = pathlib.Path(__file__).resolve().parents[2]
ROUTE = PLUGIN / "hooks" / "route-event.py"
LIST_SESSIONS = PLUGIN / "skills" / "kick-off" / "scripts" / "list-sessions.py"
GONE = f"{PLUGIN}/skills/kick-off/scripts/gone-script.py"
STALE = f"{PLUGIN}/scripts/use-board.py"
# a command and whether it is denied
MISSING = (
    (f"python3 {GONE}", True), (f"python3 -u {GONE} --x", True), (f"/usr/bin/python3.12 {GONE}", True), (f"bash {GONE}", True), (f"sh {GONE}", True), (GONE, True),
    (f"cd sub && python3 {GONE}", True), (f"python3 2>/dev/null {GONE}", True), (f"python3 {GONE} > run.log 2>&1", True), (f"ls; (python3 {GONE})", True), (f"A=1 python3 {GONE}", True), (f"python3 {GONE} | cat", True), (f"echo hi\npython3 {GONE}", True),
    (f"python3 -X dev {GONE}", True), (f"python3 -W ignore {GONE}", True), (f"if true; then python3 {GONE}; fi", True), (f"for i in 1; do python3 {GONE}; done", True), (f"{{ python3 {GONE}; }}", True), (f"! python3 {GONE}", True),
    (f"env python3 {GONE}", True), (f"env A=1 -u B python3 {GONE}", True), (f"time python3 {GONE}", True), (f"nohup python3 {GONE} &", True), (f"timeout 5 python3 {GONE}", True), (f"timeout -s KILL 5s bash {GONE}", True),
    (f"xargs -I {{}} python3 {GONE}", True), (f"exec python3 {GONE}", True), (f"command python3 {GONE}", True), (f"sudo -u me sh {GONE}", True), (f"uv run python3 {GONE}", True), (f"uv run --with x {GONE}", True), (f"nohup env time {GONE}", True),
    (f"if true; then echo y; elif python3 {GONE}; then :; fi", True), (f"if python3 {GONE}; then :; fi", True), (f"if ! python3 {GONE}; then :; fi", True), (f"while python3 {GONE}; do :; done", True),
    (f"until python3 {GONE}; do :; done", True), (f"if false; then :; else python3 {GONE}; fi", True), (f"sh -c 'python3 {GONE}'", True), (f"bash -c \"cd sub && python3 {GONE}\"", True),
    (f"eval 'python3 {GONE}'", True), (f"eval python3 {GONE}", True), (f"echo $(python3 {GONE})", True), (f"echo `python3 {GONE}`", True), (f"echo \"$(python3 {GONE})\"", True),
    (f"python3 \"{GONE}\"", True), (f"python3 '{GONE}'", True), (f"\"python3\" \"{GONE}\"", True), (f"python3 \"${{CLAUDE_PLUGIN_ROOT}}/skills/kick-off/scripts/gone-script.py\"", True),
    (f"case x in y) python3 {GONE} ;; esac", True), (f"python3 a.py\npython3 {GONE}", True), (f"ls x.py\n{GONE}", True), ("python3 $HOME/teamwork/gone-script.py", True), ("python3 ${HOME}/teamwork/gone-script.py", True),
    (f"echo \"$(python3 '{GONE}')\"", True), (f"bash -c \"python3 '{GONE}'\"", True), (f"python3 a.py {GONE}", False), (f"echo \"\" {GONE}", False), (f"echo sh -c 'python3 {GONE}'", False), (f": # python3 {GONE}", False), (f"ls x; true # it's python3 {GONE}", False), (f"python3 \"x {GONE}\"", False), (f"echo \"{GONE}\"", False), (f"echo '$(python3 {GONE})'", False),
    ("python3 ~/teamwork/present-script.py", False), ("python3 $HOME/teamwork/present-script.py", False), ("python3 ${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/use-board.py read 1", False),
    ("python3 $CLAUDE_PLUGIN_ROOT/skills/kick-off/scripts/use-board.py read 1", False), ("$(pwd)/teamwork/gone-script.py", False),
    (f"env FOO=1", False), (f"timeout 5", False), (f"then", False),
    ("python3 ${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/gone-script.py", True), ("python3 $CLAUDE_PLUGIN_ROOT/skills/kick-off/scripts/gone-script.py", True),
    ("python3 ~/teamwork/gone-script.py", True), (f"python3 {STALE}", True),
    (f"mv old.py {GONE}", False), (f"mv old.py \\\n {GONE}", False), (f"cp {GONE} copy.py", False), (f"echo x > {GONE}", False), (f"> {GONE}", False), (f">{GONE} echo hi", False), (f"echo x 2>&1 >{GONE}", False), (f"cat < {GONE}", False), (f"git log -- {GONE}", False),
    (f"git add {GONE}", False), (f"ls {GONE}", False), (f"echo \"python3 {GONE}\"", False), (f"git commit -m 'ran python3 {GONE}'", False),
    (f"cat <<'EOF'\npython3 {GONE}\nEOF", False), (f"cat > notes.md <<'EOF'\n{GONE}\nEOF", False), (f"echo ok # python3 {GONE}", False), (f"python3 -c {GONE}", False),
    (f"python3 -m {GONE}", False), (f"python3 -X dev -c {GONE}", False), (f"time echo {GONE}", False), (f"env A=1 ls {GONE}", False), (f"sudo cat {GONE}", False), (f"timeout 5 mv x {GONE}", False), (f"python3 other.py {GONE}", False), (f"python3 $OTHER/teamwork/gone-script.py", False), ("python3 `pwd`/teamwork/gone-script.py", False),
    (f"python3 {PLUGIN}/skills/kick-off/scripts/use-board.py read 1", False), (f"echo \"unclosed {GONE}", False),
    ("python3 sub/teamwork/present-script.py", False), ("python3 sub/teamwork/gone-script.py", True))
WRITES = ("cat <<EOF | sh\ngh issue create\nEOF", "gh api repos/o/r/sub_issues -f a=b", "gh api repos/o/r/dependencies -f a=b", "bash /dev/stdin <<< 'gh issue create'", "echo hi; eval \"gh\" issue create", "bash -lc 'gh issue create'", "bash --command='gh issue create'", "pwsh -Command \"gh issue create\"", "eval -- gh issue create", "gh --paginate issue create", "gh api --input f.json repos/o/r/issues",
          "gh api -H 'A: b' repos/o/r/issues -f body=x", "gh api repos/o/r/issues -X PATCH", "gh api repos/o/r/issues -XDELETE", "gh api repos/o/r/issues --method PUT", "gh api graphql --raw-field query='mutation{createIssue{id}}'",
          "echo 'gh issue create' | env sh -s", "sudo -u me gh issue create", "gh issue \"create\" -t x", "\"gh\" \"issue\" \"create\" -t x", "gh api repos/o/r/issues -X \"POST\"", "gh api repos/o/r/issues --method \"POST\"", "gh api repos/o/r/issues \"-f\" body=x",
          "gh api repos/o/r/issues -X POST", "gh api repos/o/r/issues --method=POST", "gh -R o/r issue 'comment' 1", "if gh issue close 1; then :; fi", "sh -c \"gh issue 'create'\"", "echo $(\"gh\" issue create)", "case x in y) gh issue create ;; esac",
          "echo \"$(gh api repos/o/r/issues --field a=b)\"", "bash <<< 'gh issue create'", "bash <<EOF\ngh issue create\nEOF", "gh api graphql -f query='mutation { addComment(input: {}) { id } }'",
          "gh issue create -t x", "gh issue comment 1 -b x", "\"gh\" issue create -t x", "\\gh issue comment 1 -b x", "g'h' issue close 1", "\"/usr/bin/gh\" issue create -t x",
          "/usr/bin/gh issue create -t x", "gh api repos/o/r/issues -fbody=x", "gh api repos/o/r/issues -Fbody=x", "\"gh\" api repos/o/r/issues -fbody=x",
          "gh api repos/o/r/issues/1/comments -iXPOST", "gh api -XPOST repos/o/r/issues", "gh api repos/o/r/issues -f body=x", "echo y; \"gh\" issue edit 1 -t x",
          "cd sub && \\gh issue lock 1", "echo gh api repos/o/r/issues -fbody=x | sh", "gh issue develop 1 -b x")
READS = ("cat <<EOF | cat\ngh issue create\nEOF", "gh api repos/o/r/pulls -f body=x -q issues", "gh api repos/o/r/pulls -f body=x -t issues", "gh api repos/o/r/pulls -H 'issues: x' -f body=x", "gh api repos/o/r/pulls -f body=x --jq issues", "gh api repos/o/r/pulls --header issues -f body=x",
         "gh api --input issues.json repos/o/r/pulls", "echo sh -c 'gh issue create'", "echo bash -c 'gh issue create'", "ls eval gh issue create", ": # gh issue create", "echo 'gh issue create' || sh", "echo 'gh issue create' ; sh", "gh pr comment issue", "gh api repos/o/r/issues --jq .x", "gh api -q .x repos/o/r/issues", "gh api -H 'A: b' repos/o/r/issues", "gh api repos/o/r/issues -X GET --input f.json", "bash -x script.sh <<< 'gh issue create'", "echo 'gh issue create' | bash script.sh", "gh --version", "env gh", "gh issue \"list\"", "gh api repos/o/r/issues --method \"GET\" -f state=open", "gh api repos/o/r/issues -X \"GET\"", "gh -R o/r issue view 1", "gh api repos/o/r/pulls \"-f\" body=x", "git commit -m \"gh issue create\"", "cat <<EOF\ngh issue create\nEOF",
         "echo 'gh issue create' | cat", "gh pr comment 1 -b x", "gh api graphql -f query='query { viewer { login } }'", "gh issue list --search 'comment'",
         "gh issue list", "gh issue view 1", "gh api repos/o/r/issues", "gh api repos/o/r/issues -XGET", "gh api repos/o/r/issues -iXGET -f state=open",
         "gh api repos/o/r/issues --method GET -f state=open", "echo \"gh\" issue create -t x", "\"gh issue\" create", "echo \"\"; gh issue list", "gh api repos/o/r/pulls -fbody=x", "gh api repos/o/r/pulls/1/comments -iFbody=\"see issues\"",
         "\"\" issue create", "echo ok")
failed = []


def step(name, problem):
    print(f"fail {name}: {problem}" if problem else f"ok {name}", flush=True)
    failed.extend([name] if problem else [])


def ask(stubs, name, command, cwd):
    """(the hook's decoded answer, its exit status, its stderr) to COMMAND as a worker called NAME."""
    event = {"hook_event_name": "PreToolUse", "cwd": str(cwd), "tool_input": {"command": command}}
    environment = {**os.environ, "PATH": f"{stubs}:{os.environ['PATH']}", "HERDR_PANE_ID": "p1"}
    argv = replay_probe.as_claude([ROUTE], ["--name", name], pathlib.Path(stubs).parent / "stand-in")
    try:
        done = subprocess.run(argv, input=json.dumps(event), capture_output=True, text=True, env=environment, timeout=TIMEOUT, cwd=PLUGIN)  # from a folder that is not the event's, so a relative path must be read from the event's
    except subprocess.TimeoutExpired:
        return {}, 124, f"no answer within {TIMEOUT} seconds"
    return (json.loads(done.stdout) if done.stdout.strip() else {}).get("hookSpecificOutput", {}), done.returncode, done.stderr


def verdict(stubs, command, denied, cwd, mention=None):
    """What differs from the expected answer to COMMAND: it is denied, and names MENTION in its reason, or it passes; None when nothing."""
    hook, status, error = ask(stubs, "t-worker", command, cwd)
    if status or error:
        return f"{command!r} ended {status}: {error.strip()[-200:]}"
    got = hook.get("permissionDecision") == "deny"
    if got != denied:
        return f"{command!r} was {'denied' if got else 'not denied'}"
    return mention and mention not in hook.get("permissionDecisionReason", "") and f"{command!r} was denied without naming {mention}" or None


def setup():
    work = pathlib.Path(tempfile.mkdtemp(prefix="hook-guards-"))
    stubs = replay_probe.fake_herdr(work, [{"pane_id": "p1", "name": "t-worker"}])
    (work / "sub").mkdir()
    os.environ["HOME"] = str(work)  # so `~/teamwork/gone-script.py` names a folder here
    (work / "teamwork").mkdir()
    (work / "teamwork" / "present-script.py").write_text("print('here')\n")
    (work / "sub" / "teamwork").mkdir()
    (work / "sub" / "teamwork" / "present-script.py").write_text("print('here')\n")
    return work, stubs


def missing(work, stubs):
    for command, denied in MISSING:
        answer = verdict(stubs, command, denied, work, mention="gone-script.py" if denied and "gone" in command else None)
        if answer:
            return answer
    hook = ask(stubs, "t-worker", f"python3 {STALE}", work)[0]
    named = f"{PLUGIN}/skills/kick-off/scripts/use-board.py"
    only = ask(stubs, "t-worker", f"python3 {GONE}", work)[0]
    return None if named in hook.get("permissionDecisionReason", "") and "nothing; find it" in only.get("permissionDecisionReason", "") \
        else f"the denial named {hook.get('permissionDecisionReason')!r} and {only.get('permissionDecisionReason')!r}"


def github(work, stubs):
    return next(filter(None, [verdict(stubs, command, True, work) for command in WRITES] + [verdict(stubs, command, False, work) for command in READS]), None)


PIECES = ("git commit -m ", "echo ", "gh issue list ", "python3 ", "\"", "'", "\\\"", "\\", "say \\\"hi\\\" there", "a\\\"b", "<<EOF\n", "\nEOF\n", "<<'X'\n", "\nX", "&&", ";", "|", "||", "&", "$(", ")", "`", "(", "{", "}", "!", " ", "\n", "#", ">", "2>&1", "<",
          "then ", "do ", "env ", "timeout 5 ", "gh ", "\\gh ", "g'h' ", "-fbody=x ", "api ", "-m ", "-c ", "-X dev ", f"{GONE} ", "~/x.py ", "$HOME ", "${", "$", "=")


def quotes(work, stubs):
    """Every command of escaped quotes and of PIECES put together at random ends 0 with nothing on stderr."""
    commands = ['git commit -m "say \\"hi\\" there"', 'echo "a\\"b"', "echo 'a\\'b'", 'gh issue list --jq "\\"x\\""', 'python3 -c "print(\\"hi\\")"', 'echo "a\\"', "echo \"\\\"\""]
    chance = random.Random(1491)
    commands += ["".join(chance.choice(PIECES) for _ in range(chance.randint(1, 12))) for _ in range(150)]
    commands += ["\"" * 30000, "'" * 30001, "$(" * 3000, "\"$(a)" * 3000, "eval " * 3000, "`" * 30000, "\\" * 30001 + "\"", "(" * 30000]
    for command in commands:
        hook, status, error = ask(stubs, "t-worker", command, work)
        if status or error:
            return f"{command!r} ended {status}: {error.strip()[-200:]}"
    for tool_input in ({"command": None}, {}, None):
        event = {"hook_event_name": "PreToolUse", "cwd": str(work), "tool_input": tool_input}
        done = subprocess.run(replay_probe.as_claude([ROUTE], ["--name", "t-worker"], pathlib.Path(stubs).parent / "stand-in"), input=json.dumps(event), capture_output=True, text=True,
                              env={**os.environ, "PATH": f"{stubs}:{os.environ['PATH']}", "HERDR_PANE_ID": "p1"}, timeout=TIMEOUT)
        if done.returncode or done.stderr or done.stdout.strip():
            return f"a Bash call with tool_input {tool_input!r} ended {done.returncode}: {done.stderr.strip()[-200:]}{done.stdout.strip()[-200:]}"
    return None


def order(work, stubs):
    """The `ps` a session's name check runs, logged by a stand-in first on `PATH`."""
    log = work / "ps.log"
    stub = replay_probe.write_text(stubs, "ps", f'#!/bin/sh\necho "$@" >> {log}\nexec {shutil.which("ps")} "$@"\n')
    stub.chmod(0o755)
    outcomes = []
    for name in ("t-worker", "t-probe"):
        replay_probe.fake_herdr(work, [{"pane_id": "p1", "name": name}])
        log.write_text("")
        hook, status, error = ask(stubs, name, "gh issue create -t x", work)
        asked = bool(log.read_text().strip())
        log.write_text("")
        environment = {**os.environ, "PATH": f"{stubs}:{os.environ['PATH']}", "HERDR_PANE_ID": "p1"}
        listed = subprocess.run(replay_probe.as_claude([sys.executable, LIST_SESSIONS, "--me"], ["--name", name], work / "stand-in"), capture_output=True, text=True, env=environment, timeout=TIMEOUT)
        outcomes.append((name, hook.get("permissionDecision"), asked, listed.stdout.strip(), bool(log.read_text().strip()), status or error))
    expected = [("t-worker", "deny", True, "t-worker", True, 0), ("t-probe", None, False, "", False, 0)]
    return None if [(*one[:5], one[5] or 0) for one in outcomes] == expected else f"each of the worker and the unroled session gave {outcomes}, not {expected}"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work, stubs = setup()
    step("missing", missing(work, stubs))
    step("github", github(work, stubs))
    step("quotes", quotes(work, stubs))
    step("order", order(work, stubs))
    print("FAIL hook guards" if failed else "PASS hook guards")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
