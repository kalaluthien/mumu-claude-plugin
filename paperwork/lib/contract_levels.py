"""Turn a contract between the shape its file holds, one list each of nodes, edges and areas, and levels that hold their own."""


def nested(contract):
    """CONTRACT with each level holding the areas and nodes that name it and the edges that leave its nodes; an edge that
    leaves no node goes to the first level, where the checker reports it."""
    levels = [dict(level) for level in contract["levels"]]
    held = {level["id"]: {"areas": [], "nodes": [], "edges": []} for level in levels}
    home = {}
    for kind in ("areas", "nodes"):
        for element in contract.get(kind, []):
            if element.get("level") in held:
                held[element["level"]][kind].append({name: value for name, value in element.items() if name != "level"})
                home[element["id"]] = element["level"] if kind == "nodes" else home.get(element["id"])
    for edge in contract.get("edges", []):
        held[home.get(edge["from"]) or levels[0]["id"]]["edges"].append(edge)
    for level in levels:
        level.update({kind: group for kind, group in held[level["id"]].items() if group or kind == "nodes"})
    whole = {name: value for name, value in contract.items() if name not in ("areas", "nodes", "edges")}
    whole["levels"] = levels
    return whole


def flat(contract):
    """CONTRACT, whose levels hold their own areas, nodes and edges, in the shape its file holds."""
    whole = {}
    for name, value in contract.items():
        if name != "levels":
            whole[name] = value
            continue
        whole["levels"] = [{key: part for key, part in level.items() if key not in ("areas", "nodes", "edges")} for level in value]
        for kind in ("areas", "nodes"):
            whole[kind] = [{**{key: part for key, part in element.items() if key in ("id", "label", "tag")}, "level": level["id"],
                            **{key: part for key, part in element.items() if key not in ("id", "label", "tag")}} for level in value for element in level.get(kind, [])]
        whole["edges"] = [edge for level in value for edge in level.get("edges", [])]
    return whole
