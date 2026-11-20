#!/usr/bin/env python3
"""Run the real Stop hook over a recorded week of stops and print `PASS` when it asks for wrap-up 80% to 90% as often as
the hook did before, and still asks every session whose wrap-up filed a lesson at or after the first stop where it filed, else `FAIL`, each dropped or added ask and the counts going to stderr.

usage: replay-wrap-up-rate.py
       replay-wrap-up-rate.py record   write the hook's asks as the week's base asks

`wrap-up-week.json` holds each stop in time order as [session, tool calls since the last stop, failed tool calls, the
outcome of the wrap-up asked there: filed, empty, none, or "" when none was asked], with no session text, path or id.
An ask takes the outcome of the session's recorded ask at that stop or within the next ASK_GAP stops, since the
recorded hook sometimes asked a stop later, and reports it to the hook as the wrap-up skill does.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
HOOK = str(HERE.parent / "signal-wrap-up.py")
WEEK = HERE / "wrap-up-week.json"
ASK_GAP = 3
LOW, HIGH = 0.8, 0.9


def outcome_near(stops, index):
    """The recorded outcome of the first ask at this stop or the next ASK_GAP stops of the same session."""
    for outcome in stops[index:index + ASK_GAP + 1]:
        if outcome:
            return outcome
    return "unknown"


def replay(week):
    """The hook's asks over the week, as [session, stop number within it, outcome] in time order."""
    by_session = {}
    for session, _, _, outcome in week:
        by_session.setdefault(session, []).append(outcome)
    asks, seen = [], {}
    with tempfile.TemporaryDirectory() as temp:
        root = pathlib.Path(temp)
        config, home, repository, folder = root / "config", root / "memory", root / "repository", root / "sessions"
        for path in (config, home, repository, folder):
            path.mkdir()
        subprocess.run(["git", "-C", str(repository), "init", "-q"], check=True)
        (config / "settings.json").write_text(json.dumps({"autoMemoryDirectory": str(home)}))
        env = {key: value for key, value in os.environ.items() if not key.startswith("HOMEWORK_")}
        env.update(CLAUDE_CONFIG_DIR=str(config), CLAUDE_PLUGIN_DATA=str(root / "data"))
        for session, calls, failures, _ in week:
            path = folder / f"{session}.jsonl"
            index = seen.get(session, 0)
            seen[session] = index + 1
            with open(path, "a", encoding="utf-8") as handle:
                for number in range(calls):
                    handle.write(json.dumps({"message": {"content": [{"type": "tool_use", "id": f"t{number}", "input": {}}]}}) + "\n")
                    error = number < failures
                    handle.write(json.dumps({"message": {"content": [{"type": "tool_result", "tool_use_id": f"t{number}",
                                                                     "is_error": error}]}}) + "\n")
            payload = json.dumps({"session_id": session, "transcript_path": str(path), "cwd": str(repository)})
            run = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True, env=env)
            if run.stdout.strip():
                outcome = outcome_near(by_session[session], index)
                asks.append([session, index + 1, outcome])
                if outcome in ("filed", "empty"):
                    subprocess.run([sys.executable, HOOK, "outcome", str(home), session, outcome],
                                   check=True, capture_output=True, env=env)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps({"type": "system", "subtype": "stop_hook_summary"}) + "\n")
    return asks


def main(args):
    if args not in ([], ["record"]):
        print(__doc__, file=sys.stderr)
        return 2
    data = json.loads(WEEK.read_text())
    asks = replay(data["stops"])
    if args == ["record"]:
        data["base"] = asks
        WEEK.write_text('{"stops": [\n' + ",\n".join(json.dumps(stop) for stop in data["stops"]) + "\n],\n"
                        '"base": [\n' + ",\n".join(json.dumps(ask) for ask in asks) + "\n]}\n")
        print(f"recorded {len(asks)} base asks")
        return 0
    base = data["base"]
    ratio = len(asks) / len(base)
    asked = {}
    for session, stop, _ in asks:
        asked.setdefault(session, []).append(stop)
    head = {(session, stop) for session, stop, _ in asks}
    for session, stop, outcome in base:
        if (session, stop) not in head:
            later = [new for new in asked.get(session, []) if new > stop]
            print(f"dropped: {session} stop {stop}, base outcome {outcome}" + (f", next ask at stop {later[0]}" if later else ""), file=sys.stderr)
    first_filed = {}
    for session, stop, outcome in base:
        if outcome == "filed":
            first_filed.setdefault(session, stop)
    unasked = [f"{session} filed at stop {stop}" for session, stop in first_filed.items()
               if not any(new >= stop for new in asked.get(session, []))]
    for session, stop, outcome in asks:
        if (session, stop) not in {(s, n) for s, n, _ in base}:
            print(f"added: {session} stop {stop}, outcome {outcome}", file=sys.stderr)
    print(f"asks: {len(asks)} of {len(base)} base asks ({ratio:.0%}); filed sessions left unasked: {len(unasked)}", file=sys.stderr)
    for line in unasked:
        print(f"unasked: {line}", file=sys.stderr)
    passed = asks and LOW <= ratio <= HIGH and not unasked
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
