#!/usr/bin/env python3
"""Sort a contract's edges against its sources: which relations the files show, which only the contract claims, which only the files show.

usage: sort-edges.py <contract> --root <subject root>

A node maps to the sources its `files` names. One file refers to another when its text holds the other's file name, or the other's
name without its extension as a whole word when that one is code. For each pair of mapped nodes that share no file it prints
`convergent` when an edge joins them and a file of one refers to a file of the other, `divergent` when an edge joins them and no
file does, and `absent` when a file does and no edge joins them, in either direction; a divergent edge is a relation at run time
or a wrong one, and an absent one is a relation the contract leaves out, so each is a gap to settle. It first prints
`missing path` for each mapped source that is no file under the root, and exits 1 on one, 0 otherwise.
"""
import itertools
import json
import pathlib
import re
import sys

CODE = (".py", ".js", ".cjs", ".mjs", ".ts", ".sh")


def refers(text, path):
    """Whether TEXT names the file at PATH."""
    if path.name in text:
        return True
    return path.suffix in CODE and re.search(r"(?<![\w-])" + re.escape(path.stem) + r"(?![\w-])", text) is not None


def sorted_edges(contract, root):
    """The missing paths, then the convergent, divergent and absent lines of CONTRACT under ROOT."""
    paths = {source["id"]: root / source["path"] for source in contract.get("sources", [])}
    nodes = {node["id"]: node["files"] for node in contract["nodes"] if node.get("files")}
    mapped = sorted({name for files in nodes.values() for name in files})
    missing = [f"{name}: {paths[name].relative_to(root) if name in paths else 'no such source'}" for name in mapped if name not in paths or not paths[name].is_file()]
    texts = {name: paths[name].read_text(errors="replace") for name in mapped if name in paths and paths[name].is_file()}
    joined = {}
    for edge in contract.get("edges", []):
        joined.setdefault(frozenset((edge["from"], edge["to"])), []).append(edge["id"])
    lines = {"convergent": [], "divergent": [], "absent": []}
    for one, other in itertools.combinations(sorted(nodes), 2):
        if set(nodes[one]) & set(nodes[other]):
            continue
        named = sorted(f"{paths[a].name} names {paths[b].name}" for a, b in list(itertools.product(nodes[one], nodes[other])) + list(itertools.product(nodes[other], nodes[one]))
                       if a in texts and b in texts and refers(texts[a], paths[b]))
        edges = joined.get(frozenset((one, other)), [])
        if edges and named:
            lines["convergent"].append(f"{one} and {other}: {', '.join(edges)}; {named[0]}")
        elif edges:
            lines["divergent"].append(f"{one} and {other}: {', '.join(edges)}; no file of one names a file of the other")
        elif named:
            lines["absent"].append(f"{one} and {other}: no edge; {named[0]}")
    return missing, lines


def main(args):
    if len(args) != 3 or args[1] != "--root" or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        missing, lines = sorted_edges(json.loads(pathlib.Path(args[0]).read_text()), pathlib.Path(args[2]))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(f"{args[0]}: {e!r}; run check-contract.py check on it first", file=sys.stderr)
        return 2
    print("".join(f"missing path {line}\n" for line in missing), end="")
    for kind, meaning in (("convergent", "the files show the relation"), ("divergent", "only the contract claims it"), ("absent", "only the files show it")):
        print(f"{kind} {len(lines[kind])}: {meaning}")
        print("".join(f"  {line}\n" for line in lines[kind]), end="")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
