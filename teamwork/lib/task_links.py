"""Links between tasks: the tasks a task waits on, its record's `depends`, and its parts, the
`N. [task] #n` lines of its body's Definition of done. A task waits on what it depends on and on its parts, so a cycle is
looked for over both kinds together."""
import re

import issue_state
import legacy_records

PART = re.compile(r"^\s*(?:\d+\.|[-*])\s+\[task\]\s+#(\d+)\b", re.M)
DONE = ("COMPLETED", None, "")


def parts(body):
    """The numbers its Definition of done names as parts, in order, each once."""
    return list(dict.fromkeys(int(n) for n in PART.findall(issue_state.sections(body).get("done", ""))))


def depends(record):
    """The numbers of the tasks RECORD waits on, each once: its `depends`, else those an older body names."""
    stored = record.get("depends")
    return list(dict.fromkeys(stored)) if stored is not None else legacy_records.depends(record.get("body"))


def criteria(body):
    """Its Definition of done lines that are not parts."""
    return [line for line in issue_state.ITEM.findall(issue_state.sections(body).get("done", "")) if not line.lstrip().startswith("[task]")]


def completed(issue):
    """Whether a closed issue was closed as completed, which alone releases what waits on it."""
    return issue.get("state") == "CLOSED" and (issue.get("stateReason") or issue.get("reason")) in DONE


def refusals(number, body, waits, read, parent_of):
    """Why NUMBER (None for an issue not yet filed) cannot have BODY and wait on the tasks WAITS numbers, each naming the issues; empty when it can.
    READ(n) gives issue n's record, None when it does not exist; PARENT_OF(n) the issue whose body names n as a part, else None."""
    found, named = [], parts(body)
    records = {n: read(n) for n in dict.fromkeys(waits + named) if n != number}
    found += [f"#{n} does not exist" for n, record in records.items() if record is None]
    found += [f"#{n} is a pull request, not an issue" for n, record in records.items() if record and record.get("isPullRequest")]
    for part in named:
        owner = parent_of(part) if part != number else None
        if owner is not None and owner != number:
            found.append(f"#{part} is already a part of #{owner}, and a task has one parent")
    if number is not None:
        loop = cycle(number, waits + named, read)
        if loop:
            found.append("a cycle " + " → ".join(f"#{n}" for n in loop) + ": drop one of its links")
    return found


def cycle(number, targets, read):
    """The path from NUMBER back to itself over both link kinds, when its new TARGETS close one; else None."""
    paths, seen = [[number, target] for target in targets], set()
    while paths:
        path = paths.pop()
        if path[-1] == number:
            return path
        if path[-1] in seen:
            continue
        seen.add(path[-1])
        record = read(path[-1])
        if record:
            paths += [path + [n] for n in depends(record) + parts(record["body"])]
    return None


def derive(nodes, read):
    """The open ones of NODES, issues in the shape the issue pane draws, with `parent`, `subIssues`, `subIssuesSummary` and `blockedBy` set from
    their bodies; a closed node only lends its title and state, and READ(n) gives a record for an issue the nodes lack, else None."""
    by_number = {node["number"]: node for node in nodes}
    lookup = lambda n: by_number.get(n) or read(n)
    owner = {part: node["number"] for node in nodes for part in parts(node["body"])}
    for node in nodes:
        node["parent"] = {"number": owner[node["number"]]} if node["number"] in owner else None
        waits = [record for record in map(lookup, depends(node)) if record]
        node["blockedBy"] = {"nodes": [{"number": record["number"], "state": record.get("state", "OPEN"), "stateReason": record.get("stateReason")} for record in waits]}
        found = [record for record in map(lookup, parts(node["body"])) if record]
        node["subIssues"] = {"nodes": [{"number": record["number"], "title": record["title"], "url": record["url"], "state": record.get("state", "OPEN"),
                                        "stateReason": record.get("stateReason"), "trusted": record.get("trusted", True),
                                        "blockedBy": {"nodes": [{"number": n} for n in depends(record)]}} for record in found]}
        node["subIssuesSummary"] = {"total": len(found), "completed": sum(completed(record) for record in found)}
    for node in nodes:
        for sub_issue in node["subIssues"]["nodes"]:
            sub_issue["blockedBy"]["nodes"] = [{"number": n, "state": record.get("state", "OPEN"), "stateReason": record.get("stateReason")}
                                               for n in (wait["number"] for wait in sub_issue["blockedBy"]["nodes"]) for record in [lookup(n)] if record]
    return [node for node in nodes if node.get("state", "OPEN") == "OPEN"]


RETIRED_LABEL = "backlog"  # the label that marked a parent before parts did; no open issue keeps it


def drift(nodes):
    """Each link gap among NODES, open issues as a board's tree gives them: a cycle, a part two bodies name and the retired label;
    two concurrent writes can each pass alone."""
    by_number = {node["number"]: node for node in nodes}
    found, seen = [], set()
    for node in nodes:
        loop = cycle(node["number"], depends(node) + parts(node["body"]), lambda n: by_number.get(n))
        if loop and frozenset(loop) not in seen:
            seen.add(frozenset(loop))
            found.append(f"cycle {' → '.join(f'#{n}' for n in loop)}: drop one of its links")
    owners = {}
    for node in nodes:
        for part in parts(node["body"]):
            owners.setdefault(part, []).append(node["number"])
    found += [f"second parent #{part}: {' and '.join(f'#{n}' for n in claims)} each name it as a part; keep one" for part, claims in owners.items() if len(claims) > 1]
    found += [f"label #{node['number']}: it keeps the retired `{RETIRED_LABEL}` label; drop it" for node in nodes
              if RETIRED_LABEL in [label["name"] for label in (node.get("labels") or {}).get("nodes", [])]]
    return found
