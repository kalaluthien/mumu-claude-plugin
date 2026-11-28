"""Decisions across a root's tree, by the grammar's Decisions section: each task's binding set, the rules `decide` holds a
decision to, and the gaps the manager's heartbeat lists. TASKS is {number: task}, each with `body`, `state`,
`parent` (a number, a {number} node or None) and `comments` (a list, or a {nodes} connection)."""
import datetime

import board_refs
import board_text
import task_state
import task_links


def as_task(node):
    """NODE with its comments as a list, as `task_state.records` reads them."""
    comments = node.get("comments") or []
    return {**node, "comments": comments["nodes"] if isinstance(comments, dict) else comments}


def parent_of(task):
    parent = task.get("parent")
    return parent.get("number") if isinstance(parent, dict) else parent


def typed(number, task):
    """The decisions on one task, oldest first."""
    found = []
    for index, (kind, fields, comment) in enumerate(task_state.records(as_task(task))):
        if kind == "decision":
            found.append({"task": number, "index": index, "url": comment["url"], "ref": comment["ref"], "created": comment["created"],
                          "decision": fields["decision"], "decider": fields.get("by", ""), "role": task_state.role(fields.get("by", "")),
                          "supersedes": fields.get("supersedes", ""), "answers": fields.get("answers", [])})
    return found


def chain(number, tasks):
    """NUMBER, then its ancestors as far as TASKS holds them, nearest first."""
    found = [number]
    while (parent := parent_of(tasks[found[-1]])) in tasks and parent not in found:
        found.append(parent)
    return found


def tree_of(root, tasks):
    return [number for number in tasks if chain(number, tasks)[-1] == root]


def replaced(every):
    """The refs, as `board_refs.stored` reads them, of the decisions in EVERY that a decision supersedes."""
    return {board_refs.stored(decision["supersedes"]) for decision in every if decision["supersedes"]}


def binding(number, tasks):
    """NUMBER's binding set: the decisions on it and its ancestors that no decision in the root's tree supersedes, oldest first;
    none once the root was stopped."""
    lineage = chain(number, tasks)
    root = tasks[lineage[-1]]
    if root.get("state") == "stopped":
        return []
    every = [decision for task in tree_of(lineage[-1], tasks) for decision in typed(task, tasks[task])]
    superseded = replaced(every)
    return sorted((decision for decision in every if decision["task"] in lineage and board_refs.stored(decision["ref"]) not in superseded),
                  key=lambda decision: (decision["created"], decision["task"], decision["index"]))


def read(number, fresh):
    """{number: task} of NUMBER's root's tree, by FRESH, the board's `fresh`: up by each parent, then down by each body's parts."""
    tasks, number, root = {}, int(number), None
    while number is not None and number not in tasks:
        found = fresh(number)
        if found is None:
            raise LookupError(f"cannot read #{number}")
        tasks[number], root, number = found, number, parent_of(found)
    pending, seen = [root], {root}
    while pending:
        for part in task_links.parts(tasks[pending.pop()]["body"]):
            if part not in tasks and (found := fresh(part)) is not None:
                tasks[part] = found
            if part in tasks and part not in seen:
                seen.add(part)
                pending.append(part)
    return tasks


def refusals(number, fields, tasks):
    """Why a decision of FIELDS cannot be posted on NUMBER, given its root's tree TASKS; empty when it can."""
    found = []
    owner = task_state.role(fields["by"]) == "owner"
    asked = {link: question["fields"].get("asks") for question in task_state.questions(as_task(tasks[int(number)])) for link in question["links"]}
    for answered in fields.get("answers", []):
        if asked.get(board_refs.stored(answered)) == "owner" and not owner:
            found.append(f"{answered} asks the owner, so only a decision `--by owner`, quoting the owner's words by `--owner-said`, answers it")
        if board_refs.stored(answered) not in asked:
            place = next((home for home, task in tasks.items() for comment in as_task(task)["comments"] if board_refs.stored(comment["ref"]) == board_refs.stored(answered)), None)
            found.append(f"`--answers` names {answered}, which is no question on #{number}"
                         + (f"; post the decision on #{place}, the question's own task" if place and place != int(number) else ""))
    target = fields.get("supersedes")
    if target:
        root = chain(int(number), tasks)[-1]
        every = {board_refs.stored(decision["ref"]): decision for task in tree_of(root, tasks) for decision in typed(task, tasks[task])}
        if board_refs.stored(target) not in every:
            found.append(f"`--supersedes` names {target}, which is no decision in #{root}'s tree")
        elif every[board_refs.stored(target)]["role"] == "owner" and not owner:
            found.append(f"{target} was decided by the owner, so only a decision `--by owner`, quoting the owner's words by `--owner-said`, supersedes it")
    return found


def owner_questions(tasks):
    """The lines for TASKS' open questions to the owner, oldest first."""
    asked = sorted(((question["ask"]["created"], number, question["ask"]) for number, task in tasks.items()
                    for question in task_state.open_questions(task) if question["fields"].get("asks") == "owner"),
                   key=lambda item: item[0])
    return [board_text.line(f"question #{number} ({ask['url']}) waits on the owner: ask the owner, then record the answer by `decide` "
                            "with `--by owner --owner-said <file>` and `--answers` its url;", question=task_state.first_line(ask)) for _, number, ask in asked]


def superseded_twice(every):
    """The lines for the decisions in EVERY that two later ones supersede."""
    lines, urls = [], {board_refs.stored(decision["ref"]): decision["url"] for decision in every}
    for target in sorted({board_refs.stored(decision["supersedes"]) for decision in every if decision["supersedes"]}):
        later = [decision for decision in every if decision["supersedes"] and board_refs.stored(decision["supersedes"]) == target]
        if len(later) > 1:
            lines.append(f"superseded twice #{later[0]['task']}: {urls.get(target, later[0]['supersedes'])} is superseded by {' and '.join(decision['url'] for decision in later)}; "
                         f"keep one by a decision that supersedes the other")
    return lines


def gaps(found):
    """The heartbeat's decision lines for the open tasks FOUND: open questions to the owner and a decision two later ones supersede."""
    tasks = {task["number"]: as_task(task) for task in found}
    every = [decision for number, task in tasks.items() for decision in typed(number, task)]
    return [*owner_questions(tasks), *superseded_twice(every)]


def lines(number, tasks, questions=True):
    """What binds task NUMBER now, as lines a reader starts from: the decisions on it and its ancestors, then, when QUESTIONS, the open questions on them."""
    bound = binding(number, tasks)
    found = [f"binding decisions: {len(bound)}"]
    for decision in bound:
        links = "".join(f"; {key} {' '.join(decision[key]) if isinstance(decision[key], list) else decision[key]}" for key in ("supersedes", "answers") if decision[key])
        found.append(f"- #{decision['task']} {decision['decider']}: {decision['decision']} ({decision['url']}){links}")
    if questions:
        asked = [(task, question) for task in chain(number, tasks) for question in task_state.open_questions(as_task(tasks[task]))]
        found.append(f"open questions: {len(asked)}")
        found += [f"- #{task} to the {question['fields'].get('asks') or 'manager'}: {task_state.first_line(question['ask'])} ({question['ask']['url']})" for task, question in asked]
    return found


def superseded_in(nodes):
    """The refs of the decisions among NODES that a decision supersedes, read once for a whole draw."""
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
    task = as_task(node)
    live = sorted((decision for decision in typed(node["number"], node) if board_refs.stored(decision["ref"]) not in superseded),
                  key=lambda decision: (decision["created"], decision["index"]), reverse=True)
    asked = [question for question in task_state.open_questions(task)]  # one entry per question, whatever its first line
    return {"questions": [task_state.first_line(question["ask"]) for question in asked],
            "team_questions": [k for k, question in enumerate(asked) if question["fields"].get("asks") != "owner"],
            "options": [question["fields"].get("options", []) if question["fields"].get("asks") == "owner" else [] for question in asked],
            "decided": [{"decision": decision["decision"], "time": pane_time(decision["created"]), "mark": "◆" if decision["role"] == "owner" else "◇"} for decision in live]}
