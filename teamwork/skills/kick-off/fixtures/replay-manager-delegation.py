#!/usr/bin/env python3
"""Run the manager kick-off in a clean `claude -p` on a repository question and print `PASS` as the last line when the manager hands the search to a subagent, else `FAIL: <what it did>`.

usage: replay-manager-delegation.py [--ref <sha>] [--max-direct <n>]

The tree under test is the checkout's `teamwork/` (tracked files and untracked ones git does not ignore), or `--ref`'s. It is both the only plugin the run loads and the repository the question asks about.
The owner asks which Python modules of `teamwork/lib` write board records, which takes a search of many files. A manager that follows its playbook `references/manager.md` starts an `Agent` and makes at most
`--max-direct` other tool calls itself (default 2; calls on the playbooks and their scripts, subagents and skills not counted)."""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_runs  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[4]
PLAYBOOK_FILE = re.compile(r"/skills/kick-off/(references|scripts)/[\w/.-]+\.(md|py)\b")
SEARCH = re.compile(r"\b(grep|rg|find)\b")
QUESTION = "teamwork/lib 아래 어느 파이썬 모듈이 보드 기록(이슈, 코멘트)을 쓰는지 찾아서 알려줘."
PROMPT = """Run the teamwork:kick-off skill with these arguments: teamwork-manager

This is a replay in a fresh checkout, your working folder. GitHub, herdr and other Claude sessions are off: skip each step that needs one.
The owner says: {question}"""
MODEL, BUDGET = "sonnet", "0.75"


def copy_tree(ref, into):
    into.mkdir(parents=True)
    if ref:
        archive = subprocess.run(["git", "-C", str(ROOT), "archive", ref, "teamwork"], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(into)], input=archive, check=True)
        return
    names = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard", "teamwork"], capture_output=True, text=True, check=True).stdout.split("\n")
    for name in filter(None, names):
        if (ROOT / name).is_file():
            (into / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, into / name)


def direct_file_work(uses):
    """The tool uses of the main thread, other than a subagent, a skill and a read of one playbook or script file, which is any way to read or search a file."""
    found = []
    for use in uses.values():
        named = json.dumps(use["input"])
        reads_playbook = PLAYBOOK_FILE.search(named) and use["name"] != "Grep" and not SEARCH.search(str(use["input"].get("command", "")))
        if use["name"] in ("Agent", "Skill") or reads_playbook:
            continue
        found.append(f"{use['name']} {(use['input'].get('command') or named)[:80]}")
    return found


def main(args):
    ref, limit = None, 2
    while args:
        if len(args) < 2 or args[0] not in ("--ref", "--max-direct"):
            print(__doc__, file=sys.stderr)
            return 2
        ref, limit = (args[1], limit) if args[0] == "--ref" else (ref, int(args[1]))
        args = args[2:]
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="manager-delegation-"))
    work = scratch / "repository"
    copy_tree(ref, work)
    command = [shutil.which("claude"), "-p", PROMPT.format(question=QUESTION), "--model", MODEL, "--setting-sources", "", "--strict-mcp-config",
               "--max-budget-usd", BUDGET, "--permission-mode", "acceptEdits", "--allowedTools", "Bash", "Read", "Grep", "Glob", "Skill", "Agent",
               "--plugin-dir", str(work / "teamwork"), "--output-format", "stream-json", "--verbose", "--no-session-persistence"]
    stream, _ = replay_runs.run_claude(command, work, replay_runs.clean_environment(scratch))
    uses = replay_runs.read_tool_uses(stream)
    shutil.rmtree(scratch, ignore_errors=True)
    delegated = sum(use["name"] == "Agent" for use in uses.values())
    direct = direct_file_work(uses)
    if delegated and len(direct) <= limit:
        print("PASS")
        return 0
    print(f"FAIL: {delegated} subagents started, {len(direct)} direct tool calls: {'; '.join(direct[:6])}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
