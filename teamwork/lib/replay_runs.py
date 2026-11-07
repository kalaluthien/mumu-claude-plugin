"""What a clean replay of a closed task in `claude -p` needs: a fresh export of a commit, the run's checks, a clean
environment with stand-ins for GitHub, herdr and Claude, the run itself, its jobs started under a spending limit, and its
stream read back into turns, tool uses and results priced as the bill is."""
import concurrent.futures
import json
import os
import subprocess

import criteria_check

CHARS_PER_TOKEN = 2.2
WEIGHT = {"opus": 5.0, "sonnet": 3.0, "haiku": 1.0}
BLOCKED_TOOLS = ("gh", "herdr", "claude")
CHECK_TIMEOUT = 180
RUN_TIMEOUT = 3600
SWITCHES = {"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}
BUILT_IN_PLUGIN_PREFIX = "cc-plugin-"


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
    """A replay has no judge to read an `unclear` run, so it counts as `fail`."""
    found = criteria_check.verdict(test, status, out)
    return "pass" if found == "pass" else "fail"


def blocked_path(folder):
    """A folder of stand-ins for GitHub, herdr and Claude, first on PATH, so a replay writes to no live board or session."""
    folder.mkdir(parents=True, exist_ok=True)
    for tool in BLOCKED_TOOLS:
        stand_in = folder / tool
        stand_in.write_text(f"#!/bin/sh\necho '{tool} is off in this replay' >&2\nexit 1\n")
        stand_in.chmod(0o755)
    return folder


def clean_environment(scratch):
    """The environment of a clean run: the stand-ins first on PATH, no GitHub login, no herdr session, no CLAUDE.md or memory."""
    empty_gh = scratch / "gh-config"
    empty_gh.mkdir()
    environment = {**os.environ, **SWITCHES, "PATH": f"{blocked_path(scratch / 'blocked')}:{os.environ['PATH']}",
                   "GH_TOKEN": "off-in-replay", "GH_CONFIG_DIR": str(empty_gh)}
    for key in [key for key in environment if key.startswith("HERDR")]:
        environment.pop(key)
    return environment


def run_claude(command, cwd, environment):
    """The stream and the errors of a `claude -p` COMMAND, cut off at RUN_TIMEOUT."""
    try:
        done = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True, timeout=RUN_TIMEOUT,
                              stdin=subprocess.DEVNULL)
        return done.stdout, done.stderr
    except subprocess.TimeoutExpired as expired:
        return expired.stdout.decode() if isinstance(expired.stdout, bytes) else expired.stdout or "", f"timed out after {RUN_TIMEOUT} s"


def run_jobs(jobs, run_one, parallel, spent, budget, limit):
    """Starts each of JOBS as RUN_ONE(*job), PARALLEL at a time, and stops before the next could carry SPENT() past LIMIT at its BUDGET."""
    with concurrent.futures.ThreadPoolExecutor(parallel) as pool:
        running = []
        for job in jobs:
            while len(running) >= parallel:
                done, pending = concurrent.futures.wait(running, return_when=concurrent.futures.FIRST_COMPLETED)
                running = list(pending)
            if spent() + float(budget) * (len(running) + 1) > limit:
                print(f"stop: ${spent():.2f} spent; another run could pass ${limit:.0f}")
                break
            running.append(pool.submit(run_one, *job))
        concurrent.futures.wait(running)


def read_options(args, defaults):
    """DEFAULTS with each `--flag value` pair of ARGS set, or None when ARGS holds a flag DEFAULTS lacks or a flag with no value."""
    options = dict(defaults)
    while args:
        if args[0] not in options or len(args) < 2:
            return None
        options[args[0]], args = args[1], args[2:]
    return options


def read_records(folder):
    """The JSON record of each run kept in FOLDER, in file order."""
    return [json.loads(path.read_text()) for path in sorted(folder.glob("*.json"))] if folder.exists() else []


def weight(model):
    return next((value for key, value in WEIGHT.items() if key in (model or "")), 0.0)


def turn_input(usage):
    creation = usage.get("cache_creation") or {}
    hour = creation.get("ephemeral_1h_input_tokens", 0)
    minutes = creation.get("ephemeral_5m_input_tokens", usage.get("cache_creation_input_tokens", 0) - hour)
    return usage.get("input_tokens", 0) + 1.25 * minutes + 2 * hour + 0.1 * usage.get("cache_read_input_tokens", 0)


def write_rate(usage):
    return 2.0 if (usage.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0) else 1.25


def turn_units(turn):
    """A turn's bill in input-token units: its input side plus five times its output, times its model's weight."""
    return weight(turn["model"]) * (turn_input(turn["usage"]) + 5 * turn["usage"].get("output_tokens", 0))


def run_units(turns):
    return sum(turn_units(turn) for turn in turns)


def text_of(content):
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content or [] if isinstance(part, dict))


def read_events(stream):
    """The run's init event, hook event names, turns in order, tool uses by id, results in order and its result event."""
    init, hooks, turns, uses, results, result = {}, [], {}, {}, [], {}
    for position, line in enumerate(stream.splitlines()):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind, subtype = event.get("type"), event.get("subtype", "")
        if kind == "system" and subtype == "init":
            init = event
        elif kind == "system" and subtype == "hook_response":
            hooks.append(event.get("hook_name") or event.get("hook_event") or "")
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
    return init, hooks, sorted(turns.values(), key=lambda turn: turn["position"]), uses, results, result


def carry(tokens, position, turns):
    """The cost of TOKENS taken in at POSITION: written by the next turn, read by each turn after it."""
    later = [turn for turn in turns if turn["position"] > position]
    if not later:
        return 0.0
    first = later[0]
    return tokens * (weight(first["model"]) * write_rate(first["usage"]) + sum(weight(turn["model"]) * 0.1 for turn in later[1:]))
