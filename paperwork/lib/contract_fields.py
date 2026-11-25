"""The checks of one field both contract checkers share: whether a value has an item's form, and whether an evidence entry names its source."""
import re


def fits(value, form):
    """True when VALUE has the shape FORM asks."""
    if form in ("text", "code"):
        return isinstance(value, str) and bool(value.strip())
    if form == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) or isinstance(value, str) and bool(value.strip())
    if form == "list":
        return isinstance(value, list) and bool(value) and all(isinstance(entry, str) for entry in value)
    if form == "table":
        return (isinstance(value, dict) and set(value) == {"columns", "rows"} and isinstance(value["columns"], list) and bool(value["columns"])
                and all(isinstance(name, str) for name in value["columns"]) and isinstance(value["rows"], list)
                and all(isinstance(row, list) and len(row) == len(value["columns"]) and all(isinstance(cell, (str, int, float)) and not isinstance(cell, bool) for cell in row)
                        for row in value["rows"]))
    return isinstance(value, list) and bool(value) and all(
        isinstance(entry, dict) and isinstance(entry.get("name"), str) and set(entry) <= {"name", "note", "children"} and isinstance(entry.get("note", ""), str)
        and ("children" not in entry or fits(entry["children"], "tree")) for entry in value)


def cited(entry, sources, root):
    """What is wrong with one evidence ENTRY: an unknown source, or lines the source's file does not hold."""
    name, _, lines = entry.partition(":")
    if name not in sources:
        return [f"`{entry}` opens with no source id; one of {', '.join(sources) or 'none, since the contract lists no source'}"]
    span = re.fullmatch(r"(\d+)(?:-(\d+))?", lines)
    if lines and not (span and 1 <= int(span.group(1)) <= int(span.group(2) or span.group(1))):
        return [f"`{entry}` must end with a line or a range of lines, such as `{name}:7` or `{name}:7-15`"]
    path = None if root is None or "://" in sources[name]["path"] else root / sources[name]["path"]
    if span and path is not None and path.is_file() and int(span.group(2) or span.group(1)) > len(path.read_text(errors="replace").splitlines()):
        return [f"`{entry}` names a line past the end of `{sources[name]['path']}`"]
    return []
