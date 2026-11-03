"""Links between tasks, read from bodies only: a task's `depends on` line in its teamwork block, and its parts, the
`N. [task] #n` lines of its Definition of done. A task waits on what it depends on and on its parts, so a cycle is
looked for over both kinds together."""
import re

import issue_state

PART = re.compile(r"^\s*(?:\d+\.|[-*])\s+\[task\]\s+#(\d+)\b", re.M)
NUMBER = re.compile(r"#(\d+)\b")
# GitHub's limits on a task's native `blocked by` links and sub-issues
MOST_DEPENDS, MOST_PARTS = 50, 100
DONE = ("COMPLETED", None, "")


def parts(body):
    """The numbers its Definition of done names as parts, in order, each once."""
    return list(dict.fromkeys(int(n) for n in PART.findall(issue_state.sections(body).get("done", ""))))


def depends(body):
    """The numbers its `depends on` line names, each once."""
    return list(dict.fromkeys(int(n) for n in NUMBER.findall(issue_state.data(body).get(issue_state.WORD["depends"], ""))))


def criteria(body):
    """Its Definition of done lines that are not parts."""
    return [line for line in issue_state.ITEM.findall(issue_state.sections(body).get("done", "")) if not line.lstrip().startswith("[task]")]


def completed(issue):
    """Whether a closed issue was closed as completed, which alone releases what waits on it."""
    return issue.get("state") == "CLOSED" and (issue.get("stateReason") or issue.get("reason")) in DONE


def refusals(number, body, read, parent_of):
    """Why BODY cannot be NUMBER's body (None for an issue not yet filed), each naming the issues; empty when it can.
    READ(n) gives issue n's record, None when it does not exist; PARENT_OF(n) the issue whose body names n as a part, else None."""
    found, waits, named = [], depends(body), parts(body)
    if len(waits) > MOST_DEPENDS:
        found.append(f"{len(waits)} `depends on` entries, more than GitHub's {MOST_DEPENDS}")
    if len(named) > MOST_PARTS:
        found.append(f"{len(named)} parts, more than GitHub's {MOST_PARTS}")
    if found:  # each named issue is a read, so a list past the limit is refused before them
        return found
    records = {n: read(n) for n in dict.fromkeys(waits + named) if n != number}
    found += [f"#{n} does not exist" for n, record in records.items() if record is None]
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
            paths += [path + [n] for n in depends(record["body"]) + parts(record["body"])]
    return None


def derive(nodes, read):
    """The open ones of NODES, issues in GitHub's shape, with `parent`, `subIssues`, `subIssuesSummary` and `blockedBy` set from
    their bodies; a closed node only lends its title and state, and READ(n) gives a record for an issue the nodes lack, else None."""
    by_number = {node["number"]: node for node in nodes}
    lookup = lambda n: by_number.get(n) or read(n)
    owner = {part: node["number"] for node in nodes for part in parts(node["body"])}
    for node in nodes:
        node["parent"] = {"number": owner[node["number"]]} if node["number"] in owner else None
        waits = [record for record in map(lookup, depends(node["body"])) if record]
        node["blockedBy"] = {"nodes": [{"number": record["number"], "state": record.get("state", "OPEN"), "stateReason": record.get("stateReason")} for record in waits]}
        found = [record for record in map(lookup, parts(node["body"])) if record]
        node["subIssues"] = {"nodes": [{"number": record["number"], "title": record["title"], "url": record["url"], "state": record.get("state", "OPEN"),
                                        "stateReason": record.get("stateReason"), "trusted": record.get("trusted", True),
                                        "blockedBy": {"nodes": [{"number": n} for n in depends(record.get("body", ""))]}} for record in found]}
        node["subIssuesSummary"] = {"total": len(found), "completed": sum(completed(record) for record in found)}
    for node in nodes:
        for sub_issue in node["subIssues"]["nodes"]:
            sub_issue["blockedBy"]["nodes"] = [{"number": n, "state": record.get("state", "OPEN"), "stateReason": record.get("stateReason")}
                                               for n in (wait["number"] for wait in sub_issue["blockedBy"]["nodes"]) for record in [lookup(n)] if record]
    return [node for node in nodes if node.get("state", "OPEN") == "OPEN"]


RETIRED_LABEL = "backlog"  # the label that marked a parent before parts did; no open issue keeps it


def drift(nodes):
    """Each link gap among NODES, open issues as a board's tree gives them: a cycle, a part two bodies name, the retired label,
    and, on GitHub, a native link no body names or a body link with no native one; two concurrent writes can each pass alone."""
    by_number = {node["number"]: node for node in nodes}
    found, seen = [], set()
    for node in nodes:
        loop = cycle(node["number"], depends(node["body"]) + parts(node["body"]), lambda n: by_number.get(n))
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
    for node in nodes:
        native = node.get("native")
        if native is None:
            continue
        for kind, said in (("parts", parts(node["body"])), ("depends", depends(node["body"]))):
            extra, missing = sorted(set(native[kind]) - set(said)), sorted(set(said) - set(native[kind]))
            word = "part" if kind == "parts" else "`depends on`"
            found += [f"native-only #{node['number']}: GitHub links #{n} as its {word}, which its body does not name; add the line or drop the link" for n in extra]
            found += [f"body-only #{node['number']}: its body names #{n} as its {word}, which GitHub does not link; run `use-board.py edit` again" for n in missing]
    return found
