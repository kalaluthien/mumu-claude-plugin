"""Dream's replay: dejavu's owner corrections as cases, the files each candidate made a judge recall, and their marks."""
import hashlib
import json
import pathlib

import memory_home

HELD_OUT_SHARE = 5
ASKED_CHARS = 400
THEN_CHARS = 800
# a mark on the instruction files, which load alike for every candidate
INSTRUCTIONS = "instructions"


def flat(text):
    return " ".join(str(text or "").split())


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def said(entry):
    """What a transcript entry says: a person's prompt as ("asked", text), the agent's words and tool calls as ("then", text)."""
    message = entry.get("message") or {}
    body = message.get("content")
    if entry.get("type") == "user" and not entry.get("isMeta"):
        if isinstance(body, str):
            return "asked", body
        texts = [block.get("text", "") for block in body or [] if isinstance(block, dict) and block.get("type") == "text"]
        return ("asked", " ".join(texts)) if texts else (None, "")
    if entry.get("type") == "assistant" and isinstance(body, list):
        parts = []
        for block in body:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                parts.append(f"[{block.get('name')} {flat(json.dumps(block.get('input'), ensure_ascii=False))[:200]}]")
        return "then", " ".join(parts)
    return None, ""


def read_transcript(path):
    """The transcript's entries, numbered as dejavu numbers a case's `line`, dropping a line that is no JSON, and its first `cwd`."""
    entries, cwd = [], None
    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                entries.append(entry if isinstance(entry, dict) else {})
                cwd = cwd or entries[-1].get("cwd")
    except OSError:
        pass
    return entries, cwd


def situation(entries, line):
    """The person's last prompt before transcript line `line` (1-based, the owner's correction) and what the agent did after it."""
    asked, then = "", []
    end = int(number(line))
    # a line past the transcript's end would show the owner's own words, so it shows nothing
    for entry in entries[:max(end - 1, 0)] if end <= len(entries) else []:
        kind, text = said(entry) if not entry.get("isSidechain") else (None, "")
        if kind == "asked" and text.strip():
            asked, then = text, []
        elif kind == "then" and text.strip():
            then.append(text)
    return f"asked: {flat(asked)[:ASKED_CHARS]} | then: {flat(' '.join(then))[-THEN_CHARS:]}"


def root_of(cwd):
    top = memory_home.git(cwd, "rev-parse", "--show-toplevel")
    return pathlib.Path(top or cwd)


def instruction_files(root, config):
    """The instruction files that load in a session at root, whatever its memory: the config's and the repository's own."""
    config = pathlib.Path(config)
    found = [config / "CLAUDE.md", *sorted((config / "rules").glob("*.md"))]
    if root:
        found += [root / "AGENTS.md", root / "CLAUDE.md"]
    # a session in the config folder itself loads its CLAUDE.md once
    return list(dict.fromkeys(path.resolve() for path in found if path.is_file()))


def load(dejavu, config=None):
    """Each case of `<dejavu>/friction.jsonl`, oldest first, with `held_out`, `folder`, `situation` and `instructions` added; [] when missing."""
    dejavu = pathlib.Path(dejavu)
    cases, cache = [], {}
    try:
        lines = (dejavu / "friction.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict) and item.get("id"):
            cases.append(item)
    cases.sort(key=lambda item: (number(item.get("time")), number(item.get("line")), str(item["id"])))
    held = len(cases) // HELD_OUT_SHARE
    for index, item in enumerate(cases):
        item["held_out"] = index >= len(cases) - held
        path = str(dejavu / item["path"]) if item.get("path") else ""
        if path not in cache:
            entries, cwd = read_transcript(path) if path else ([], None)
            live = bool(cwd) and pathlib.Path(cwd).is_dir()
            cache[path] = (entries, memory_home.repository(cwd) if live else "-", root_of(cwd) if live else None)
        entries, item["folder"], root = cache[path]
        item["situation"] = situation(entries, item.get("line"))
        item["instructions"] = instruction_files(root, config) if config else []
    return cases


def candidates(dejavu):
    return sorted(path for path in (pathlib.Path(dejavu) / "candidates").glob("*") if path.is_dir())


def jsonl(paths):
    """Each JSON object of the files' lines, in order."""
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict) and "case" in item:
                yield item


def inside(candidate, files):
    """Whether `files` is a list of paths within the candidate, the only form a pick may take."""
    if not isinstance(files, list) or not all(isinstance(file, str) and file for file in files):
        return False
    root = pathlib.Path(candidate).resolve()
    return all((root / file).resolve().is_relative_to(root) for file in files)


def picks(dejavu, name):
    """Each case's recalled files, relative to candidate `name`, from `<dejavu>/picks/<name>/*.jsonl`; the last line wins.

    A line whose `recalled` is not a list of paths within the candidate is dropped, so its case counts as missing."""
    folder = pathlib.Path(dejavu) / "picks" / name
    candidate = pathlib.Path(dejavu) / "candidates" / name
    found = {}
    for item in jsonl(sorted(folder.glob("*.jsonl"))):
        files = item.get("recalled", [])
        if inside(candidate, files):
            found[str(item["case"])] = files
        else:
            found.pop(str(item["case"]), None)
    return found


def recall_set(candidate, files):
    """A key for what the recalled files say, so one text recalled by several candidates is marked once; None for no file."""
    if not files:
        return None
    texts = []
    for file in sorted(set(files)):
        try:
            texts.append([file, (pathlib.Path(candidate) / file).read_text(encoding="utf-8")])
        except OSError:
            texts.append([file, ""])
    return hashlib.sha1(json.dumps(texts).encode()).hexdigest()[:10]


def marks(dejavu):
    """(case, set or INSTRUCTIONS) -> (covered, misfire), from `<dejavu>/marks/*.jsonl`; the last line wins."""
    folder = pathlib.Path(dejavu) / "marks"
    return {(str(item["case"]), str(item.get("set"))): (bool(item.get("covered")), bool(item.get("misfire")))
            for item in jsonl(sorted(folder.glob("*.jsonl")))}


def verdict(candidate, files, case, marked):
    """(covered, misfire, missing) of one case for one candidate: covered by the instruction files' mark or its own set's."""
    if files is None:
        return False, False, True
    instructions = marked.get((case, INSTRUCTIONS))
    key = recall_set(candidate, files)
    own = marked.get((case, key)) if key else (False, False)
    missing = instructions is None or own is None
    covered = bool(instructions and instructions[0]) or bool(own and own[0])
    return covered, bool(own and own[1]), missing
