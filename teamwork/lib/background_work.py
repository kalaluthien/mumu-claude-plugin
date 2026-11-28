"""The background work a session started and has not seen end: what its transcript shows, and what still runs under its session id."""
import json
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


LIMIT_SECONDS = 12 * 3600  # a process older than this is a daemon a command left behind, no work


def seconds(elapsed):
    """The seconds of a `ps` elapsed time, `[[dd-]hh:]mm:ss`."""
    days, _, clock = elapsed.rpartition("-")
    fields = [int(field) for field in clock.split(":")]
    return int(days or 0) * 86400 + sum(field * 60 ** place for place, field in enumerate(reversed(fields)))


def running_commands(session_id):
    """Pids of the processes younger than 12 hours that carry SESSION_ID in their environment, such as a command the session detached from its shell with `( ... ) &`
    or a monitor's loop, which no transcript record shows; the session's own heartbeat is no work, and a daemon older than that, which a command left behind and which ends
    with nothing, holds no worker busy. `ps -E` shows no environment for a system binary such as `sleep`, so a detached command of system binaries alone is not seen."""
    if not session_id:
        return []
    listing = subprocess.run(["ps", "-E", "-ww", "-A", "-o", "pid=,etime=,command="], capture_output=True, text=True).stdout
    mark = f" CLAUDE_CODE_SESSION_ID={session_id}"
    return [int(line.split()[0]) for line in listing.splitlines()
            if mark in line and "/monitors/print-team-gaps.py " not in line and seconds(line.split()[1]) < LIMIT_SECONDS]


def clock_seconds(clock):
    """The seconds of a `ps` CPU time, `[hh:]mm:ss.ss`, or None for a field of another form."""
    try:
        return sum(float(field) * 60 ** place for place, field in enumerate(reversed(clock.split(":"))))
    except ValueError:
        return None


SYSTEM_SHELL = re.compile(r"/(?:usr/)?bin/(?:zsh|bash|sh)\b")


def runs(session_ids):
    """Per session id, each process tree it still runs, as (root pid, root command, the tree's pids and CPU seconds, its oldest `run-criteria.py` as
    (seconds, command) or None); a root is a process carrying the id whose parent does not, and its tree is every process under it, the system
    binaries `ps -E` shows no environment for among them. The session's own heartbeat is no run, and a process older than LIMIT_SECONDS with no `run-criteria.py` under it is a left-behind daemon, no run."""
    listing = subprocess.run(["ps", "-E", "-ww", "-A", "-o", "pid=,ppid=,etime=,time=,command="], capture_output=True, text=True).stdout
    processes = {}
    for line in listing.splitlines():
        fields = line.split(None, 4)
        if len(fields) == 5 and fields[0].isdigit() and fields[1].isdigit() and re.fullmatch(r"(\d+-)?(\d+:)?\d+:\d+", fields[2]) and (cpu := clock_seconds(fields[3])) is not None:
            processes[int(fields[0])] = (int(fields[1]), seconds(fields[2]), cpu, fields[4])
    children = {}
    for pid, (parent, *_) in processes.items():
        children.setdefault(parent, []).append(pid)
    owner = {pid: next((session_id for session_id in session_ids if session_id and f" CLAUDE_CODE_SESSION_ID={session_id}" in command), None)
             for pid, (_, _, _, command) in processes.items()}
    for pid, (parent, *_) in processes.items():  # a system shell shows no environment, so it takes its owned child's session, or the child's pipeline mates would each be a run
        shell = processes.get(parent)
        if shell and SYSTEM_SHELL.match(shell[3]):
            owner[parent] = owner[parent] or owner[pid]
    found = {session_id: [] for session_id in session_ids}
    for pid, (parent, _, _, command) in processes.items():
        if owner[pid] is None or owner.get(parent) == owner[pid] or "/monitors/print-team-gaps.py " in command:
            continue
        tree, waiting = [], [pid]
        while waiting:
            tree.append(waiting.pop())
            waiting += children.get(tree[-1], [])
        criteria = max(((processes[member][1], shown(processes[member][3])) for member in tree if "run-criteria.py" in processes[member][3]), default=None)
        if processes[pid][1] >= LIMIT_SECONDS and not criteria:  # a daemon a command left behind, which a check run never is
            continue
        found[owner[pid]].append((pid, shown(command), sum(processes[member][2] for member in tree), criteria))
    return found


def shown(command):
    """COMMAND without the environment `ps -E` appends to it and with each path cut to its file name, so a run's script and arguments stay in 100 characters."""
    return re.sub(r"\S*/", "", re.sub(r" [A-Z][A-Z0-9_]*=.*", "", command))[:100]


def heartbeat_running(session_id):
    """Whether the heartbeat `print-team-gaps.py` runs under SESSION_ID, which a manager's watch needs while any task it routed is held."""
    listing = subprocess.run(["ps", "-E", "-ww", "-A", "-o", "pid=,command="], capture_output=True, text=True).stdout
    return any(f" CLAUDE_CODE_SESSION_ID={session_id}" in line and "/monitors/print-team-gaps.py" in line for line in listing.splitlines())
