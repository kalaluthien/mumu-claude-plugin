"""Claude Code as the agent port's adapter."""
import json
import os
import pathlib
import re
import subprocess

KIND = "claude"
# claude.ai connectors (Gmail, Drive, Notion...) serve no teamwork role, and their tool list costs ~5k tokens every turn
SETTINGS = {"disableClaudeAiConnectors": True}
# every call re-reads the whole context, which Claude Code lets grow far before it compacts; a worker's window compacts sooner,
# so its history stays shorter on every call
WORKER_SETTINGS = {**SETTINGS, "autoCompactWindow": 145000}
# Each tool off is a choice, since each description costs ~2-11k tokens every turn; subagents get only their session's tools (code.claude.com/docs/en/sub-agents):
# - manager: Artifact off, it publishes nothing; Workflow off, it orchestrates by hand
# - worker: AskUserQuestion off, it asks the owner through its manager; Artifact off, unless its manager passes --allow Artifact for a root task that publishes a page
# - sentinel: the worker's tools off, and Agent and Workflow too, since it repeats one duty and needs no helper
# - judge, a general-purpose subagent of a worker: the worker's tools; judge.md's steps use Read, Bash, and Write for scratchpad tests, and the plugin may ship no agent to narrow it
TOOLS_OFF = {"worker": "Artifact,AskUserQuestion", "manager": "Artifact,Workflow", "sentinel": "Agent,Artifact,AskUserQuestion,Workflow"}
TRUST = ("Yes, I trust this folder", ("down", "enter"))
EXIT = "/exit"
TELL = "SendMessage"  # how a session of this kind is told; herdr typing reaches it only once its turn ends, so a sender waits
# Claude Code may ask these on /exit; each key is the answer that exits without saving anything
DIALOGS = [
    ("Background work is running", "enter"),  # first option: Exit
    ("unsent feedback draft", "esc"),  # Esc to discard and exit
    ("d to discard", "d"),  # the drafts list, reached by Enter
    ("No feedback drafts queued", "esc"),  # the empty panel after `d`
]


def command(name, plugin_folder, model, effort, off):
    return ["--name", name, "--plugin-dir", plugin_folder, "--model", model, "--effort", effort,
            "--settings", json.dumps(WORKER_SETTINGS if name.endswith("-worker") else SETTINGS), *(["--disallowedTools", ",".join(off)] if off else [])]


def named(name, transcript):
    """Whether the session running this process was started or renamed as NAME: the nearest `claude` above it was started with `--name NAME`,
    or its TRANSCRIPT's last title is NAME, so a `claude -p` started in a named session's pane, which herdr then records as that pane's session, takes no name."""
    return bool(name) and (started_name() == name or last_title(transcript) == name)


def started_name():
    """The `--name` of the nearest `claude` process above this one; None when there is none, or it was started without one."""
    listed = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,command="], capture_output=True, text=True).stdout.splitlines()
    processes = {int(pid): (int(ppid), words) for pid, ppid, *words in (line.split() for line in listed) if words}
    at = os.getppid()
    while at in processes and at > 1:
        parent, words = processes[at]
        if os.path.basename(words[0]) == KIND:
            return next((value for option, value in zip(words, words[1:]) if option == "--name"), None)
        at = parent
    return None


def last_title(transcript):
    """The name Claude Code last recorded in TRANSCRIPT, by `--name` or `/rename`; None before the file exists, as at a session's start."""
    try:
        titles = [line for line in pathlib.Path(transcript or "").read_text(errors="replace").splitlines() if line.startswith('{"type":"custom-title"')]
    except OSError:
        return None
    return titles and json.loads(titles[-1]).get("customTitle") or None


def kickoff(args):
    return f"Run the teamwork:kick-off skill with these arguments: {args}"  # model-only: a typed /teamwork:kick-off is refused


def draft(screen):
    """The box is the lines between the last two rules; its hints, such as `Press up to edit queued messages`, are drawn dim, which typed text never is.
    The box pads each line with spaces, so a draft of only spaces reads as empty."""
    plain = lambda line: re.sub(r"\x1b\[[0-9;]*m", "", line)
    lines = screen.splitlines()
    rules = [at for at, line in enumerate(lines) if plain(line).startswith("──")]
    if len(rules) < 2:
        return None
    box = [plain(re.sub(r"\x1b\[2m.*?\x1b\[0m", "", line)) for line in lines[rules[-2] + 1:rules[-1]]]
    return re.sub(r"^❯.?", "", "\n".join(box)).strip()
