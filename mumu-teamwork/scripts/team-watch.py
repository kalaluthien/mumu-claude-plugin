#!/usr/bin/env python3
"""The `team-watch` monitor, run in a lead's checkout: one line per change of its workers, and one while its team sits idle.

A `<folder>-lead`, its folder in the checkout, watches only the workers whose task carries `scope:<folder>`."""
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import gh  # noqa: E402
import herdr  # noqa: E402
import sessions  # noqa: E402

REPEAT = 3600
WORD = {"blocked": "blocked", "idle": "idle", "done": "idle", "working": "working"}


def changes(last, now):
    """Next `{name: word}` and the lines to print, from the last words and herdr's `{name: agent_status}` now."""
    words = {name: WORD.get(status, last.get(name, "working")) for name, status in now.items()}
    lines = [f"{w} {name}" for name, w in words.items() if w != last.get(name, "working")]
    return words, lines + [f"gone {name}" for name in last if name not in now]


def folder(listed, checkout):
    """This pane's lead folder, or None for a `<repo>-lead` or a session that is no lead."""
    name = next((a.get("name") or "" for a in listed if a.get("pane_id") == os.environ.get("HERDR_PANE_ID")), "")
    f = name.removesuffix("-lead")
    return f if f != name and f and (pathlib.Path(checkout) / f).is_dir() else None


def scoped(workers, checkout, f, owned):
    """The `workers` whose task carries `scope:<f>`, reading each new name's task once into `owned`; all of them without `f`."""
    if not f:
        return workers
    for name in workers.keys() - owned.keys():
        try:
            owned[name] = f"scope:{f}" in gh.labels(checkout, sessions.WORKER.fullmatch(name)[2])
        except (RuntimeError, ValueError, KeyError, TypeError):
            pass  # read again at the next poll
    return {name: s for name, s in workers.items() if owned.get(name)}


def main():
    if os.environ.get("MUMU_ROLE") == "worker":
        return
    checkout, ticks = os.getcwd(), int(os.environ.get("MONITOR_TICKS", 0))
    interval, after = float(os.environ.get("MONITOR_POLL", 10)), float(os.environ.get("TEAM_WATCH_IDLE", 1200))
    last, since, printed, n, owned, f = {}, None, None, 0, {}, None  # the team quiet since, the idle line printed at
    while not ticks or n < ticks:
        n += 1
        try:
            listed = herdr.listed("agent")
            f = folder(listed, checkout)
            last, lines = changes(last, scoped(sessions.workers(listed, checkout), checkout, f, owned))
        except RuntimeError:
            time.sleep(interval)
            continue
        now = time.time()
        if "working" in last.values():
            since = printed = None
        else:
            since = since or now
            if now - since >= after and (printed is None or now - printed >= REPEAT) and gh.held(checkout, f):
                printed = now
                lines.append(f"team idle {int((now - since) // 60)}m")
        for line in lines:
            print(line, flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
