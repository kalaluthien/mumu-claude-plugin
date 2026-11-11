"""The data of a record written before `use-board.py` took it as options: `key: value` lines in a `teamwork` fence and a `decision` fence
inside the text, read into the fields board-record-schema.json names. No write makes such a record, so this module goes once no board holds one."""
import re

DATA = re.compile(r"^```teamwork\n(.*?)^```", re.M | re.S)
DECISION = re.compile(r"^```decision\n(.*?)^```", re.M | re.S)
DIFF = re.compile(r"^(`{3,})diff\n(.*?)^\1$", re.M | re.S)
# the day decisions became typed: a question asked before it also closes on a later `DECIDED:` that is no event
TYPED_SINCE = "2026-11-05"
STOPPING = "DECIDED: stopping #"


def pairs(block):
    return {key.strip(): value.strip() for key, separator, value in (line.partition(":") for line in block.splitlines()) if separator}


def data(text):
    return {key: value for block in DATA.findall(text or "") for key, value in pairs(block).items()}


def depends(body):
    """The task numbers a body's `depends on` line names, each once."""
    return list(dict.fromkeys(int(n) for n in re.findall(r"#(\d+)\b", data(body).get("depends on", ""))))


def fields(text):
    """The fields of a comment's TEXT; `untyped` marks a `DECIDED:` that holds no decision and is no event, which answered a question asked before TYPED_SINCE."""
    text = text or ""
    raw, found = data(text), {}
    if "holders" in raw:
        found["holders"] = raw["holders"].split()
    if raw.get("asks") == "owner":
        found["asks"] = "owner"
    if raw.get("live runs", "").isdigit():
        found["live_runs"] = int(raw["live runs"])
    block = DECISION.search(text)
    if block:
        said = pairs(block.group(1))
        found.update({"decision": said.get("decision", ""), "by": said.get("decided by", "")})
        if said.get("door") == "one-way":
            found["one_way"] = True
        lead = re.match(r"\s*[A-Z]+:\s*answers:[ \t]*(\S+)", text)
        for key, value in (("supersedes", said.get("supersedes")), ("answers", said.get("answers") or (lead and lead.group(1)))):
            if value:
                found[key] = value
    elif not (DATA.search(text) or DIFF.search(text) or text.startswith(STOPPING)):
        found["untyped"] = True
    return found
