"""The background work a session's transcript started and has not seen end."""
import json
import re

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
    for record in records:
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
