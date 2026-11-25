#!/usr/bin/env python3
"""Send a worker's `cd` into the live checkout through route-event.py from a worktree of a temporary repository, print `ok <case>` or `fail <case>: <what differed>`
per case, then `PASS cd never allowed` as the last line when every case holds, else `FAIL cd never allowed`, and exit 1 on any failure.

usage: replay-cd-refusal.py
- denied: each spelling of a cd into the live checkout in SPELLINGS, a symlink to it or to a folder in it, a `..` after a link in or out of it, and another letter case of its path where the file system ignores case, included, followed by a read, `git ls-remote`, `gh api` or a write, and each cd that opens a block, is
  refused with `permissionDecision: deny` naming the folder the shell stands in, `--repository <folder>` and `git -C <folder>`, and no answer of the hook holds `allow`
- chain: from the worktree, a second cd is read from the folder the first reached when `&&`, `;` or `(` joins them, and from the worktree when a pipe, `||` or
  a closed subshell does, so each of CHAINS is denied or passes as it says, a redirect on the first cd included
- quoted: a `cd <live>/teamwork` inside a quoted argument, a heredoc body or a comment passes, and one in a `$(...)`, or run after a heredoc or a quoted `&&`,
  is denied, each of QUOTED as it says
- gone: a cd into a live checkout whose folder is not on disk is refused by its path, and a cd out of it passes
- inside: a cd within the session's own worktree or outside the checkout passes with no answer"""
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import replay_probe  # noqa: E402

ROUTE = pathlib.Path(__file__).resolve().parents[1] / "route-event.py"
SPELLINGS = ("cd -P {live}/teamwork", "cd -L -- {live}/teamwork", "builtin cd {live}/teamwork", "command cd {live}/teamwork", "pushd -n {live}/teamwork",
             "LIVE={live}/teamwork; cd $LIVE", "export LIVE={live} && cd \"$LIVE/teamwork\"", "cd \"$TEAMWORK_LIVE_FOLDER/teamwork\"", "L={live}/teamwork; cd ${{L}}",
             "L={live}/teamwork; cd ${{L}}/.", "L={live}/teamwork; echo \"x; L=/tmp;\"; cd $L", "L={live}/teamwork; echo 'x; L=/tmp;'; cd $L", "L={live}/teamwork; # y; L=/tmp;\ncd $L",
             "L={live}/teamwork; false && L=/tmp; cd $L", "L=/tmp; false || L={live}/teamwork; cd $L", "cd \"$PWD/../../../teamwork\"",
             "cd .. && cd $PWD/../../teamwork", "cd .. && cd ${{PWD}}/../../teamwork", "A=1 L={live}/teamwork; cd $L", "export A=1 L={live}/teamwork && cd $L", "L=\"{live}\"/teamwork; cd $L",
             "L={live}; M=$L/teamwork; cd $M", "cd \"$TEAMWORK_LIVE_ALIAS/teamwork\"", "cd -P $TEAMWORK_LIVE_ALIAS/teamwork/..", "cd link", "cd -P link/..", "cd link/../", "cd {live}/teamwork/out/..", "L={live}/teamwork; cd ${{L%/}}", "cd $UNSET_FOR_CD_REPLAY",
             "command builtin cd {live}/teamwork", "command -p cd {live}/teamwork", "cd $'{live}/teamwork'", "cd $'{live}/team\\x77ork'", "cd $(echo {live}/teamwork)",
             "cd `echo {live}/teamwork`", "cd \"$(echo {live}/teamwork)\"", "command -p builtin cd $(echo {live}/teamwork)",
             "command -- cd {live}/teamwork", "command -p -- cd {live}/teamwork", "command -pp cd {live}/teamwork", "cd $'{live}/teamwork\\x00/../.claude/worktrees/w'", "cd $'{live}/teamwork\\0'",
             "cd $'{live}/teamwork\\u0000/x'",
             "cd $'{live}/teamwork\\c@/../../..'", "cd $'{live}/teamwork\\400/../../..'", "cd $'{live}/teamwork\\x00/../../..'", "cd $\"{live}/teamwork\"", "cd $'{live}/teamwork\\n'",
             "cd \"$PWD\"/../../../teamwork", "cd -P \"$PWD\"/../../../teamwork", "builtin cd \"$PWD\"/../../../teamwork", "cd '{live}'\"/teamwork\"", "L={live}; cd \"$L\"/teamwork",
             "cd $PWD/.. && cd ../..", "cd -P ${{PWD}}/.. && cd ../..", "builtin cd $PWD/.. && cd ../..", "L={live}/.claude/worktrees; cd $L && cd ../..")
BLOCKS = (("if true; then cd {live}/teamwork;", "fi"), ("for f in a b; do cd {live}/teamwork;", "done"), ("{{ cd {live}/teamwork;", "}}"), ("while true; do cd {live}/teamwork;", "done"),
          ("if true; then\n cd {live}/teamwork\n", "fi"))
BLOCKED = tuple(f"{opening} {risky}; {closer}" for opening, closer in BLOCKS for risky in ("rm note.txt", "git commit -qm x", "echo x > new.txt", "cd /tmp && rm note.txt")) \
    + ("if rm note.txt; then cd {live}/teamwork; git ls-files; fi", "if cat note.txt > out.txt; then cd {live}/teamwork; git ls-files; fi", "for f in $(rm note.txt); do cd {live}/teamwork; git ls-files; done",
       "if true; then cd {live}/teamwork; git ls-files; else rm note.txt; fi", "if true; then cd {live}/teamwork; git ls-files; fi; rm note.txt",
       "{{ cd {live}/teamwork; git ls-files; }} && rm note.txt", "{{ cd {live}/teamwork; git ls-files; }} > out.txt", "while rm note.txt; do cd {live}/teamwork; git ls-files; done",
       "if true; then cd $UNSET_FOR_CD_REPLAY; rm note.txt; fi")
CHAINS = (("cd sub && cd ../../..", True), ("cd sub; (cd .. && cd ../..)", True), ("cd sub && cd ../.. && ls", False), ("(cd sub && cd ..); cd ../..", True),
          ("cd sub | cd ../..", True), ("cd sub && cd .. && cd ..", False), ("cd sub 2>/dev/null && cd ../../..", True), ("cd sub 2>&1 && cd ../.. && ls", False), ("cd -P link/../..", False))
QUOTED = (("echo $'cd {live}/teamwork && ls'", False), ("git commit -m \"fix && cd {live}/teamwork && ls\"", False), ("echo 'cd {live}/teamwork && ls'", False), ("cat <<'EOF'\nit's && cd {live}/teamwork && ls\nEOF", False),
          ("cat <<EOF\n(cd {live}/teamwork && ls)\nEOF", False), ("echo x # cd {live}/teamwork && ls", False), ("cat <<'EOF' >/dev/null\nit's\nEOF\ncd {live}/teamwork && ls", True),
          ("echo \"a && b\" && cd {live}/teamwork && ls", True), ("git commit -m 'x'; (cd {live}/teamwork && ls)", True),
          ("echo $(cd {live}/teamwork && ls)", True), ("echo \"$(cd {live}/teamwork && ls)\"", True), ("cat <<'EOF'\ncd sub\nEOF\ncd ../.. && ls", True))


def setup():
    work = pathlib.Path(tempfile.mkdtemp(prefix="cd-refusal-"))
    live = work.resolve() / "live"
    (live / "teamwork").mkdir(parents=True)
    (live / "teamwork" / "note.txt").write_text("the live note\nthe second line\n")
    for command in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "first"]):
        subprocess.run(["git", *command], cwd=live, check=True, capture_output=True)
    worktree = live / ".claude" / "worktrees" / "w"
    worktree.mkdir(parents=True)
    os.environ["TEAMWORK_LIVE_FOLDER"] = str(live)
    (live / "teamwork" / "out").symlink_to(work / "alias" / "..")  # a link out of the live checkout, whose `..` a plain cd reads as the folder it stands in
    (worktree / "link").symlink_to(live / "teamwork")  # a link inside the worktree to a folder of the live checkout, whose `..` a `cd -P` takes to the live checkout
    (work / "alias").symlink_to(live)  # the live checkout under another name, which a cd enters as well
    os.environ["TEAMWORK_LIVE_ALIAS"] = str(work / "alias")
    stubs = replay_probe.fake_herdr(work, [{"pane_id": "p1", "name": "t-worker"}])
    return stubs, live, worktree


def hook_reason(stubs, worktree, command):
    event = {"hook_event_name": "PreToolUse", "cwd": str(worktree), "tool_input": {"command": command}}
    hook = replay_probe.route_event(ROUTE, event, stubs, "t-worker").get("hookSpecificOutput", {})
    if "allow" in json.dumps(hook):
        return f"allowed: {json.dumps(hook)[:200]}"
    return hook.get("permissionDecision") == "deny" and hook.get("permissionDecisionReason", "")


FOLLOWERS = ("git ls-files", "cat note.txt", "git ls-remote .", "gh api repos/x/y", "touch new.txt")
failed = []


def step(name, problem):
    print(f"fail {name}: {problem}" if problem else f"ok {name}", flush=True)
    failed.extend([name] if problem else [])


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    signal.alarm(300)  # a hook that loops ends the runner, which would otherwise wait for it
    stubs, live, worktree = setup()
    (worktree / "sub").mkdir()
    swapped = str(live).swapcase()  # the live checkout under another letter case, the same folder where the file system ignores case
    entering = [f"{spelling} && {follower}" for spelling in SPELLINGS[:1] for follower in FOLLOWERS] + [f"{spelling} && git ls-files" for spelling in SPELLINGS[1:]]
    entering += [f"cd {swapped}/teamwork && git ls-files"] * os.path.isdir(swapped)
    entering += [text for text in BLOCKED] + [f"{opening} git ls-files; {closer}" for opening, closer in BLOCKS]
    said = {command: hook_reason(stubs, worktree, command.format(live=live)) for command in entering}
    step("denied", next((f"{command!r} " + (said[command] if said[command] else "was not denied") for command in entering
                         if not said[command] or said[command].startswith("allowed") or not all(text in said[command] for text in (f"stands in {worktree}", "--repository <folder>", "git -C <folder>"))), None))
    step("chain", next((f"{command!r} " + ("was not denied" if denied else "was denied") for command, denied in CHAINS
                        if bool(hook_reason(stubs, worktree, command)) != denied), None))
    step("quoted", next((f"{command!r} " + ("was not denied" if denied else "was denied") for command, denied in ((text.format(live=live), denied) for text, denied in QUOTED)
                         if bool(hook_reason(stubs, worktree, command)) != denied), None))
    ghost = pathlib.Path(os.sep + "gone-checkout") / ".claude" / "worktrees" / "w"  # a checkout that is not on disk is read by its written path
    step("gone", None if hook_reason(stubs, ghost, "cd /gone-checkout/teamwork && ls") and not hook_reason(stubs, ghost, "cd /tmp && ls") else "a cd into a checkout that is gone was not refused, or a cd out of it was")
    step("inside", next((f"{command!r} got {got}" for command in ("cd sub && ls", "cd /tmp && ls", f"cd {worktree}/sub && git status")
                         if (got := replay_probe.route_event(ROUTE, {"hook_event_name": "PreToolUse", "cwd": str(worktree), "tool_input": {"command": command}}, stubs, "t-worker"))), None))
    print("FAIL cd never allowed" if failed else "PASS cd never allowed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
