"""Decisions across a root's tree, by the grammar's Decisions section: each task's binding set, the rules `decide` holds a
decision to, and the gaps the manager's heartbeat lists. ISSUES is {number: issue}, each with `body`, `trusted`, `state`,
`stateReason`, `parent` (a number, a {number} node or None) and `comments` (a list, or a {nodes} connection)."""
import datetime
import re

import issue_state
import task_links



def as_issue(node):
    """NODE with its comments as a list, as `issue_state.records` reads them."""
    comments = node.get("comments") or []
    return {**node, "comments": comments["nodes"] if isinstance(comments, dict) else comments}


def parent_of(issue):
    parent = issue.get("parent")
    return parent.get("number") if isinstance(parent, dict) else parent


def quoted(text):
    """Whether TEXT, outside its fenced blocks, quotes someone's words: a `>` line or a span in double quotes."""
    prose = re.sub(r"^(`{3,}).*?^\1", "", text or "", flags=re.M | re.S)
    return bool(re.search(r'^>\s*\S|"[^"\n]{2,}"|“[^”\n]{2,}”', prose, re.M))


def typed(number, issue):
    """The decisions on one issue, oldest first, untrusted comments left out."""
    found = []
    for index, (word, fields, comment) in enumerate(issue_state.records(as_issue(issue))[1:]):
        if word == issue_state.ANSWER and "decision" in fields:
            found.append({"task": number, "index": index, "url": comment["url"], "createdAt": comment.get("createdAt") or "",
                          "decision": fields["decision"], "decider": fields.get("by", ""), "role": issue_state.role(fields.get("by", "")),
                          "door": "one-way" if fields.get("one_way") else "two-way", "supersedes": fields.get("supersedes", ""), "answers": fields.get("answers", "")})
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
    """Whether a decision binds, a worker's one-way decision only once a later manager or owner decision on its task
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


def refusals(number, text, fields, issues):
    """Why TEXT with the decision FIELDS cannot be posted on NUMBER, given its root's tree ISSUES; empty when it can."""
    found = []
    owner = issue_state.role(fields["by"]) == "owner"
    if owner and not quoted(text):
        found.append("`--by owner` quotes no words of the owner's, as a `>` line or in double quotes")
    answered = fields.get("answers")
    if answered and issue_state.place(answered) not in [issue_state.place(question["ask"]["url"]) for question in issue_state.questions(as_issue(issues[int(number)]))]:
        place = next((task for task, issue in issues.items() for comment in as_issue(issue)["comments"] if issue_state.place(comment.get("url") or "") == issue_state.place(answered)), None)
        found.append(f"`--answers` names {answered}, which is no question on #{number}"
                     + (f"; post the decision on #{place}, the question's own task" if place and place != int(number) else ""))
    target = fields.get("supersedes")
    if target:
        root = chain(int(number), issues)[-1]
        every = {decision["url"]: decision for task in tree_of(root, issues) for decision in typed(task, issues[task])}
        if target not in every:
            found.append(f"`--supersedes` names {target}, which is no decision in #{root}'s tree")
        elif every[target]["role"] == "owner" and not owner:
            found.append(f"{target} was decided by the owner, so only a decision `--by owner`, quoting the owner's words, supersedes it")
    return found


def first_line(comment):
    return issue_state.first_line(comment["body"])


def owner_questions(issues):
    """The lines for ISSUES' open questions to the owner, oldest first."""
    asked = sorted(((question["ask"].get("createdAt") or "", number, question["ask"]) for number, issue in issues.items()
                    for question in issue_state.open_questions(issue) if question["fields"].get("asks") == "owner"),
                   key=lambda item: item[0])
    return [f"question #{number}: {first_line(ask)} ({ask['url']}) waits on the owner; ask the owner, then record the answer by `decide` "
            "with `--by owner` and `--answers` its url" for _, number, ask in asked]


def superseded_twice(every):
    """The lines for the decisions in EVERY that two later ones supersede."""
    lines = []
    for url in sorted({decision["supersedes"] for decision in every if decision["supersedes"]}):
        later = [decision for decision in every if decision["supersedes"] == url]
        if len(later) > 1:
            lines.append(f"superseded twice #{later[0]['task']}: {url} is superseded by {' and '.join(decision['url'] for decision in later)}; "
                         f"keep one by a decision that supersedes the other")
    return lines


def one_way_waiting(every):
    """The lines for a worker's one-way decision in EVERY that nothing supersedes and no manager or owner decision follows."""
    superseded = replaced(every)
    return [f"one-way #{decision['task']}: {decision['decider']}'s {decision['url']} binds only once you repeat or supersede it by `decide`"
            for decision in every if decision["url"] not in superseded and not binds(decision, every)]


def gaps(found):
    """The heartbeat's decision lines for the open issues FOUND: open questions to the owner, a decision two later ones supersede, and a worker's
    one-way decision that nothing binds."""
    issues = {issue["number"]: as_issue(issue) for issue in found}
    every = [decision for number, issue in issues.items() for decision in typed(number, issue)]
    return [*owner_questions(issues), *superseded_twice(every), *one_way_waiting(every)]


def task_number(argument):
    """The task number a `7`, a `#7` or an issue's url names, else None."""
    found = re.fullmatch(r"(?:#|\S+://\S*/)?(\d+)", argument)
    return int(found.group(1)) if found else None


def lines(number, issues, questions=True):
    """What binds task NUMBER now, as lines a reader starts from: the decisions on it and its ancestors, then, when QUESTIONS, the open questions on them."""
    bound = binding(number, issues)
    found = [f"binding decisions: {len(bound)}"]
    for decision in bound:
        links = "".join(f"; {key} {decision[key]}" for key in ("supersedes", "answers") if decision[key])
        found.append(f"- #{decision['task']} {decision['decider']}{', one-way' * (decision['door'] == 'one-way')}: {decision['decision']} ({decision['url']}){links}")
    if questions:
        asked = [(task, question) for task in chain(number, issues) for question in issue_state.open_questions(as_issue(issues[task]))]
        found.append(f"open questions: {len(asked)}")
        found += [f"- #{task} to the {question['fields'].get('asks') or 'manager'}: {first_line(question['ask'])} ({question['ask']['url']})" for task, question in asked]
    return found


def superseded_in(nodes):
    """The urls of the decisions among NODES that a decision passed by its door supersedes, read once for a whole draw."""
    return replaced([decision for node in nodes for decision in typed(node["number"], node)])


def pane_time(created):
    """CREATED, a board timestamp such as `2026-11-04T04:00:00Z`, as `MM/DD HH:MM` in UTC+9; empty when it has none or cannot be read."""
    try:
        when = datetime.datetime.fromisoformat((created or "").replace("Z", "+00:00"))
    except ValueError:
        return ""
    return when.replace(tzinfo=when.tzinfo or datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=9))).strftime("%m/%d %H:%M")


def shown(node, superseded=frozenset()):
    """What the pane draws under a task: its open questions' first lines, which of them the team answers, per question the answers one to the owner offers, and its decisions that no decision in SUPERSEDED replaced, newest first.
    A decision is {decision, time, mark}: `mark` is `◆` for the owner's and `◇` for a manager's or a worker's."""
    issue = as_issue(node)
    live = sorted((decision for decision in typed(node["number"], node) if decision["url"] not in superseded),
                  key=lambda decision: (decision["createdAt"], decision["index"]), reverse=True)
    asked = {first_line(question["ask"]): question["fields"] for question in issue_state.open_questions(issue)}  # an ask posted again is one question
    return {"questions": list(asked), "team_questions": [k for k, fields in enumerate(asked.values()) if fields.get("asks") != "owner"],
            "options": [fields.get("options", []) if fields.get("asks") == "owner" else [] for fields in asked.values()],
            "decided": [{"decision": decision["decision"], "time": pane_time(decision["createdAt"]), "mark": "◆" if decision["role"] == "owner" else "◇"} for decision in live]}
