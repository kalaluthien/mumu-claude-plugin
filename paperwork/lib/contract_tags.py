"""A skill's tag catalogue: the shared one beside this module, which holds the item forms and the tags and common items both skills
use, with the skill's own catalogue over it, so a shared tag is written once and a skill adds only its own."""
import json
import pathlib

SHARED = pathlib.Path(__file__).resolve().parent / "tags.json"


def merged(own, shared):
    """The catalogue OWN over SHARED: SHARED's forms, each kind's tags with OWN's replacing one of the same name, and each kind's
    common items, SHARED's that OWN does not name, then OWN's as written, so a whole catalogue merged again stays the same and
    OWN's own faults, such as an item named twice, stay for the checker to find."""
    whole = {"forms": shared["forms"], "common": {}}
    for kind in dict.fromkeys([*shared["common"], *own.get("common", {})]):
        added = own.get("common", {}).get(kind, [])
        named = {item.get("name") for item in added if isinstance(item, dict)}
        whole["common"][kind] = [item for item in shared["common"].get(kind, []) if item["name"] not in named] + added
    for kind in dict.fromkeys([*shared, *own]):
        if kind not in ("forms", "common"):
            whole[kind] = {**shared.get(kind, {}), **own[kind]} if kind in own else dict(shared[kind])
    return whole


def catalogue(path):
    """The catalogue of the skill whose own catalogue is the file at PATH."""
    return merged(json.loads(pathlib.Path(path).read_text()), json.loads(SHARED.read_text()))
