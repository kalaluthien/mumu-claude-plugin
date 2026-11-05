"""What a clean replay of a closed task in `claude -p` needs: a fresh export of a commit, the run's checks, stand-ins for
GitHub, herdr and Claude, and the run's stream read back into turns, tool uses and results priced as the bill is."""
import json
import os
import pathlib
import subprocess

CHARS_PER_TOKEN = 2.2
WEIGHT = {"opus": 5.0, "sonnet": 3.0, "haiku": 1.0}
BLOCKED_TOOLS = ("gh", "herdr", "claude")
CHECK_TIMEOUT = 180


def export(root, sha, into):
    """A fresh repository at SHA's tree in INTO, one commit, so checks that read git see a clean tree."""
    into.mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(root), "archive", sha], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(into)], input=archive, check=True)
    identity = {**os.environ, "GIT_AUTHOR_NAME": "replay", "GIT_AUTHOR_EMAIL": "replay@localhost",
                "GIT_COMMITTER_NAME": "replay", "GIT_COMMITTER_EMAIL": "replay@localhost"}
    for command in (["git", "init", "-q", "-b", "main"], ["git", "add", "-A"], ["git", "commit", "-q", "-m", f"base {sha}"]):
        subprocess.run(command, cwd=into, env=identity, check=True, capture_output=True)


def run_check(command, cwd):
    try:
        done = subprocess.run(["bash", "-c", command], cwd=cwd, capture_output=True, text=True, timeout=CHECK_TIMEOUT,
                              stdin=subprocess.DEVNULL)
        return done.returncode, (done.stdout + done.stderr).strip()
    except subprocess.TimeoutExpired:
        return None, f"timed out after {CHECK_TIMEOUT} s"


def verdict(test, status, out):
    kind, want = test
    if status is None:
        return "fail"
    if kind == "exits":
        return "pass" if status == want else "fail"
    if kind == "more":
        first = out.split(maxsplit=1)[:1]
        return "pass" if first and first[0].isdigit() and int(first[0]) >= want else "fail"
    return "pass" if out == want else "fail"


def blocked_path(folder):
    """A folder of stand-ins for GitHub, herdr and Claude, first on PATH, so a replay writes to no live board or session."""
    folder.mkdir(parents=True, exist_ok=True)
    for tool in BLOCKED_TOOLS:
        stand_in = folder / tool
        stand_in.write_text(f"#!/bin/sh\necho '{tool} is off in this replay' >&2\nexit 1\n")
        stand_in.chmod(0o755)
    return folder


def weight(model):
    return next((value for key, value in WEIGHT.items() if key in (model or "")), 0.0)


def turn_input(usage):
    creation = usage.get("cache_creation") or {}
    hour = creation.get("ephemeral_1h_input_tokens", 0)
    minutes = creation.get("ephemeral_5m_input_tokens", usage.get("cache_creation_input_tokens", 0) - hour)
    return usage.get("input_tokens", 0) + 1.25 * minutes + 2 * hour + 0.1 * usage.get("cache_read_input_tokens", 0)


def run_units(turns):
    """The run's bill in input-token units: each turn's input side plus five times its output, times its model's weight."""
    return sum(weight(turn["model"]) * (turn_input(turn["usage"]) + 5 * turn["usage"].get("output_tokens", 0)) for turn in turns)


def text_of(content):
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content or [] if isinstance(part, dict))


def read_events(stream):
    """The run's init event, turns in order, tool uses by id, results in order and its result event."""
    init, turns, uses, results, result = {}, {}, {}, [], {}
    for position, line in enumerate(stream.splitlines()):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind, subtype = event.get("type"), event.get("subtype", "")
        if kind == "system" and subtype == "init":
            init = event
        elif kind == "assistant" and event.get("parent_tool_use_id") is None:
            message = event["message"]
            first = turns.get(message.get("id"), {}).get("position", position)
            turns[message.get("id")] = {"id": message.get("id"), "position": first, "usage": message.get("usage") or {},
                                        "model": message.get("model")}
            for part in message.get("content", []):
                if isinstance(part, dict) and part.get("type") == "tool_use":
                    uses[part["id"]] = {"name": part["name"], "input": part.get("input") or {}, "turn": message.get("id")}
        elif kind == "user" and event.get("parent_tool_use_id") is None and isinstance(event["message"].get("content"), list):
            for part in event["message"]["content"]:
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    results.append({"position": position, "id": part.get("tool_use_id"), "text": text_of(part.get("content"))})
        elif kind == "result":
            result = event
    return init, sorted(turns.values(), key=lambda turn: turn["position"]), uses, results, result


def carry(tokens, position, turns):
    """The cost of TOKENS taken in at POSITION: written by the next turn, read by each turn after it."""
    later = [turn for turn in turns if turn["position"] > position]
    if not later:
        return 0.0
    first = later[0]
    rate = 2.0 if (first["usage"].get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0) else 1.25
    return tokens * (weight(first["model"]) * rate + sum(weight(turn["model"]) * 0.1 for turn in later[1:]))
