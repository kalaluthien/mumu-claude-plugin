#!/usr/bin/env python3
"""The `team-watch` monitor, run in a lead's checkout: one line per change of its workers, and one while its team sits idle.

A `<folder>-lead`, its folder in the checkout, watches only the workers whose task carries `scope:<folder>`.

While a usage limit holds, read from a rejection that is the last reply in the lead's or a watched worker's transcript,
it prints nothing and polls nothing; once the limit resets it prints one `usage reset` line, once per lead and reset
across runs by a claim in the data folder given as its argument."""
import datetime
import glob
import json
import os
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import gh  # noqa: E402
import herdr  # noqa: E402
import sessions  # noqa: E402

REPEAT = 3600
WORD = {"blocked": "blocked", "idle": "idle", "done": "idle", "working": "working"}
TAIL = 256 * 1024  # bytes read of a transcript first seen
NAP = 300  # the longest sleep while a limit holds, so a clock change is seen within it


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


def stall(lines, prior=None):
    """The `resetsAt` of the rejection that is the last reply among transcript `lines`, None when a later reply is none, `prior` without a reply."""
    for line in lines:
        if '"assistant"' not in line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue  # cut at the tail's start, or garbage
        if not isinstance(entry, dict) or entry.get("type") != "assistant":
            continue
        quota = entry.get("quotaLimits")
        rejected = entry.get("error") == "rate_limit" and isinstance(quota, dict) and quota.get("status") == "rejected"
        prior = int(quota["resetsAt"]) if rejected and isinstance(quota.get("resetsAt"), (int, float)) else None
    return prior


def limit(stalls, now):
    """The latest reset still ahead among the sessions' `stalls`, or None when no limit holds."""
    return max((t for t in stalls if t and t > now), default=None)


def stalled(stalls, now):
    """The resets already passed that a session still stalls on, oldest first."""
    return sorted({t for t in stalls if t and t <= now})


def reset_line(at, words, lead_status):
    """The one line for a reset at `at`, naming the workers by `words`, or None while the lead works and no worker is idle."""
    idle = [n for n, w in words.items() if w == "idle"]
    if lead_status == "working" and not idle:
        return None
    groups = [f"{w} {' '.join(n for n, v in words.items() if v == w)}" for w in ("idle", "working", "blocked") if w in words.values()]
    return f"usage reset {datetime.datetime.fromtimestamp(at).strftime('%H:%M')}" + (": " + "; ".join(groups) if groups else "")


class Transcripts:
    """Each watched session's stall, reading only the bytes appended to its transcript since the last poll."""

    def __init__(self):
        self.config = pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR") or pathlib.Path.home() / ".claude")
        self.seen = {}  # session id: [path, offset, unfinished line, stall]

    def stalls(self, ids):
        out = []
        for sid in ids:
            s = self.seen.get(sid)
            if s is None:
                found = glob.glob(str(self.config / "projects" / "*" / f"{glob.escape(sid)}.jsonl"))
                if not found:
                    continue  # no transcript yet: looked for again at the next poll
                size = os.path.getsize(found[0])
                s = self.seen[sid] = [found[0], max(0, size - TAIL), b"", None]
            try:
                with open(s[0], "rb") as f:
                    f.seek(s[1])
                    data = f.read()
            except OSError:
                continue
            s[1] += len(data)
            *done, s[2] = (s[2] + data).split(b"\n")
            s[3] = stall([line.decode("utf-8", "replace") for line in done], s[3])
            out.append(s[3])
        return out


def claim(data, lead, at):
    """True the first time any run claims the reset at `at` for `lead`, by creating its file in `data`."""
    path = pathlib.Path(data) / "usage-reset" / f"{lead}-{at}"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        return True
    except FileExistsError:
        return False
    except OSError:
        return True  # an unwritable folder prints the line rather than lose it


def main():
    if os.environ.get("MUMU_ROLE") == "worker":
        return
    checkout, ticks = os.getcwd(), int(os.environ.get("MONITOR_TICKS", 0))
    interval, after = float(os.environ.get("MONITOR_POLL", 10)), float(os.environ.get("TEAM_WATCH_IDLE", 1200))
    margin = float(os.environ.get("TEAM_WATCH_MARGIN", 60))
    data = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else os.environ.get("CLAUDE_PLUGIN_DATA") or tempfile.gettempdir()
    pane, transcripts, done, held = os.environ.get("HERDR_PANE_ID"), Transcripts(), set(), False
    last, since, printed, n, owned, f = {}, None, None, 0, {}, None  # the team quiet since, the idle line printed at
    while not ticks or n < ticks:
        n += 1
        try:
            listed = herdr.listed("agent")
            f = folder(listed, checkout)
            workers = scoped(sessions.workers(listed, checkout), checkout, f, owned)
            words, lines = changes(last, workers)
        except RuntimeError:
            time.sleep(interval)
            continue
        lead = next((a for a in listed if a.get("pane_id") == pane), {})
        ids = [(a.get("agent_session") or {}).get("value") for a in listed if a is lead or a.get("name") in workers]
        stalls = [t + margin for t in transcripts.stalls([s for s in ids if s]) if t]
        now = time.time()
        if (until := limit(stalls, now)) is not None:
            held = True
            time.sleep(min(NAP, until - now))
            continue
        due = [t for t in stalled(stalls, now) if t not in done]
        if held or due:
            lines, since, printed = [], None, None  # a change while the limit held, or one a reset line names, is not told
        last, held = words, False
        for t in due:
            done.add(t)
            line = reset_line(t - margin, words, lead.get("agent_status"))
            if line and claim(data, lead.get("name") or pane, int(t - margin)):
                lines.append(line)
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
