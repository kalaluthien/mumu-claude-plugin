"""The background work a session's transcript started and has not seen end."""
import json
import re

# what a tool's result says when it starts background work, by tool
STARTED = {"Agent": r"^agentId: (\w+)", "SendMessage": r"\"resumedAgentId\":\s*\"(\w+)\"", "Bash": r"\ACommand running in background with ID: (\w+)"}


def text(content):
    return content if isinstance(content, str) else " ".join(x.get("text", "") for x in content or [] if isinstance(x, dict))


def running_work(transcript):
    """Ids of the background agents and commands a transcript started that no task notification has ended yet."""
    running, tools = set(), {}
    try:
        records = [json.loads(line) for line in open(transcript) if line.strip()]
    except (OSError, ValueError):
        return running
    for r in records:
        content = r.get("content") if r.get("type") == "queue-operation" else (r.get("message") or {}).get("content")
        if isinstance(content, str):  # a notification arrives as plain text, never inside a tool result
            running.difference_update(re.findall(r"<task-id>(\w+)</task-id>.*?<status>(?:completed|failed|killed|stopped)</status>", content, re.S))
            continue
        for b in (b for b in content or [] if isinstance(b, dict)):
            if b.get("type") == "tool_use":
                tools[b.get("id")] = STARTED.get(b.get("name"))
                running.discard((b.get("input") or {}).get("task_id") if b.get("name") == "TaskStop" else None)
            elif (pattern := tools.get(b.get("tool_use_id"))) and (found := re.search(pattern, text(b.get("content")), re.M)):
                running.add(found.group(1))
    return running
