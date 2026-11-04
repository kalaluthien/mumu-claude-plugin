"""Typed decisions across a root's tree, by the grammar's Decisions section: each task's binding set, the rules `decide` holds a
decision to, and the gaps the manager's heartbeat lists. ISSUES is {number: issue}, each with `body`, `trusted`, `state`,
`stateReason`, `parent` (a number, a {number} node or None) and `comments` (a list, or a {nodes} connection)."""
import datetime
import re

import issue_state
import task_links

DOORS = ("one-way", "two-way")
FIELD = issue_state.FIELD
SHOWN_DECIDED = 3  # the latest owner decisions the pane draws under a task; the rest it counts


def as_issue(node):
    """NODE with its comments as a list, as `issue_state.records` reads them."""
    comments = node.get("comments") or []
    return {**node, "comments": comments["nodes"] if isinstance(comments, dict) else comments}


def parent_of(issue):
    parent = issue.get("parent")
    return parent.get("number") if isinstance(parent, dict) else parent


def role(decider):
    """`owner`; `manager` for a session named `<project>-manager`, or `<project>-manager-next`, the name Succession gives; else `worker`."""
    return "owner" if decider == "owner" else "manager" if decider == "manager" or decider.removesuffix("-next").endswith("-manager") else "worker"


def quoted(text):
    """Whether TEXT, outside its fenced blocks, quotes someone's words: a `>` line or a span in double quotes."""
    prose = re.sub(r"^(`{3,}).*?^\1", "", text or "", flags=re.M | re.S)
    return bool(re.search(r'^>\s*\S|"[^"\n]{2,}"|“[^”\n]{2,}”', prose, re.M))


def typed(number, issue):
    """The decisions on one issue, oldest first, untrusted comments left out."""
    found = []
    for index, (word, _, comment) in enumerate(issue_state.records(as_issue(issue))[1:]):
        fields = issue_state.decision(comment["body"]) if issue_state.KEYWORDS.get(word) == "answer" else None
        if fields is None:
            continue
        decider = fields.get(FIELD["decider"], "")
        found.append({"task": number, "index": index, "url": comment["url"], "createdAt": comment.get("createdAt") or "",
                      "decision": fields.get(FIELD["decision"], ""), "decider": decider, "role": role(decider),
                      "door": fields.get(FIELD["door"], ""), "supersedes": fields.get(FIELD["supersedes"], ""),
                      "answers": fields.get(FIELD["answers"], ""), "depends": [int(n) for n in re.findall(r"#(\d+)", fields.get(FIELD["depends"], ""))]})
    return found


def chain(number, issues):
    """NUMBER, then its ancestors as far as ISSUES holds them, nearest first."""
    found = [number]
    while (parent := parent_of(issues[found[-1]])) in issues and parent not in found:
        found.append(parent)
    return found


def tree_of(root, issues):
    return [number for number in issues if chain(number, issues)[-1] == root]


def binds(decision, every):
    """Whether a decision binds by its door: a worker's one-way decision only once a later manager or owner decision on its task
    repeats or supersedes it."""
    if decision["role"] != "worker" or decision["door"] != "one-way":
        return True
    return any(later["task"] == decision["task"] and later["index"] > decision["index"] and later["role"] != "worker"
               and (later["decision"] == decision["decision"] or later["supersedes"] == decision["url"]) for later in every)


def replaced(every):
    """The urls of the decisions in EVERY that a decision passed by its door supersedes; one still behind its door replaces nothing."""
    return {decision["supersedes"] for decision in every if decision["supersedes"] and binds(decision, every)}


def binding(number, issues):
    """NUMBER's binding set: the decisions on it and its ancestors that no decision in the root's tree passed by its door supersedes,
    and whose door is passed, oldest first; none once the root was closed as not planned."""
    lineage = chain(number, issues)
    root = issues[lineage[-1]]
    if root.get("state") == "CLOSED" and not task_links.completed(root):
        return []
    every = [decision for task in tree_of(lineage[-1], issues) for decision in typed(task, issues[task])]
    superseded = replaced(every)
    return sorted((decision for decision in every if decision["task"] in lineage and decision["url"] not in superseded and binds(decision, every)),
                  key=lambda decision: (decision["createdAt"], decision["task"], decision["index"]))


def read(number, fresh):
    """{number: issue} of NUMBER's root's tree, by FRESH, the board's `fresh`: up by each parent, then down by each body's parts."""
    issues, number, root = {}, int(number), None
    while number is not None and number not in issues:
        found = fresh(number)
        if found is None:
            raise LookupError(f"cannot read #{number}")
        issues[number], root, number = found, number, parent_of(found)
    pending, seen = [root], {root}
    while pending:
        for part in task_links.parts(issues[pending.pop()]["body"]):
            if part not in issues and (found := fresh(part)) is not None:
                issues[part] = found
            if part in issues and part not in seen:
                seen.add(part)
                pending.append(part)
    return issues


def refusals(number, text, issues):
    """Why TEXT cannot be posted as a decision on NUMBER, given its root's tree ISSUES; empty when it can, or holds no decision block."""
    fields = issue_state.decision(text)
    if fields is None:
        return []
    found = [f"the decision block lacks `{FIELD[key]}:`" for key in ("decision", "decider", "door") if not fields.get(FIELD[key])]
    if fields.get(FIELD["door"]) and fields[FIELD["door"]] not in DOORS:
        found.append(f"`{FIELD['door']}:` is `{fields[FIELD['door']]}`, not one of {', '.join(DOORS)}")
    owner = role(fields.get(FIELD["decider"], "")) == "owner"
    if owner and not quoted(text):
        found.append(f"`{FIELD['decider']}: owner` quotes no words of the owner's, as a `>` line or in double quotes")
    answered = fields.get(FIELD["answers"])
    if answered and answered not in [question["ask"]["url"] for question in issue_state.questions(as_issue(issues[int(number)]))]:
        home = next((task for task, issue in issues.items() for comment in as_issue(issue)["comments"] if comment.get("url") == answered), None)
        found.append(f"`{FIELD['answers']}:` names {answered}, which is no question on #{number}"
                     + (f"; post the decision on #{home}, the question's own task" if home and home != int(number) else ""))
    replaced = fields.get(FIELD["supersedes"])
    if replaced:
        root = chain(int(number), issues)[-1]
        every = {decision["url"]: decision for task in tree_of(root, issues) for decision in typed(task, issues[task])}
        if replaced not in every:
            found.append(f"`{FIELD['supersedes']}:` names {replaced}, which is no decision in #{root}'s tree")
        elif every[replaced]["role"] == "owner" and not owner:
            found.append(f"{replaced} was `{FIELD['decider']}: owner`, so only a decision by the owner, quoting the owner's words, supersedes it")
    return found


def first_line(comment):
    """A comment's first line of text without its keyword, the line after a keyword that stands alone."""
    return next((line.strip() for line in re.sub(r"^\s*[A-Z]+:", "", (comment["body"] or "").strip()).splitlines() if line.strip()), "")


def gaps(found):
    """The heartbeat's decision lines for the open issues FOUND: open questions to the owner, oldest first; a decision two later
    ones supersede; a worker's one-way decision nothing supersedes and no manager or owner decision follows; a `DECIDED:` posted since decisions were typed
    with no block that is no event."""
    issues = {issue["number"]: as_issue(issue) for issue in found}
    asked = sorted(((question["ask"].get("createdAt") or "", number, question["ask"]) for number, issue in issues.items()
                    for question in issue_state.open_questions(issue) if question["fields"].get(issue_state.WORD["audience"]) == "owner"),
                   key=lambda item: item[0])
    lines = [f"question #{number}: {first_line(ask)} ({ask['url']}) waits on the owner; ask the owner, then record the answer by `decide` "
             f"with `{FIELD['decider']}: owner` and `{FIELD['answers']}:` its url" for _, number, ask in asked]
    every = [decision for number, issue in issues.items() for decision in typed(number, issue)]
    for url in sorted({decision["supersedes"] for decision in every if decision["supersedes"]}):
        later = [decision for decision in every if decision["supersedes"] == url]
        if len(later) > 1:
            lines.append(f"superseded twice #{later[0]['task']}: {url} is superseded by {' and '.join(decision['url'] for decision in later)}; "
                         f"keep one by a decision that supersedes the other")
    superseded = replaced(every)
    for decision in every:
        if decision["url"] not in superseded and not binds(decision, every):
            lines.append(f"one-way #{decision['task']}: {decision['decider']}'s {decision['url']} binds only once you repeat or supersede it by `decide`")
    for number, issue in issues.items():
        for word, _, comment in issue_state.records(issue)[1:]:
            if (issue_state.KEYWORDS.get(word) == "answer" and issue_state.decision(comment["body"]) is None and not issue_state.event(comment)
                    and not issue_state.legacy(comment)):
                lines.append(f"untyped #{number}: {comment['url']} is a {issue_state.WORD['answer']}: with no decision block, which no index reads; "
                             f"post it again by `decide` with one")
    return lines


def superseded_in(nodes):
    """The urls of the decisions among NODES that a decision passed by its door supersedes, read once for a whole draw."""
    return replaced([decision for node in nodes for decision in typed(node["number"], node)])


def stamp(created):
    """CREATED, a board timestamp such as `2026-11-04T04:00:00Z`, as `MM/DD HH:MM` in UTC+9; empty when it has none."""
    if not created:
        return ""
    return datetime.datetime.fromisoformat(created.replace("Z", "+00:00")).astimezone(datetime.timezone(datetime.timedelta(hours=9))).strftime("%m/%d %H:%M")


def shown(node, superseded=frozenset()):
    """What the pane draws under a task: its open questions' first lines, its latest SHOWN_DECIDED owner decisions that no decision in SUPERSEDED
    replaced, each after the decisions it replaced, marked `struck`, and how many current ones are left out."""
    issue = as_issue(node)
    owned = [decision for decision in typed(node["number"], node) if decision["role"] == "owner"]
    by_url = {decision["url"]: decision for decision in owned}

    def history(decision):
        """DECISION after the decisions it replaced, oldest first."""
        found = [decision]
        while (earlier := by_url.get(found[0]["supersedes"])) and earlier not in found:
            found.insert(0, earlier)
        return found

    current = [decision for decision in owned if decision["url"] not in superseded]
    kept = [decision for latest in current[-SHOWN_DECIDED:] for decision in history(latest)]
    asked = [first_line(question["ask"]) for question in issue_state.open_questions(issue)]
    return {"questions": [text for k, text in enumerate(asked) if text not in asked[:k]],  # an ask posted again is one question
            "decided": [{"decision": decision["decision"], "time": stamp(decision["createdAt"]), "struck": decision["url"] in superseded} for decision in kept],
            "more": max(len(current) - SHOWN_DECIDED, 0)}
