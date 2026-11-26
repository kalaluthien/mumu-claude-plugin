"""The records every contract holds, whatever its skill: sources, terms, areas, claims and questions, with the rules that check
them, so both checkers hold one definition and word each break alike; a skill adds its own records and says which of its
records a claim's `on` and a question's `answers` may name."""
import re

from contract_fields import cited

KINDS = ("guarantee", "assumption")  # Zave and Jackson's split: what the subject keeps true, and what it takes the world to be
STRENGTHS = ("must", "should", "may")
STATUSES = ("holds", "fails", "conflicting", "unknown")
BASES = ("observed", "documented", "inferred")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
LISTS = ("avoid", "aliases", "on", "answers", "evidence")  # each a list of strings, `aliases` the one that may hold an empty entry
FIELDS = {
    "sources": ({"id": str, "path": str, "says": str}, {"authority": str}),
    "terms": ({"term": str, "meaning": str}, {"coined": bool, "avoid": list, "aliases": list}),
    "areas": ({"id": str, "label": str}, {"purpose": str, "aliases": list, "evidence": list, "basis": str}),
    "claims": ({"id": str, "title": str, "kind": str, "statement": str},
               {"strength": str, "status": str, "fault": str, "source": str, "on": list, "paths": list, "evidence": list, "basis": str}),
    "questions": ({"id": str, "asks": str}, {"answers": list}),
}
RULES = {
    "unique-ids": "an id is lowercase words and digits joined by `-`, used once in the whole contract",
    "area-known": "a node's `area` names an area it may sit in, and every area holds one node at least",
    "claim-form": f"one guarantee at least is stated; a claim's kind is one of {', '.join(KINDS)}, its strength one of {', '.join(STRENGTHS)} and its status one of {', '.join(STATUSES)}, "
                  "`holds` when none is written; a claim that does not hold says why in `fault`, as may one that holds with no document stating it; "
                  "`source` names the source that set the claim, and each `on` names a record the claim is about, never a source, a claim or a question",
    "claim-paths": "a guarantee alone holds `paths`, two different chains of edges that start at one node and end at one node, none of them marked `many`; "
                   "it writes no status, since the checker settles it from the paths",
    "evidence-source": "an evidence entry is a source id, `id:line` or `id:line-line`; under --root each source path that is no url exists and holds the lines cited",
    "question-answered": "one rebuild question at least is asked; each names in `answers` the records that answer it, one at least with evidence, "
                         "or a claim whose `fault` says why no source does",
}


def record_breaks(where, holder, fields, optional, texts=LISTS):
    """Breaks of the `form` rule on one record HOLDER: its required FIELDS and OPTIONAL ones, each a name over its type, and
    each of them named in TEXTS a list of strings."""
    if not isinstance(holder, dict):
        return [(where, "form", "must be an object")]
    found = []
    for name, form in fields.items():
        if not isinstance(holder.get(name), form) or form is str and not holder[name].strip():
            found.append((where, "form", f"`{name}` is missing or no {form.__name__}"))
    for name in sorted(set(holder) - set(fields) - set(optional)):
        found.append((where, "form", f"`{name}` is no field here"))
    for name, form in optional.items():
        if name in holder and not isinstance(holder[name], form):
            found.append((where, "form", f"`{name}` must be a {form.__name__}"))
    for name in texts:
        if isinstance(holder.get(name), list) and not all(isinstance(entry, str) and (entry.strip() or name == "aliases") for entry in holder[name]):
            found.append((where, "form", f"`{name}` must be a list of strings"))
    if "basis" in holder and holder["basis"] not in BASES:
        found.append((where, "form", f"`basis` is one of {', '.join(BASES)}"))
    return found


def id_breaks(named):
    """Breaks of `unique-ids` among NAMED, each (where, id) in the order a reader meets them."""
    found, seen = [], {}
    for where, name in named:
        if not SLUG.fullmatch(name):
            found.append((where, "unique-ids", f"`{name}` is not lowercase words joined by `-`, so no text can name it as `{{id}}`"))
        if name in seen:
            found.append((where, "unique-ids", f"`{name}` is also {seen[name]}"))
        seen.setdefault(name, where)
    return found


def source_breaks(sources, root):
    """Breaks of `evidence-source` by a source whose path is not under ROOT."""
    return [(f"sources {source['id']}", "evidence-source", f"`{source['path']}` is not under {root}") for source in sources.values()
            if root is not None and "://" not in source["path"] and not (root / source["path"]).exists()]


def area_breaks(areas, nodes, where, beyond=""):
    """Breaks of `area-known` among AREAS and the NODES that may sit in them, each placed by WHERE of its kind, `nodes` or
    `areas`, and its record; BEYOND says where else an area would have to be."""
    named = {area["id"] for area in areas}
    found = [(where("nodes", node), "area-known", f"`area` names `{node['area']}`, which is no area{beyond}") for node in nodes if "area" in node and node["area"] not in named]
    held = {node.get("area") for node in nodes}
    return found + [(where("areas", area), "area-known", "holds no node; an area groups one node at least") for area in areas if area["id"] not in held]


def chained(paths, edges):
    """Whether PATHS are two different chains of the EDGES by id, each edge leading to the next, with one start and one end."""
    return (isinstance(paths, list) and len(paths) == 2 and paths[0] != paths[1]
            and all(isinstance(path, list) and path and all(isinstance(key, str) and key in edges for key in path)
                    and all(edges[key]["to"] == edges[after]["from"] for key, after in zip(path, path[1:])) for path in paths)
            and edges[paths[0][0]]["from"] == edges[paths[1][0]]["from"] and edges[paths[0][-1]]["to"] == edges[paths[1][-1]]["to"])


def claim_breaks(claims, sources, root, about, edges):
    """Breaks of `claim-form`, `claim-paths` and `evidence-source` on CLAIMS; ABOUT is the ids an `on` may name, and EDGES the edges
    by id that `paths` may follow."""
    found = []
    if not any(claim["kind"] == "guarantee" for claim in claims):
        found.append(("claims", "claim-form", "state one guarantee at least: what the subject keeps true while its purpose is met"))
    for claim in claims:
        where = f"claims {claim['id']}"
        found += [(where, "evidence-source", message) for entry in claim.get("evidence", []) for message in cited(entry, sources, root)]
        if claim["kind"] not in KINDS or claim.get("strength", "must") not in STRENGTHS or claim.get("status", "holds") not in STATUSES:
            found.append((where, "claim-form", f"kind is one of {', '.join(KINDS)}; strength of {', '.join(STRENGTHS)}; status of {', '.join(STATUSES)}"))
        elif claim.get("status", "holds") != "holds" and not claim.get("fault", "").strip():
            found.append((where, "claim-form", f"is `{claim['status']}` and says no `fault`; say why it does not hold"))
        if "source" in claim and claim["source"] not in sources:
            found.append((where, "claim-form", f"`source` names `{claim['source']}`, which is no source"))
        found += [(where, "claim-form", f"`on` names `{name}`, which is no record a claim can be about") for name in claim.get("on", []) if name not in about]
        if "paths" not in claim:
            continue
        if claim["kind"] != "guarantee":
            found.append((where, "claim-paths", "an assumption holds no `paths`; only a guarantee is shown by two paths that agree"))
        if "status" in claim:
            found.append((where, "claim-paths", "holds `paths` and a written `status`; take the status out, since the checker settles it from the paths"))
        if not chained(claim["paths"], edges):
            found.append((where, "claim-paths", "`paths` holds two different chains of edge ids with one start and one end"))
        elif any(edges[key].get("many") for path in claim["paths"] for key in path):
            found.append((where, "claim-paths", "a path crosses an edge marked `many`, which leads to several things, so the two paths cannot be said to agree"))
    return found


def question_breaks(questions, records, proven, claims):
    """Breaks of `question-answered`: RECORDS is the ids an answer may name, PROVEN those that carry evidence, CLAIMS the claims by id."""
    if not questions:
        return [("questions", "question-answered", "ask one rebuild question at least: what a reader must learn from the contract to rebuild the subject")]
    found = []
    for question in questions:
        where, answers = f"questions {question['id']}", question.get("answers", [])
        found += [(where, "question-answered", f"`answers` names `{name}`, which is no record of the contract") for name in answers if name not in records]
        if not answers:
            found.append((where, "question-answered", "has no answer: name in `answers` the records that answer it, or the claim whose `fault` says why no source does"))
        elif not proven & set(answers) and not any(claims.get(name, {}).get("fault", "").strip() for name in answers):
            found.append((where, "question-answered", "no record in `answers` carries `evidence` and no claim in it says in `fault` why none can, so the answer has no source"))
    return found
