"""Claude Code as the agent port's adapter."""
import json

KIND = "claude"
# claude.ai connectors (Gmail, Drive, Notion...) serve no teamwork role, and their tool list costs ~5k tokens every turn
SETTINGS = json.dumps({"disableClaudeAiConnectors": True})
# Each tool off is a choice, since each description costs ~2-11k tokens every turn; subagents get only their session's tools (code.claude.com/docs/en/sub-agents):
# - manager: Artifact off, it publishes nothing; Workflow off, it orchestrates by hand
# - worker: AskUserQuestion off, it asks the owner through its manager; Artifact off, unless its manager passes --allow Artifact for a backlog that publishes a page
# - judge, a general-purpose subagent of a worker: the worker's tools; judge.md's steps use Read, Bash, and Write for scratchpad tests, and the plugin may ship no agent to narrow it
TOOLS_OFF = {"worker": "Artifact,AskUserQuestion", "manager": "Artifact,Workflow"}
TRUST = ("Yes, I trust this folder", ("down", "enter"))
EXIT = "/exit"
# Claude Code may ask these on /exit; each key is the answer that exits without saving anything
DIALOGS = [
    ("Background work is running", "enter"),  # first option: Exit
    ("unsent feedback draft", "esc"),  # Esc to discard and exit
    ("d to discard", "d"),  # the drafts list, reached by Enter
    ("No feedback drafts queued", "esc"),  # the empty panel after `d`
]


def command(name, plugin_dir, model, effort, off):
    return ["--name", name, "--plugin-dir", plugin_dir, "--model", model, "--effort", effort,
            "--settings", SETTINGS, *(["--disallowedTools", ",".join(off)] if off else [])]


def kickoff(args):
    return f"Run the teamwork:kick-off skill with these arguments: {args}"  # model-only: a typed /teamwork:kick-off is refused
