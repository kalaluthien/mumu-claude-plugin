"""The background work a session started and has not seen end: what its transcript shows, and what still runs under its session id."""
import json
import os
import re
import subprocess

import claude_config

# what a tool's result says when it starts background work, by tool
STARTED = {"Agent": r"^agentId: (\w+)", "SendMessage": r"\"resumedAgentId\":\s*\"(\w+)\"", "Bash": r"\ACommand running in background with ID: (\w+)"}


def text(content):
    return content if isinstance(content, str) else " ".join(item.get("text", "") for item in content or [] if isinstance(item, dict))


def running_work(transcript):
    """Ids of the background agents and commands a transcript started that no task notification has ended yet."""
    running, tools = set(), {}
    try:
        records = [json.loads(line) for line in open(transcript) if line.strip()]
    except (OSError, ValueError):
        return running
    # an `api-request-blob` replays old tool results, which would start a finished task again
    for record in (record for record in records if record.get("type") in ("user", "assistant", "queue-operation")):
        content = record.get("content") if record.get("type") == "queue-operation" else (record.get("message") or {}).get("content")
        if isinstance(content, str):  # a notification arrives as plain text, never inside a tool result
            running.difference_update(re.findall(r"<task-id>(\w+)</task-id>.*?<status>(?:completed|failed|killed|stopped)</status>", content, re.S))
            continue
        for block in (block for block in content or [] if isinstance(block, dict)):
            if block.get("type") == "tool_use":
                tools[block.get("id")] = STARTED.get(block.get("name"))
                running.discard((block.get("input") or {}).get("task_id") if block.get("name") == "TaskStop" else None)
            elif (pattern := tools.get(block.get("tool_use_id"))) and (found := re.search(pattern, text(block.get("content")), re.M)):
                running.add(found.group(1))
    return running


def transcript_of(session_id):
    """The path of a session's transcript, which Claude Code files under the project folder of the folder it started in; None when there is none."""
    return next(iter((claude_config.folder() / "projects").glob(f"*/{session_id}.jsonl")), None) if session_id else None


def seconds(elapsed):
    """The seconds of a `ps` elapsed time, `[[dd-]hh:]mm:ss`."""
    days, _, clock = elapsed.rpartition("-")
    fields = [int(field) for field in clock.split(":")]
    return int(days or 0) * 86400 + sum(field * 60 ** place for place, field in enumerate(reversed(fields)))


def running_commands(session_id):
    """Pids of the processes younger than TEAMWORK_BACKGROUND_SECONDS (12 hours) that carry SESSION_ID in their environment, such as a command the session detached
    from its shell with `( ... ) &` or a monitor's loop, which no transcript record shows; the session's own heartbeat is no work, and a daemon older than the limit,
    which a command left behind and which ends with nothing, holds no worker busy."""
    if not session_id:
        return []
    limit = float(os.environ.get("TEAMWORK_BACKGROUND_SECONDS", 12 * 3600))
    listing = subprocess.run(["ps", "-E", "-ww", "-A", "-o", "pid=,etime=,command="], capture_output=True, text=True).stdout
    mark = f" CLAUDE_CODE_SESSION_ID={session_id}"
    return [int(line.split()[0]) for line in listing.splitlines()
            if mark in line and "/monitors/print-team-gaps.py " not in line and seconds(line.split()[1]) < limit]
