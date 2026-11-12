#!/usr/bin/env python3
"""Call every teamwork script that takes words with `--help` and with an unknown `--x` at each word position of a valid call, on a throwaway git board and a stand-in herdr, and list each call that is not refused as AGENTS.md's Script form says.

usage: replay-option-calls.py [root]

A call is refused when the script exits 2, prints `usage:` on stderr and nothing on stdout, and leaves the folder, the git refs and worktrees, and the herdr call log as they were. Prints one `option <script>: <call> gave <answer>` line per call not refused, and a script that takes words but has no valid call in CALLS, then a summary line `<n> scripts, <n> calls, <n> not refused`, and exits 0 only when none failed."""
import concurrent.futures
import os
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PLUGIN = "teamwork"
UNKNOWN = ("--help", "--x")
# the valid calls of each script, each word either a file the sandbox holds (`body`, `diff`) or a name; an option goes in at every position
CALLS = {
    "hooks/list-issue-board.py": [["project", "--width", "80"], ["--nodes", "body", "--json"], ["project", "--check"]],
    "hooks/print-task-markdown.py": [["1"], ["--nodes", "body", "1"]],
    "skills/kick-off/scripts/add-worktree.py": [["name", "main", "branch"]],
    "skills/kick-off/scripts/answer-prompt.py": [["name", "1"]],
    "skills/kick-off/references/estimation/scripts/backtest-estimate.py": [["--from-json", "body", "--as-of", "2026-01-01", "--tasks", "1,2"]],
    "skills/kick-off/scripts/check-criteria.py": [["--task", "1", "body"], ["--cut-off"]],
    "skills/kick-off/scripts/close-session.py": [["name"]],
    "skills/kick-off/references/estimation/scripts/estimate-task-time.py": [["--from-json", "body", "--gaps-json", "body", "--expect-restarts", "1", "--wait", "name=1", "--seed", "1", "url"]],
    "skills/kick-off/references/worker/scripts/list-additions.py": [["1"]],
    "skills/kick-off/references/estimation/scripts/list-session-gaps.py": [["--from-folder", ".", "--json", "name"]],
    "skills/kick-off/scripts/list-sessions.py": [["--me"]],
    "skills/kick-off/references/estimation/scripts/list-task-durations.py": [["--from-json", "body"]],
    "skills/kick-off/references/manager/scripts/print-scope-folder.py": [["name"], ["--me"]],
    "skills/kick-off/scripts/print-steering.py": [["key"]],
    "skills/kick-off/references/recall/scripts/recall-work.py": [["words", "--path", "file", "--before", "2026-01-01", "--top", "3"]],
    "skills/kick-off/scripts/remove-worktree.py": [["name", "other"]],
    "skills/kick-off/references/adapters/session-herdr/scripts/rename-session.py": [["name"]],
    "skills/kick-off/scripts/run-criteria.py": [["--timeout", "5", "--base", "--ref", "main", "1"], ["--pass", "1=body", "1"]],
    "skills/kick-off/references/worker-build/scripts/run-on-refs.py": [["true", "main", "main"]],
    "skills/kick-off/scripts/start-session.py": [["name", ".", "worker name", "--model", "m", "--effort", "low", "--allow", "Bash", "--steer", "key"]],
    "skills/kick-off/references/adapters/message-herdr/scripts/tell-session.py": [["name", "body"]],
    "skills/kick-off/scripts/use-board.py": [
        ["read", "1", "--as", "worker", "--full"], ["comment", "1", "body", "--asks", "owner", "--option", "x", "--option", "y"], ["hold", "1", "name"], ["depend", "1", "2"], ["file", "Add thing", "body", "label", "--scope", "", "--depends", "1"],
        ["edit", "1", "diff", "DECIDED: x", "--base", "abc"], ["title", "1", "Add thing"], ["resolve", "1", "body", "--not-planned"],
        ["reopen", "1"], ["decide", "1", "body", "--by", "owner", "--one-way", "--supersedes", "url", "--answers", "url", "--holders", "name", "--live-runs", "1"], ["label", "1", "label", "--remove"]],
    "skills/kick-off/references/adapters/landing-git/scripts/use-landing.py": [["change", "branch", "Add thing", "body", "main"], ["merge", "1", "abc"]],
}


def scripts_of(root):
    """The scripts of the plugin that Claude Code or a session runs: those of hooks/, monitors/, each skill's scripts/ and each scripts/ under its references/."""
    found = []
    for pattern in ("hooks/*.py", "monitors/*.py", "skills/*/scripts/*.py", "skills/*/references/**/scripts/*.py"):
        found += sorted(path.relative_to(root / PLUGIN).as_posix() for path in (root / PLUGIN).glob(pattern))
    return found


def takes_words(path):
    """Whether a usage line of the script's docstring names anything after the script's name."""
    text = pathlib.Path(path).read_text()
    docstring = re.match(r'(?:#!.*\n)?"""(.*?)"""', text, re.S)
    name = re.escape(pathlib.Path(path).name)
    return bool(docstring and re.search(rf"^(?:usage:[ \t]*(?:python3?[ \t]+)?)?[ \t]*(?:\S*/)?{name}[ \t]+\S", docstring.group(1), re.M))


def run(command, **options):
    return subprocess.run(command, capture_output=True, text=True, timeout=30, **options)


def build_sandbox(root, work):
    """A git repository with a board holding issue 1, a home, and a PATH with the stand-in herdr first."""
    repository, home = work / "repository", work / "home"
    repository.mkdir()
    home.mkdir()
    state = work / "herdr-state.json"
    state.write_text('{"n": 0, "tabs": [], "workspaces": [], "agents": []}')
    for name, text in (("body", "A body.\n"), ("diff", "--- a\n+++ b\n@@ -1 +1 @@\n-A\n+B\n"), ("file", "x\n")):
        (repository / name).write_text(text)
    git = ["git", "-C", str(repository), "-c", "user.name=x", "-c", "user.email=x@x"]
    run(git + ["init", "-q", "-b", "main"])
    run(git + ["commit", "-q", "--allow-empty", "-m", "start"])
    environment = {"PATH": f"{HERE / 'fake-herdr'}:{os.environ['PATH']}", "HOME": str(home), "CLAUDE_CONFIG_DIR": str(home / "claude"),
                   "TEAMWORK_FAKE_HERDR_STATE": str(state), "TEAMWORK_FAKE_HERDR_LOG": str(work / "herdr-log"), "PYTHONDONTWRITEBYTECODE": "1"}
    seeded = run([sys.executable, str(root / PLUGIN / "skills/kick-off/scripts/use-board.py"), "file", "Seed the board", "body"], cwd=repository, env=environment)
    if seeded.returncode:
        sys.exit(f"replay-option-calls: the throwaway board did not start: {seeded.stderr.strip()}")
    return repository, environment


def snapshot(repository, work):
    """What a call could change: files, refs, worktrees and the herdr call log."""
    files = sorted((str(path.relative_to(work)), path.stat().st_size, path.stat().st_mtime_ns) for path in work.rglob("*")
                   if ".git" not in path.relative_to(work).parts[:2] and path.is_file())
    git = lambda *args: run(["git", "-C", str(repository), *args]).stdout
    log = work / "herdr-log"
    return files, git("for-each-ref"), git("worktree", "list"), log.read_text() if log.exists() else ""


def calls_with_option(words):
    """Each call that puts an unknown option into WORDS at a word position: before the word, or in its place."""
    for position in range(len(words) + 1):
        for option in UNKNOWN:
            yield words[:position] + [option] + words[position:]
            if position < len(words):
                yield words[:position] + [option] + words[position + 1:]


def replay_script(root, path):
    """The calls made on one script and the lines of those not refused, run in a sandbox of its own so scripts replay side by side."""
    failures, called = [], 0
    with tempfile.TemporaryDirectory() as folder:
        work = pathlib.Path(folder)
        repository, environment = build_sandbox(root, work)
        for words in CALLS[path]:
            for call in calls_with_option(words):
                before = snapshot(repository, work)
                called += 1
                try:
                    answered = run([sys.executable, str(root / PLUGIN / path), *call], cwd=repository, env=environment, stdin=subprocess.DEVNULL)
                    answer = (f"exit {answered.returncode}, stdout {answered.stdout[:60]!r}" if answered.returncode != 2 or answered.stdout or "usage:" not in answered.stderr
                              else "a change to the folder, refs or herdr calls" if snapshot(repository, work) != before else "")
                except subprocess.TimeoutExpired:
                    answer = "no answer in 30 s"
                if answer:
                    failures.append(f"option {PLUGIN}/{path}: {' '.join(call)} gave {answer}")
    return called, failures


def main(args):
    if len(args) > 1 or (args and args[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 2
    root = pathlib.Path(args[0] if args else HERE.parents[3]).resolve()
    scripts = scripts_of(root)
    failures = [f"option {PLUGIN}/{path}: takes words but has no valid call in replay-option-calls.py, so no option was tried on it"
                for path in scripts if path not in CALLS and takes_words(root / PLUGIN / path)]
    # four at a time, since each call starts a process and the machine is shared
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        replayed = list(pool.map(lambda path: replay_script(root, path), [path for path in scripts if path in CALLS]))
    called = sum(count for count, _ in replayed)
    for _, lines in replayed:
        failures += lines
    for line in failures:
        print(line)
    print(f"{len(replayed)} scripts, {called} calls, {len(failures)} not refused")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
