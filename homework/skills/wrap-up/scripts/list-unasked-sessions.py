#!/usr/bin/env python3
"""List, by cause, the interactive sessions of at least 25 tool calls that the wrap-up hook never asked, so a gap in the asks has a count.

usage: list-unasked-sessions.py <projects-folder>

<projects-folder> holds one folder per project of session transcripts, `~/.claude/projects` in a normal setup. A session
counts when its `entrypoint` is not `sdk`, it has FIRST_RETRO or more tool calls and no stop carried the ask.
Its cause is `no stop` when it never stopped, `hook absent` when no stop summary lists `signal-wrap-up`, so the plugin
was not enabled for that project, else `hook ran, no ask`. It prints one `<cause>: <session file>` line per session,
then `unasked: <n> sessions, <cause> <count>, ...` and exits 0.
"""
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import transcript  # noqa: E402

FIRST_RETRO = 25  # the hook's own limit of tool calls for a session's first retro


def cause_of(entries):
    """The cause a session of enough tool calls was never asked, None when it was asked, is too short or is headless."""
    entrypoint = next((str(entry["entrypoint"]) for entry in entries if "entrypoint" in entry), "")
    calls = sum(len(transcript.blocks_of(entry, "tool_use")) for entry in entries)
    stops = [entry for entry in entries if transcript.is_stop(entry)]
    if entrypoint.startswith("sdk") or calls < FIRST_RETRO or any(transcript.asked_at(entry) for entry in stops):
        return None
    if not stops:
        return "no stop"
    listed = any("signal-wrap-up" in str(info.get("command")) for entry in stops for info in entry.get("hookInfos") or [])
    return "hook ran, no ask" if listed else "hook absent"


def main(args):
    if len(args) != 1 or args[0].startswith("-") or not pathlib.Path(args[0]).is_dir():
        print(__doc__, file=sys.stderr)
        return 2
    causes = collections.Counter()
    for path in sorted(pathlib.Path(args[0]).glob("*/*.jsonl")):
        entries = transcript.entries_of(str(path))
        cause = cause_of(entries) if entries else None
        if cause:
            causes[cause] += 1
            print(f"{cause}: {path}")
    print(f"unasked: {sum(causes.values())} sessions" + "".join(f", {cause} {count}" for cause, count in sorted(causes.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
