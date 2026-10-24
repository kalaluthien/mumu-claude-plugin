#!/usr/bin/env python3
"""Ask for a wrap-up at a stop, with a sentence of counts the wrap-up skill routes on.

  signal-wrap-up.py                        the Stop hook: its payload on stdin,
                                           the plugin's data folder in CLAUDE_PLUGIN_DATA;
                                           WRAP_UP=off silences it and writes nothing
  signal-wrap-up.py <transcript|session>   print the sentence for a transcript's last stop
  signal-wrap-up.py outcome <data> <session> filed|empty
                                           report what a session's last asked wrap-up did

A dream rides on a lesson or recipe ask, since a dream alone rarely pays.
Enabling the plugin for a project is the opt-in, so no arm step writes to the
data folder. Asks are scored by fixtures/replay-score.py on fixtures/labels.json, and
fixtures/replay-sessions.py replays fixtures/sessions.json; the other fixtures are
trimmed past stops to run the sentence on.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import memory as memory_file  # noqa: E402
import transcript  # noqa: E402

FAILURE_POINTS = 4
CALLS_PER_POINT = 30
START, UP, DOWN, LOWEST, HIGHEST = 8.0, 1.0, 0.125, 6.0, 12.0
MEMORY_LIMIT = 8
FIRST_RETRO = 25
ASK_GAP = 3
TEMPLATE = (transcript.SIGNAL + " {failures} failed tool calls and {calls} tool calls since the last stop "
            "make {points:g} lesson points of {threshold:g}; this session's first retro {first}; {memory} memory files changed since the last "
            "dream, of {memory_limit}; run recipe: {recipe}{generator}.")
ASK = " Run the wrap-up skill with this sentence before you stop."
RUNS = re.compile(r"\b(pytest|tox|nox|make|cmake|gradlew|mvn|cargo\s+(test|build|run)|go\s+(test|build|run)"
                  r"|swift\s+(test|build|run)|xcodebuild|(npm|pnpm|yarn|bun)\s+(run\s+)?(test|build|start|dev)"
                  r"|uvx?\s+run|docker\s+(compose|build|run))\b")
RECIPE = re.compile(r"(^|[:/])run-[\w-]+")


def segment(entries):
    """Entries since the previous stop, a trailing stop entry dropped."""
    end = len(entries)
    while end and transcript.is_stop(entries[end - 1]):
        end -= 1
    start = next((i + 1 for i in range(end - 1, -1, -1) if transcript.is_stop(entries[i])), 0)
    return entries[start:end]


def toplevel(cwd):
    run = subprocess.run(["git", "-C", cwd or ".", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return run.stdout.strip() if run.returncode == 0 else None


def has_recipe(cwd):
    root = toplevel(cwd)
    folder = os.path.join(root, ".claude", "skills") if root else None
    return bool(folder and os.path.isdir(folder) and any(n.startswith("run-") for n in os.listdir(folder)))


def counts(entries, cwd):
    uses, failures, calls, memory, ran_failed, recipe_failed = {}, 0, 0, set(), False, False
    for entry in segment(entries):
        for use in transcript.blocks_of(entry, "tool_use"):
            calls += 1
            uses[use.get("id")] = use
            memory.update(memory_file.PATH.findall(json.dumps(use.get("input") or {})))
        for result in transcript.blocks_of(entry, "tool_result"):
            if not result.get("is_error"):
                continue
            failures += 1
            use = uses.get(result.get("tool_use_id")) or {}
            given = use.get("input") or {}
            said = given.get("skill") or given.get("command") or ""
            if (use.get("name") == "Skill" and RECIPE.search(said)) or ".claude/skills/run-" in said:
                recipe_failed = True
            elif use.get("name") == "Bash" and RUNS.search(said):
                ran_failed = True
    recipe = "failed" if recipe_failed else "missing" if ran_failed and not has_recipe(cwd) else "fine"
    session = sum(len(transcript.blocks_of(entry, "tool_use")) for entry in entries)
    return {"failures": failures, "calls": calls, "memory": memory, "recipe": recipe, "session": session,
            "points": round(failures * FAILURE_POINTS + calls / CALLS_PER_POINT, 1)}


def bounded(threshold):
    return min(HIGHEST, max(LOWEST, threshold))


def load(data):
    """The saved state, each key that is missing or of the wrong type taken from the defaults."""
    state = {"threshold": START, "memory": [], "asked": {}, "pending": {}}
    try:
        with open(os.path.join(data, "wrap-up.json"), encoding="utf-8") as handle:
            saved = json.load(handle)
    except (OSError, ValueError):
        saved = {}
    if isinstance(saved, dict):
        state.update((key, saved[key]) for key in state
                     if isinstance(saved.get(key), (int, float) if key == "threshold" else type(state[key])))
    state["threshold"] = bounded(state["threshold"])
    return state


def save(data, state):
    os.makedirs(data, exist_ok=True)
    with open(os.path.join(data, "wrap-up.json"), "w", encoding="utf-8") as handle:
        json.dump(state, handle)


def fixed():
    value = os.environ.get("WRAP_UP_THRESHOLD")
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def threshold_of(state):
    override = fixed()
    return state["threshold"] if override is None else bounded(override)


def first_retro(found, asked):
    if asked:
        return "asked"
    return "due" if found["session"] >= FIRST_RETRO else f"at {found['session']} of {FIRST_RETRO} tool calls"


def sentence(found, threshold):
    generator = "" if found["recipe"] == "fine" else ", to record with /run-skill-generator"
    return TEMPLATE.format(threshold=threshold, memory_limit=MEMORY_LIMIT, generator=generator, **found)


def hook():
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not data or os.environ.get("WRAP_UP") == "off":
        return 0
    payload = json.load(sys.stdin)
    entries = transcript.entries_of(payload.get("transcript_path") or "")
    if entries is None:
        return 0
    entrypoint = next((str(e["entrypoint"]) for e in entries if "entrypoint" in e), "")
    if fixed() is None and entrypoint.startswith("sdk"):
        return 0
    state = load(data)
    found = counts(entries, payload.get("cwd"))
    state["memory"] = sorted(set(state["memory"]) | found["memory"])
    threshold = threshold_of(state)
    session, stops = payload.get("session_id", ""), sum(1 for e in entries if transcript.is_stop(e))
    # the stops right after an ask hold the wrap-up's own work and its fallout
    just_asked = stops - state["asked"].get(session, -ASK_GAP - 1) <= ASK_GAP
    # a stop the hook already blocked still counts, since the wrap-up writes its lessons in that turn
    # a session past a short fix owes one retro, whatever the lesson threshold, which other sessions' outcomes move
    first = first_retro(found, session in state["asked"]) == "due"
    lesson = found["points"] >= threshold or found["recipe"] != "fine"
    if not payload.get("stop_hook_active") and not just_asked and (lesson or first) and toplevel(payload.get("cwd")):
        reason = sentence(dict(found, memory=len(state["memory"]), first=first_retro(found, False)), threshold) + ASK
        state["asked"][session] = stops
        # only a lesson ask's outcome tunes the lesson threshold
        if lesson:
            state["pending"][session] = True
        if len(state["memory"]) >= MEMORY_LIMIT:
            state["memory"] = []
        json.dump({"decision": "block", "reason": reason}, sys.stdout)
    save(data, state)
    return 0


def outcome(data, session, result):
    state = load(data)
    if state["pending"].pop(session, False):
        step = UP if result == "empty" else -DOWN
        state["threshold"] = bounded(state["threshold"] + step)
        save(data, state)
    print(f"wrap-up outcome {result}: lesson threshold now {state['threshold']:g}")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(hook())
    if args[0] == "outcome" and len(args) == 4 and args[3] in ("filed", "empty"):
        sys.exit(outcome(args[1], args[2], args[3]))
    if len(args) == 1 and args[0] != "outcome":
        path = transcript.find(args[0])
        entries = transcript.entries_of(path or "")
        if entries is None:
            print(f"no transcript: {args[0]}", file=sys.stderr)
            sys.exit(1)
        cwd = next((e["cwd"] for e in reversed(entries) if e.get("cwd")), None)
        data = os.environ.get("CLAUDE_PLUGIN_DATA")
        state = load(data or os.devnull)
        found = counts(entries, cwd)
        asked = any(transcript.asked_at(entry) for entry in entries)
        print(sentence(dict(found, memory=len(found["memory"]), first=first_retro(found, asked)), threshold_of(state)))
        sys.exit(0)
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    sys.exit(2)
