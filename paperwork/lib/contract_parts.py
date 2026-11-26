"""A contract's parts, each edited, checked and built alone: `top`, the records no level holds, and `levels/<id>`, one level with the
records it shows. A contract is one JSON file, split into its parts in memory, or a folder of part files, `top.json` and
`levels/<id>.json`, whose paths a task's criterion names. A part's check reads the other parts only as its view keeps them, so a part
whose view is unchanged keeps its earlier result."""
import hashlib
import json
import pathlib
import re

SYSTEM = {"held": {"areas": "level", "nodes": "level", "edges": "from"}, "after": "levels"}
FLOW = {"held": {"edges": "level", "tasks": "level", "fragments": "level", "milestones": "level"}, "after": "nodes"}
TOP = "top"
SPOKEN = ("about", "basis", "evidence", "info", "purpose")  # what no rule of another level reads
READ_BY_TOP = ("evidence", "purpose")  # what the top's scenarios, properties and questions read of a level
TOP_WORDS = {"contract", "title", "purpose", "source", "sources", "term", "terms", "group", "groups", "scenario", "scenarios",
             "property", "properties", "question", "questions"}


def level_part(name):
    return f"levels/{name}"


def homes(contract, shape):
    """Each held record's level id, by list name and position, for CONTRACT in the shape its file holds: a system edge's is that of
    the node it leaves."""
    placed = {record.get("id"): record.get("level") for record in contract.get("nodes", []) if isinstance(record, dict)}
    return {kind: [record.get("level") if how == "level" else placed.get(record.get("from")) for record in contract.get(kind, [])]
            for kind, how in shape["held"].items()}


def split(contract, shape):
    """The parts of CONTRACT, in the shape its file holds, by part name in reading order: the top, then each level. ValueError when a
    break could not be told to one part: the contract's form is broken, a record names no level, or two parts hold one id."""
    try:
        home = homes(contract, shape)
        levels = [level["id"] for level in contract["levels"]]
        owners = {}
        for kind, at in home.items():
            for record, level in zip(contract.get(kind, []), at):
                if level not in levels or owners.setdefault(record["id"], level) != level:
                    raise ValueError(f"`{record['id']}` sits in no level or in two")
    except (KeyError, TypeError, AttributeError) as e:
        raise ValueError(f"the contract's form is broken: {e}") from None
    top = {name: value for name, value in contract.items() if name not in shape["held"]}
    top["levels"] = [level["id"] for level in contract["levels"]]
    parts = {TOP: top}
    for level in contract["levels"]:
        part = dict(level)
        for kind in shape["held"]:
            held = [record for record, at in zip(contract.get(kind, []), home[kind]) if at == level["id"]]
            if held or kind in contract:
                part[kind] = [{name: value for name, value in record.items() if name != "level"} for record in held]
        parts[level_part(level["id"])] = part
    return parts


def join(parts, shape):
    """The contract, in the shape its file holds, that PARTS split from, its held lists right after the field the shape names."""
    top = parts[TOP]
    contract = {}
    for name, value in top.items():
        contract[name] = [{key: entry for key, entry in parts[level_part(level)].items() if key not in shape["held"]} for level in value] if name == "levels" else value
        if name == shape["after"]:
            for kind, how in shape["held"].items():
                held = [(level, record) for level in top["levels"] for record in parts[level_part(level)].get(kind, [])]
                if held or any(kind in parts[level_part(level)] for level in top["levels"]):
                    contract[kind] = [{**record, "level": level} if how == "level" else record for level, record in held]
    return contract


def read(path, shape):
    """The parts of the contract at PATH, a JSON file or a folder of part files, as written: ValueError names the part file that is
    no object, holds a list of SHAPE's records that is no list of objects, or is missing from or unlisted in `top.json`."""
    path = pathlib.Path(path)
    if not path.is_dir():
        return None, json.loads(path.read_text())
    top = json.loads((path / "top.json").read_text())
    if not isinstance(top, dict) or not isinstance(top.get("levels"), list) or not all(isinstance(name, str) for name in top["levels"]):
        raise ValueError(f"{path / 'top.json'}: `levels` must list the level ids in order")
    parts = {TOP: top}
    for name in top["levels"]:
        file = path / "levels" / f"{name}.json"
        part = json.loads(file.read_text())
        if not isinstance(part, dict) or not all(isinstance(part.get(kind, []), list) and all(isinstance(record, dict) for record in part.get(kind, []))
                                                 for kind in shape["held"]):
            raise ValueError(f"{file}: a level's part is an object whose {', '.join(shape['held'])} are lists of objects")
        parts[level_part(name)] = part
    unlisted = sorted(file.name for file in (path / "levels").glob("*.json") if file.stem not in top["levels"])
    if unlisted:
        raise ValueError(f"{path / 'levels'}: {', '.join(unlisted)} names no level top.json lists")
    return parts, None


def load(path, shape):
    """The contract at PATH, a JSON file or a folder of part files, in the shape a file holds."""
    parts, whole = read(path, shape)
    return whole if parts is None else join(parts, shape)


def write(folder, parts):
    """Write PARTS as part files under FOLDER, and return their paths."""
    folder = pathlib.Path(folder)
    written = []
    for name, value in parts.items():
        file = folder / f"{name}.json"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        written.append(file)
    return written


def view(parts, name, shape):
    """The contract the check of part NAME reads, in the shape a file holds: that part and the top whole, and of every other level
    only the fields a rule of NAME compares across records, so an edit elsewhere that leaves them alone leaves NAME's check as it was."""
    dropped = tuple(field for field in SPOKEN if not (name == TOP and field in READ_BY_TOP))
    shown = {}
    for part, value in parts.items():
        if part in (name, TOP):
            shown[part] = value
        else:
            shown[part] = {key: [{field: entry for field, entry in record.items() if field not in dropped} if isinstance(record, dict) else record
                                 for record in entry] if key in shape["held"] and isinstance(entry, list) else entry
                           for key, entry in value.items() if key not in dropped}
    return join(shown, shape)


def owner(where, contract, shape):
    """The part a break at WHERE belongs to, WHERE read against CONTRACT, the contract that was checked, or None when WHERE names no
    part or every reading of it does not name the same one, since a break given to the wrong part is dropped."""
    home = homes(contract, shape)
    levels = [level["id"] for level in contract["levels"]]
    named = set()
    indexed = re.match(r"(?P<kind>\w+)(?P<mark>\[|/)(?P<at>\d+)\b", where)
    if indexed and indexed["kind"] in contract and isinstance(contract[indexed["kind"]], list):
        kind, k = indexed["kind"], int(indexed["at"]) - (indexed["mark"] == "/")  # a path names a list entry from 1
        at = levels if kind == "levels" else home.get(kind)
        named.add(TOP if at is None else level_part(at[k]) if k < len(at) and at[k] in levels else None)
    words = [word for word in re.split(r"[\s/\[\].]+", where) if word]
    if words and (words[0] in TOP_WORDS or words[0] in contract and words[0] not in shape["held"] and words[0] != "levels"):
        named.add(TOP)
    held = {record.get("id"): at for kind in home for record, at in zip(contract.get(kind, []), home[kind]) if isinstance(record, dict)}
    named |= {level_part(word) for word in words if word in levels}
    named |= {level_part(held[word]) if held[word] in levels else None for word in words if word in held}
    return named.pop() if len(named) == 1 else None


def checked(contract, chosen, shape, check):
    """The breaks CHECK finds in the parts CHOSEN of CONTRACT, each part read from its view; a contract that splits into no parts, whose
    parts join in another order, since a break names a record by its place in CONTRACT, or one of whose breaks names no part, is checked
    whole. ValueError names a part CONTRACT lacks."""
    try:
        parts = split(contract, shape)
    except ValueError:
        return check(contract)
    if join(parts, shape) != contract:
        return check(contract)
    unknown = [name for name in chosen if name not in parts]
    if unknown:
        raise ValueError(f"{', '.join(unknown)} is no part; one of {', '.join(parts)}")
    found = []
    for name in [name for name in parts if name in chosen]:
        shown = view(parts, name, shape)
        owned = [(owner(entry[0], shown, shape), entry) for entry in check(shown)]
        if any(part is None for part, _ in owned):
            return check(contract)
        found += [entry for part, entry in owned if part == name]
    return found


def split_to(source, folder, shape):
    """Write the parts of the contract at SOURCE as files under FOLDER, and return their paths; ValueError when FOLDER holds files or
    the contract cannot be split."""
    target = pathlib.Path(folder)
    if target.exists() and any(target.iterdir()):
        raise ValueError(f"{folder} holds files already; split into an empty or new folder")
    try:
        parts = split(load(source, shape), shape)
    except ValueError as e:
        raise ValueError(f"{e}; fix the breaks `check` prints first") from None
    return write(target, parts)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def code_digest(files):
    """One digest of the code FILES, so a change to the checker or the builder makes every part's key new."""
    sha = hashlib.sha256()
    for file in sorted(files):
        sha.update(file.name.encode() + b"\0" + file.read_bytes())
    return sha.hexdigest()[:16]


def keys(parts, shape, code):
    """Each part's key: its view and the CODE digest, which together decide its check and its build."""
    return {name: digest([code, view(parts, name, shape)]) for name in parts}
