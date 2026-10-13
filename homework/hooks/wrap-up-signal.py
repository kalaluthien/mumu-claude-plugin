#!/usr/bin/env python3
"""Ask for a wrap-up at a stop, with a sentence of counts the wrap-up skill routes on.

  wrap-up-signal.py                        the Stop hook: its payload on stdin,
                                           the plugin's data folder in CLAUDE_PLUGIN_DATA
  wrap-up-signal.py <transcript|session>   print the sentence for a transcript's last stop
  wrap-up-signal.py outcome <data> filed|empty
                                           report what the last asked wrap-up did

The counts cover the segment since the previous stop: failed tool calls and
tool calls make lesson points, memory files written add to a count kept since
the last tidy, and a run recipe is `missing` when a build, test or launch
command failed in a repository with no `.claude/skills/run-*/` skill, `failed`
when a call of such a skill failed. The hook asks when the points reach the
threshold or the recipe is missing or failed, and a memory count at
MEMORY_LIMIT rides on that ask, since a tidy alone rarely pays. It never asks
at the stop right after its own ask, in a headless session, or while a Stop
hook already blocks.

The threshold adapts: each `empty` outcome raises it by UP and each `filed`
lowers it by DOWN, between LOWEST and HIGHEST, so it settles where about
DOWN / (UP + DOWN) of asks come back empty. WRAP_UP_THRESHOLD fixes it and lets a headless session ask too.
Replay on labelled past stops: replay-score.py.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import transcript  # noqa: E402

FAILURE_POINTS = 4
CALLS_PER_POINT = 30
START, UP, DOWN, LOWEST, HIGHEST = 8.0, 1.0, 0.125, 6.0, 12.0
MEMORY_LIMIT = 8
TEMPLATE = (transcript.SIGNAL + " {failures} failed tool calls and {calls} tool calls since the last stop "
            "make {points:g} lesson points of {threshold:g}; {memory} memory files changed since the last "
            "tidy, of {memory_limit}; run recipe: {recipe}{generator}.")
ASK = " Run the wrap-up skill with this sentence before you stop."
MEMORY = re.compile(r"/memory/(?!MEMORY\.md)([\w.-]+\.md)")
RUNS = re.compile(r"\b(pytest|tox|nox|make|cmake|gradlew|mvn|cargo\s+(test|build|run)|go\s+(test|build|run)"
                  r"|swift\s+(test|build|run)|xcodebuild|(npm|pnpm|yarn|bun)\s+(run\s+)?(test|build|start|dev)"
                  r"|uvx?\s+run|docker\s+(compose|build|run))\b")
RECIPE = re.compile(r"(^|[:/])run-[\w-]+")


def segment(entries):
    """Entries since the previous stop, a trailing stop entry dropped."""
    while entries and transcript.is_stop(entries[-1]):
        entries = entries[:-1]
    stops = [i for i, e in enumerate(entries) if transcript.is_stop(e)]
    return entries[stops[-1] + 1:] if stops else entries


def has_recipe(cwd):
    run = subprocess.run(["git", "-C", cwd or ".", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    root = run.stdout.strip() if run.returncode == 0 else None
    folder = os.path.join(root, ".claude", "skills") if root else None
    return bool(folder and os.path.isdir(folder) and any(n.startswith("run-") for n in os.listdir(folder)))


def counts(entries, cwd):
    uses, failures, calls, memory, ran_failed, recipe_failed = {}, 0, 0, set(), False, False
    for entry in segment(entries):
        for use in transcript.blocks_of(entry, "tool_use"):
            calls += 1
            uses[use.get("id")] = use
            memory.update(MEMORY.findall(json.dumps(use.get("input") or {})))
        for result in transcript.blocks_of(entry, "tool_result"):
            if not result.get("is_error"):
                continue
            failures += 1
            use = uses.get(result.get("tool_use_id")) or {}
            said = (use.get("input") or {}).get("skill") or (use.get("input") or {}).get("command") or ""
            if (use.get("name") == "Skill" and RECIPE.search(said)) or ".claude/skills/run-" in said:
                recipe_failed = True
            elif use.get("name") == "Bash" and RUNS.search(said):
                ran_failed = True
    recipe = "failed" if recipe_failed else "missing" if ran_failed and not has_recipe(cwd) else "fine"
    return {"failures": failures, "calls": calls, "memory": len(memory), "recipe": recipe,
            "points": round(failures * FAILURE_POINTS + calls / CALLS_PER_POINT, 1)}


def load(data):
    try:
        with open(os.path.join(data, "wrap-up.json"), encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {"threshold": START, "memory": 0, "asked": {}, "pending": False}


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


def sentence(found, threshold, memory):
    generator = "" if found["recipe"] == "fine" else ", to record with /run-skill-generator"
    return TEMPLATE.format(threshold=threshold, memory_limit=MEMORY_LIMIT, generator=generator,
                           **{**found, "memory": memory})


def hook():
    payload = json.load(sys.stdin)
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    entries = transcript.entries_of(payload.get("transcript_path") or "")
    if not data or entries is None or payload.get("stop_hook_active"):
        return 0
    override = fixed()
    if override is None and any(str(e.get("entrypoint", "")).startswith("sdk") for e in entries):
        return 0
    state = load(data)
    found = counts(entries, payload.get("cwd"))
    state["memory"] += found["memory"]
    threshold = state["threshold"] if override is None else override
    session, stops = payload.get("session_id", ""), sum(1 for e in entries if transcript.is_stop(e))
    # the stop right after an ask holds the wrap-up's own work
    just_asked = state["asked"].get(session) == stops - 1
    harvest = found["points"] >= threshold
    tidy = state["memory"] >= MEMORY_LIMIT
    if not just_asked and (harvest or found["recipe"] != "fine"):
        reason = sentence(found, threshold, state["memory"]) + ASK
        state["asked"][session], state["pending"] = stops, True
        state["memory"] = 0 if tidy else state["memory"]
        json.dump({"decision": "block", "reason": reason}, sys.stdout)
    save(data, state)
    return 0


def outcome(data, result):
    state = load(data)
    if state["pending"]:
        step = UP if result == "empty" else -DOWN
        state["threshold"] = min(HIGHEST, max(LOWEST, state["threshold"] + step))
        state["pending"] = False
        save(data, state)
    print(f"wrap-up outcome {result}: lesson threshold now {state['threshold']:g}")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(hook())
    if args[0] == "outcome" and len(args) == 3 and args[2] in ("filed", "empty"):
        sys.exit(outcome(args[1], args[2]))
    if len(args) == 1 and args[0] != "outcome":
        path = transcript.find(args[0])
        entries = transcript.entries_of(path or "")
        if entries is None:
            print(f"no transcript: {args[0]}", file=sys.stderr)
            sys.exit(1)
        cwd = next((e["cwd"] for e in reversed(entries) if e.get("cwd")), None)
        found = counts(entries, cwd)
        override = fixed()
        print(sentence(found, START if override is None else override, found["memory"]))
        sys.exit(0)
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    sys.exit(2)
