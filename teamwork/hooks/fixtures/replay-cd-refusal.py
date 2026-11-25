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
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import replay_probe  # noqa: E402

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


def setup(work):
    """A sandbox whose repository is the live checkout, a worktree in it and the links a cd may take into it; and the variables naming it."""
    sandbox = replay_probe.Sandbox(work, [replay_probe.agent("t-worker", 1)])
    live = sandbox.repository
    (live / "teamwork").mkdir()
    (live / "teamwork" / "note.txt").write_text("the live note\nthe second line\n")
    sandbox.git("add", "-A")
    sandbox.git("commit", "-q", "-m", "first")
    worktree = live / ".claude" / "worktrees" / "w"
    (worktree / "sub").mkdir(parents=True)
    (live / "teamwork" / "out").symlink_to(work / "alias" / "..")  # a link out of the live checkout, whose `..` a plain cd reads as the folder it stands in
    (worktree / "link").symlink_to(live / "teamwork")  # a link inside the worktree to a folder of the live checkout, whose `..` a `cd -P` takes to the live checkout
    (work / "alias").symlink_to(live)  # the live checkout under another name, which a cd enters as well
    return sandbox, live, worktree, {"TEAMWORK_LIVE_FOLDER": live, "TEAMWORK_LIVE_ALIAS": work / "alias"}


def answer(sandbox, variables, cwd, command):
    """The hook's answer to COMMAND run from CWD, which may not be on disk, so the hook runs from the sandbox's folder."""
    return sandbox.route({"hook_event_name": "PreToolUse", "cwd": str(cwd), "tool_input": {"command": command}}, cwd=sandbox.work, **variables)


def hook_reason(sandbox, variables, worktree, command):
    hook = answer(sandbox, variables, worktree, command).get("hookSpecificOutput", {})
    if "allow" in json.dumps(hook):
        return f"allowed: {json.dumps(hook)[:200]}"
    return hook.get("permissionDecision") == "deny" and hook.get("permissionDecisionReason", "")


FOLLOWERS = ("git ls-files", "cat note.txt", "git ls-remote .", "gh api repos/x/y", "touch new.txt")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases("cd never allowed")
    with replay_probe.scratch("cd-refusal-") as work:
        sandbox, live, worktree, variables = setup(work)
        reason = lambda cwd, command: hook_reason(sandbox, variables, cwd, command)
        swapped = str(live).swapcase()  # the live checkout under another letter case, the same folder where the file system ignores case
        entering = [f"{spelling} && {follower}" for spelling in SPELLINGS[:1] for follower in FOLLOWERS] + [f"{spelling} && git ls-files" for spelling in SPELLINGS[1:]]
        entering += [f"cd {swapped}/teamwork && git ls-files"] * os.path.isdir(swapped)
        entering += [text for text in BLOCKED] + [f"{opening} git ls-files; {closer}" for opening, closer in BLOCKS]
        said = {command: reason(worktree, command.format(live=live)) for command in entering}
        problem = next((f"{command!r} " + (said[command] if said[command] else "was not denied") for command in entering
                        if not said[command] or said[command].startswith("allowed") or not all(text in said[command] for text in (f"stands in {worktree}", "--repository <folder>", "git -C <folder>"))), None)
        cases.step("denied", not problem, problem)
        problem = next((f"{command!r} " + ("was not denied" if denied else "was denied") for command, denied in CHAINS if bool(reason(worktree, command)) != denied), None)
        cases.step("chain", not problem, problem)
        problem = next((f"{command!r} " + ("was not denied" if denied else "was denied") for command, denied in ((text.format(live=live), denied) for text, denied in QUOTED)
                        if bool(reason(worktree, command)) != denied), None)
        cases.step("quoted", not problem, problem)
        ghost = pathlib.Path(os.sep + "gone-checkout") / ".claude" / "worktrees" / "w"  # a checkout that is not on disk is read by its written path
        cases.step("gone", reason(ghost, "cd /gone-checkout/teamwork && ls") and not reason(ghost, "cd /tmp && ls"), "a cd into a checkout that is gone was not refused, or a cd out of it was")
        problem = next((f"{command!r} got {got}" for command in ("cd sub && ls", "cd /tmp && ls", f"cd {worktree}/sub && git status")
                        if (got := answer(sandbox, variables, worktree, command))), None)
        cases.step("inside", not problem, problem)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
