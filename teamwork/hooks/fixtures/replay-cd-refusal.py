#!/usr/bin/env python3
"""Send a worker's `cd` into the live checkout through route-event.py from a worktree of a temporary repository, run the command its refusal offers, and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-cd-refusal.py [--case <name>]   (no argument: every one in turn)
- git: `cd <live>/teamwork && git ls-files` is denied with a command that has no cd and prints what the cd command printed
- path: `cd <live>/teamwork && cat note.txt | head -1 && ls .` is denied with a command that has no cd and prints what the cd command printed
- subshell: `(cd <live>/teamwork && cat note.txt)` is denied with a command that has no cd and prints what the cd command printed
- listing: `cd <live>/teamwork && ls`, then a `sed -n`, a `cut` and a `head -n 1` of a file, and a `grep -m 1`, each denied with such a command
- script: `cd <live>/teamwork && ls scripts; python3 scripts/read-board.py 3 --as worker 2>&1 | head -5` is denied with such a command
- direct: `cd <live>/teamwork && git log --oneline -1 && grep -c the note.txt; scripts/status.sh status 2>&1 | tail -1` is denied with such a command
- again: `cd <live>/teamwork && cat note.txt && cd /tmp && echo done` is denied with such a command that keeps the second cd
- chain: from the worktree, a second cd is read from the folder the first reached when `&&`, `;` or `(` joins them, and from the worktree when a pipe, `||` or a closed subshell does, so each of CHAINS is denied or passes as it says, a redirect on the first cd included
- real: each cd call of the transcripts under ~/.claude/projects that an independent reading calls a read gets a rewrite, and none whose later commands write gets one; passes when there are no transcripts
- writes: `cd <live>/teamwork && <command>` is denied with no command offered for each command of WRITES, a write, a cd again, or a command whose effect the rewrite cannot know"""
import glob
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import replay_probe  # noqa: E402

ROUTE = pathlib.Path(__file__).resolve().parents[1] / "route-event.py"
COMMANDS = {"git": "cd {live}/teamwork && git ls-files",
            "path": "cd {live}/teamwork && cat note.txt | head -1 && ls .",
            "subshell": "(cd {live}/teamwork && cat note.txt)",
            "listing": "cd {live}/teamwork && ls; sed -n 1,2p note.txt; cut -c1-4 note.txt | head -1; head -n 1 note.txt; grep -m 1 the note.txt",
            "script": "cd {live}/teamwork && ls scripts; python3 scripts/read-board.py 3 --as worker 2>&1 | head -5",
            "direct": "cd {live}/teamwork && git log --oneline -1 && grep -c the note.txt; scripts/status.sh status 2>&1 | tail -1",
            "again": "cd {live}/teamwork && cat note.txt && cd /tmp && echo done"}
WRITES = ("cp note.txt copy.txt", "git add . && git commit -m x", "git log && cd .. && git log", "cat note.txt; cd ..; git log", "sed -i '' s/a/b/ note.txt",
          "git log abc#1 -- note.txt", "rm -rf sub", "cat note.txt | tee new.txt", "sort -o out note.txt", "grep -f note.txt note.txt", "git log --output=out.txt",
          "cat note.txt > copy.txt", "cat note.txt >> copy.txt", "echo x > new.txt", "touch new.txt", "mkdir sub2", "git commit -qm x", "git checkout -b x", "git fetch",
          "git pull", "cat note.txt && rm note.txt", "python3 -c 'print(1)'", "python3 - <<'E'\nprint(1)\nE", "python3 -m http.server", "just build", "cat $HOME/note.txt",
          "cat *.txt", "cat `pwd`/note.txt", "for f in note.txt; do cat $f; done", "echo x | python3 -", "sed -n 1p note.txt > out.txt", "cat note.txt &",
          "/bin/rm note.txt", "/usr/bin/touch new.txt", "/usr/bin/git commit -qm x", "cat note.txt; cd /tmp && rm -rf x", "cat note.txt && cd /tmp && git commit -qm x",
          "git grep -O'touch z' the", "git ls-remote --upload-pack='touch z' .", "git -c core.pager='touch z' log", "sed -n 'w out.txt' note.txt", "sed 's/a/b/w out.txt' note.txt",
          "sed -i2 s/a/b/ note.txt", "echo 'rm note.txt' | sh -s a", "echo 'rm note.txt' | bash -s a", "gh issue create -t x", "gh api repos/x/y/issues -f title=x",
          "gh api repos/x/y/issues/1 -X PATCH", "gh api graphql -f query=x",
          "git grep --open-f='touch z' the", "git ls-remote --upload='touch z' .", "gh api repos/x/y -fa=b", "gh api repos/x/y -Fa=b", "gh api repos/x/y -XPOST", "cat only-here.txt",
          "cat note.txt #'\nrm note.txt\n#'", "echo 'touch pwn' | sh /dev/stdin", "git log \"${X:---output=pwn}\"", "cat \"$PWD/note.txt\"", "sed -I p s/a/b/ note.txt", "file -C -m x",
          "tree -R", "tree -L 1", "ls -I x", "gh api repos/x/y --method post", "grep -rn the", "wc -l", "git grep -EOecho the", "cat note.txt | grep -rn the", "cat note.txt; cd /no/such/dir; cat note.txt", "cat note.txt && cd LIVE/teamwork/.. && ls",
          "cat note.txt & cat note.txt", "gh pr view", "gh pr diff", "echo \"'$(touch z)'\"", "git log --grep=\"'$(touch z)'\"", "wc -l note.txt", "du", "file note.txt", "grep the note.txt 1", "head note.txt 1",
          "grep -rn the .", "ls -R", "ls -d .", "sed -n 's/[/]/;p;s/;w d/r/g' note.txt", "grep the note.txt nonexist.txt", "ls note.txt", "grep -l the note.txt", "tail -v -n 1 note.txt", "python3 ../outside.py", "sed -n '/a\\/p;/w ./p' note.txt", "python3 scripts/read-board.py 1", "../../../../../../../../../../../../../../bin/rm note.txt")
CHAINS = (("cd sub && cd ../../..", True), ("cd sub; (cd .. && cd ../..)", True), ("cd sub && cd ../.. && ls", False), ("(cd sub && cd ..); cd ../..", True),
          ("cd sub | cd ../..", True), ("cd sub && cd .. && cd ..", False), ("cd sub 2>/dev/null && cd ../../..", True), ("cd sub 2>&1 && cd ../.. && ls", False))
# a command word no cd call may be offered a rewrite for when it follows the cd, whatever its arguments
WRITING_WORD = re.compile(r"(?<![-\w/.])(?:rm|mv|cp|mkdir|touch|tee|ln|chmod|truncate|install|dd|patch|kill|curl|wget|just|make|npm|uvx)(?![-\w.])|(?<![0-9&>])>(?!&|/dev/null)|>>|\bsed\s+-\w*i"
                          r"|\bgit\s+(?:-C\s+\S+\s+)?(?:add|commit|push|pull|fetch|checkout|switch|merge|rebase|reset|stash|worktree|branch|tag|clean|restore|cherry-pick|config|clone|init|remote)(?![-\w])")
NAME_OPTIONS = {"head": "v", "tail": "v", "grep": "lLHrR", "rg": "lH", "ls": "dR"}
READ_WORDS = {"cat", "head", "tail", "wc", "ls", "grep", "sed", "cut", "echo", "tr", "nl", "stat", "file", "du", "diff", "rg", "git", "python3", "bash", "gh"}
READ_GIT_VERBS = {"status", "log", "diff", "show", "grep", "ls-files", "rev-parse", "blame", "describe", "shortlog", "cat-file", "ls-tree"}


def setup():
    work = pathlib.Path(tempfile.mkdtemp(prefix="cd-refusal-"))
    live = work.resolve() / "live"
    (live / "teamwork" / "scripts").mkdir(parents=True)
    (live / "teamwork" / "note.txt").write_text("the live note\nthe second line\n")
    (live / "teamwork" / "1").write_text("a file named like an option's value\n")
    (live / "teamwork" / "scripts" / "read-board.py").write_text("import pathlib, sys\nprint(sys.argv[1:], sorted(p.name for p in pathlib.Path(__file__).resolve().parents[1].iterdir()))\n")
    (live / "teamwork" / "scripts" / "status.sh").write_text("#!/bin/sh\necho \"status $1 $(ls \"$(dirname \"$0\")\" | tr '\\n' ' ')\"\n")
    (live / "teamwork" / "scripts" / "status.sh").chmod(0o755)
    for command in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "first"]):
        subprocess.run(["git", *command], cwd=live, check=True, capture_output=True)
    worktree = live / ".claude" / "worktrees" / "w"
    worktree.mkdir(parents=True)
    (worktree / "only-here.txt").write_text("a name only the worktree holds\n")
    stubs = replay_probe.fake_herdr(work, [{"pane_id": "p1", "name": "t-worker"}])
    return stubs, live, worktree


def hook_reason(stubs, worktree, command):
    event = {"hook_event_name": "PreToolUse", "cwd": str(worktree), "tool_input": {"command": command}}
    hook = replay_probe.route_event(ROUTE, event, stubs).get("hookSpecificOutput", {})
    return hook.get("permissionDecision") == "deny" and hook.get("permissionDecisionReason", "")


def offered(reason):
    found = re.search(r"run this instead: `([^`]+)`", reason or "")
    return found and found[1]


def check_read(stubs, live, worktree, command):
    """None when the refusal of COMMAND offers a command with no cd of the live folder that prints what COMMAND printed, else the failure."""
    reason = hook_reason(stubs, worktree, command)
    if not reason:
        return "the hook did not deny the cd"
    if not (rewrite := offered(reason)):
        return f"the refusal names no full command: {reason!r}"
    if re.search(rf"(^|[;&|({{]|\s)(cd|pushd)\s+{re.escape(str(live))}", rewrite):
        return f"the offered command still has a cd: {rewrite}"
    want = subprocess.run(["bash", "-c", command], cwd=worktree, capture_output=True, text=True)
    got = subprocess.run(["bash", "-c", rewrite], cwd=worktree, capture_output=True, text=True)
    if (got.returncode, got.stdout) != (want.returncode, want.stdout) or not want.stdout:
        return f"the offered command printed {got.stdout!r} (exit {got.returncode}), not {want.stdout!r} (exit {want.returncode}): {got.stderr.strip()[-200:]}"
    return None


def reads_only(tail, folder, root):
    """Whether TAIL, the text after a cd into FOLDER of the checkout ROOT, holds only commands of READ_WORDS with no expansion, redirect to a file, glob, loop or cd; read here by words, apart from the hook's reading."""
    if re.search(r"[$`]|(?:^|\s)#|~[+-]", re.sub(r"'[^']*'", "''", tail)):
        return False  # an expansion inside double quotes still runs, and a comment hides what follows it
    text = re.sub(r"'[^']*'|\"[^\"]*\"", "''", re.sub(r"2>&1|2>/dev/null|>/dev/null", "", tail))
    if re.search(r"[$`<>*?\[\]~#(){}\\]|\b(?:cd|pushd)\b", text):
        return False
    for stage in re.split(r"&&|\|\||[;|\n]", text):
        words = stage.split()
        if not words:
            continue
        if words[0] not in READ_WORDS or words[0] == "git" and (words[1:2] or [""])[0] not in READ_GIT_VERBS:
            return False
        if any(word.startswith("-") and re.search(r"[feiw]", word[1:]) for word in words[1:] if words[0] in ("sed", "grep", "stat", "cut", "sort", "rg")):
            return False
        if words[0] == "gh" and not (words[1:2] == ["api"] and not re.search(r"graphql|\s-[XfF]\b|--(?:method|field|raw-field|input)", stage)):
            return False
        existing = [word for word in words[1:] if not word.startswith("-") and os.path.exists(os.path.join(folder, word))]
        if words[0] in ("wc", "du", "file", "stat", "diff", "tree") and (existing or words[0] in ("du", "tree") and len(words) == 1):
            return False  # these print the operand's name, which the rewrite makes an absolute path
        if words[0] in ("ls", "head", "tail", "grep", "rg") and (len(existing) > 1 or any(re.match(rf"-[A-Za-z]*[{NAME_OPTIONS[words[0]]}]", word) for word in words[1:]) \
                or words[0] in ("grep", "rg") and any(os.path.isdir(os.path.join(folder, word)) for word in existing)
                or words[0] == "ls" and any(os.path.isfile(os.path.join(folder, word)) for word in existing)):
            return False
        if words[0] in ("python3", "bash") and (len(words) < 2 or words[1].startswith("-") or not re.search(r"\.(py|sh)$", words[1]) or not os.path.isfile(os.path.join(folder, words[1])) or not (os.path.realpath(os.path.join(folder, words[1])) + "/").startswith(root + "/") or any(os.path.exists(os.path.join(folder, word)) for word in words[2:])):
            return False
    return True


def real_calls():
    """{(command, cwd)} of the Bash calls in the transcripts under ~/.claude/projects made from a worktree that enter a cd."""
    found = set()
    for path in glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")) + glob.glob(os.path.expanduser("~/.claude/projects/*/*/subagents/*.jsonl")):
        try:
            lines = pathlib.Path(path).read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if '"command"' not in line or not re.search(r"\b(?:cd|pushd)\b", line) or "/.claude/worktrees/" not in line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            content = (event.get("message") or {}).get("content")
            for part in content if isinstance(content, list) else ():
                if isinstance(part, dict) and part.get("name") == "Bash" and "/.claude/worktrees/" in (event.get("cwd") or ""):
                    found.add(((part.get("input") or {}).get("command", ""), event["cwd"]))
    return found


def check_real():
    """None when every real cd call that the hook refuses and only reads is offered a rewrite and none that writes is, else the first failure."""
    spec = importlib.util.spec_from_file_location("route_event", ROUTE)
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    for command, cwd in sorted(real_calls()):
        entered = hook.live_change_directory(command, cwd)
        found = next((match for match in hook.CHANGE_DIRECTORY.finditer(command) if entered and os.path.normpath(os.path.join(cwd, os.path.expanduser(match[1].strip("\"'")))) == entered[0]), None)
        if not entered or not found:
            continue
        tail = command[found.end():]
        before_later_cd = re.split(r"[;&|(\n]\s*(?:cd|pushd)\s", tail)[0]  # what runs after a later cd runs in its folder
        if entered[2] and WRITING_WORD.search(re.sub(r"'[^']*'|\"[^\"]*\"", "''", before_later_cd)):
            return f"a write was offered a rewrite: {command[:200]!r}"
        if not entered[2] and not command[:found.start()].strip() and re.match(r"\s*(?:&&|;)", tail) and reads_only(tail, entered[0], cwd.split("/.claude/worktrees/")[0]):
            return f"a read was offered none: {command[:200]!r}"
    return None


def main(args):
    if not args:
        return replay_probe.run_every(__file__, "--case", (*COMMANDS, "chain", "real", "writes"))
    if len(args) != 2 or args[0] != "--case" or args[1] not in (*COMMANDS, "chain", "real", "writes"):
        print(__doc__, file=sys.stderr)
        return 2
    stubs, live, worktree = setup()
    if args[1] == "real":
        problem = check_real()
    elif args[1] == "chain":
        problem = next((f"{command!r} " + ("was not denied" if denied else "was denied") for command, denied in CHAINS
                        if bool(hook_reason(stubs, worktree, command)) != denied), None)
    elif args[1] == "writes":
        problem = next((f"{risky!r} " + ("was not denied" if not said else "was offered a rewrite: " + said[said.index("run this instead"):][:200])
                        for risky in WRITES if not (said := hook_reason(stubs, worktree, f"cd {live}/teamwork && {risky.replace('LIVE', str(live))}")) or "run this instead" in said), None)
    else:
        problem = check_read(stubs, live, worktree, COMMANDS[args[1]].format(live=live))
    if problem:
        return replay_probe.fail(problem)
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
