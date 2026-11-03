"""Dream's replay cases: dejavu's owner corrections, oldest first, the newest fifth held out from revising."""
import json
import pathlib

import memory_home

HELD_OUT_SHARE = 5


def folder(transcript, cache):
    """The memory folder name of the repository a transcript ran in, read from its first recorded `cwd`; `-` when gone."""
    if transcript not in cache:
        cache[transcript] = "-"
        try:
            with open(transcript, encoding="utf-8") as handle:
                for line in handle:
                    cwd = json.loads(line).get("cwd")
                    if cwd:
                        if pathlib.Path(cwd).is_dir():
                            cache[transcript] = memory_home.repository(cwd)
                        break
        except (OSError, ValueError, AttributeError):
            pass
    return cache[transcript]


def load(dejavu):
    """Each case of `<dejavu>/friction.jsonl` as a dict with `held_out` and `folder` added; [] when the file is missing."""
    cases, cache = [], {}
    try:
        lines = (pathlib.Path(dejavu) / "friction.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict) and item.get("id"):
            cases.append(item)
    cases.sort(key=lambda item: (item.get("time") or 0, item.get("line") or 0, item["id"]))
    held = len(cases) // HELD_OUT_SHARE
    for index, item in enumerate(cases):
        item["held_out"] = index >= len(cases) - held
        item["folder"] = folder(item["path"], cache) if item.get("path") else "-"
    return cases
