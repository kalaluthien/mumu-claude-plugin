#!/usr/bin/env python3
"""Check typed decisions on a board, writing only through use-board.py and reading through list-decisions.py, and print `ok <case>` or
`fail <case>: <what it saw>` per case; exit 1 on any fail. files and git run every case; github-nodes the pane's, from GitHub-shaped
nodes written here by hand. The files and git boards trust every comment, so pane-untrusted there marks one of the board's own
decision comments untrusted, as the GitHub adapter marks an outsider's, before the rows are laid out.
- record-fields, record-event, record-supersedes, record-unknown-supersedes: `decide` writes a decision block the index reads back
- authority-refuses, authority-unquoted, authority-comment, authority-owner, authority-manager: who may supersede an owner decision
- binding-ancestors, binding-stopped-root, binding-answered, binding-event-keeps-question, binding-one-way-waits,
  binding-one-way-supersedes: a task's binding set and open questions
- heartbeat-open-question, heartbeat-twice-superseded, heartbeat-one-way, heartbeat-one-way-superseded, heartbeat-answer-line,
  heartbeat-unblocked-decided,
  heartbeat-legacy-quiet: the manager's heartbeat lines
- pane-question, pane-latest-three, pane-cut, pane-untrusted: list-issue-board.py's `?` and `◆` lines; pane-linear, on github-nodes
  only: one draw parses each task's comments a bounded number of times, however many tasks there are

usage: replay-task-decisions.py --board <files|git|github-nodes>"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
USE = HERE.parent / "scripts" / "use-board.py"
INDEX = HERE.parent / "scripts" / "list-decisions.py"
LIST = ROOT / "hooks" / "list-issue-board.py"
CHECK = "1. [check] **probe passes**: `echo ok` prints `ok`; on base nothing.\n"
LONG = "probe only the sandbox repository, never the team's own board, and keep every raw response as a fixture beside the probe"
failures = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[:400]}", flush=True)
    if not ok:
        failures.append(name)


def body(parts=()):
    items = [CHECK] + [f"{i}. [task] #{n} Probe part {n}\n" for i, n in enumerate(parts, 2)]
    return f"## Goal\n\nProbe typed decisions.\n\n## Definition of done\n\n{''.join(items)}"


def use(*argv):
    return subprocess.run([sys.executable, str(USE), *map(str, argv)], capture_output=True, text=True)


def write(text):
    path = work / f"text-{time.monotonic_ns()}.md"
    path.write_text(text)
    return path


def file(title, parts=()):
    done = use("file", title, write(body(parts)))
    if done.returncode:
        raise SystemExit(f"replay-task-decisions: cannot file {title}: {done.stderr}")
    return int(done.stdout.strip().rsplit("/", 1)[1])


def decide(number, decision, by="probe-manager", door="two-way", supersedes="", answers="", depends="", quote=None, verb="decide"):
    """Posts a decision by `use-board.py <VERB>`; its url, or the finished call when it exited non-zero."""
    fields = {"decision": decision, "decided by": by, "door": door, "supersedes": supersedes, "answers": answers, "depends on": depends}
    said = f"> {quote}\n\n" if quote else ""
    block = "".join(f"{key}: {value}\n" for key, value in fields.items() if value)
    done = use(verb, number, write(f"DECIDED: {decision}\n\n{said}```decision\n{block}```\n"))
    return done.stdout.strip() if done.returncode == 0 else done


def post(number, text, verb="comment"):
    done = use(verb, number, write(text))
    return done.stdout.strip()


def ask(number, question, owner=False):
    return post(number, f"BLOCKED: {question}\n" + ("\n```teamwork\nasks: owner\n```\n" if owner else ""))


def index(number):
    return subprocess.run([sys.executable, str(INDEX), str(number)], capture_output=True, text=True).stdout


def bound(number):
    """The urls in NUMBER's binding set, as list-decisions.py prints them."""
    text = index(number).split("open questions:")[0]
    return re.findall(r"\((\S+)\)", text)


def asked(number):
    return re.findall(r"\((\S+)\)$", index(number).split("open questions:")[1], re.M)


def comments(number):
    return len(board.fresh(number)["comments"])


def refused(name, number, call, *said):
    """CALL, a decide on NUMBER, exits 1 naming each of SAID, and posts nothing."""
    before = comments(number)
    done = call()
    text = done.stderr if isinstance(done, subprocess.CompletedProcess) else f"posted {done}"
    step(name, isinstance(done, subprocess.CompletedProcess) and done.returncode == 1 and all(word in text for word in said) and comments(number) == before, text)


def record_cases():
    root, other = file("Probe a decided root"), file("Probe another root")
    question = ask(root, "which board")
    first = decide(root, "use the files board")
    full = decide(root, "use the git board", door="one-way", supersedes=first, answers=question, depends=f"#{other}")
    line = next((line for line in index(root).splitlines() if full in line), "")
    step("record-fields", all(part in line for part in ("probe-manager, one-way: use the git board", f"supersedes {first}", f"answers {question}", f"waits on #{other}")), index(root))
    event = post(root, "DECIDED: probe-worker holds this\n\n```teamwork\nholders: probe-worker\n```\n", "decide")
    report = post(root, "REPORTED: probe findings\n")
    step("record-event", event not in bound(root) and report not in bound(root) and bound(root) == [full], index(root))
    part = file("Probe a part")
    parent = file("Probe a parent", parts=[part])
    ruled = decide(parent, "keep the parent's rule")
    replaced = decide(part, "the part's rule replaces it", supersedes=ruled)
    step("record-supersedes", isinstance(replaced, str) and ruled not in bound(parent) and ruled not in bound(part) and replaced in bound(part), [index(parent), index(part)])
    refused("record-unknown-supersedes", other, lambda: decide(other, "replace another tree's rule", supersedes=ruled), ruled, "no decision")


def authority_cases():
    task = file("Probe an owner's task")
    owner = decide(task, "no external service", by="owner", door="one-way", quote="no external service")
    refused("authority-refuses", task, lambda: decide(task, "an external service is fine", supersedes=owner), owner, "owner")
    refused("authority-unquoted", task, lambda: decide(task, "an external service is fine", by="owner", supersedes=owner), "quotes no words")
    refused("authority-comment", task, lambda: decide(task, "an external service is fine", supersedes=owner, verb="comment"), "decide")
    again = decide(task, "only the sandbox service", by="owner", door="one-way", supersedes=owner, quote="the sandbox is fine")
    step("authority-owner", isinstance(again, str) and bound(task) == [again], index(task))
    managed = file("Probe a manager's task")
    first = decide(managed, "build it in Python")
    second = decide(managed, "build it in TypeScript", supersedes=first)
    step("authority-manager", isinstance(second, str) and bound(managed) == [second], index(managed))


def binding_cases():
    left, right = file("Probe a left part"), file("Probe a right part")
    middle = file("Probe a middle task", parts=[left, right])
    root = file("Probe a binding root", parts=[middle])
    on_root, on_middle, on_left, on_right = (decide(n, f"rule on #{n}") for n in (root, middle, left, right))
    seen = bound(left)
    step("binding-ancestors", {on_root, on_middle, on_left} <= set(seen) and on_right not in seen, index(left))
    use("resolve", root, write("REPORTED: probe stopped\n"), "--not-planned")
    step("binding-stopped-root", bound(left) == [] and bound(root) == [], index(left))
    task = file("Probe a question")
    question = ask(task, "which width counts")
    post(task, "DECIDED: probe-worker holds this\n\n```teamwork\nholders: probe-worker\n```\n", "decide")
    step("binding-event-keeps-question", asked(task) == [question], index(task))
    other = ask(task, "which height counts")
    decide(task, "any height counts", answers=other)
    # a decision naming another question leaves this one open, though a legacy question closes on any later decision with no `answers:`
    named_other = asked(task) == [question]
    decide(task, "24 to 80 columns count", answers=question)
    step("binding-answered", named_other and asked(task) == [], index(task))
    gated = file("Probe a one-way door")
    worker = decide(gated, "drop the cache", by="probe-worker", door="one-way")
    waited = worker not in bound(gated)
    decide(gated, "drop the cache")
    step("binding-one-way-waits", waited and worker in bound(gated), index(gated))
    held = file("Probe a door over a manager's rule")
    rule = decide(held, "keep the cache")
    pending = decide(held, "drop the cache", by="probe-worker", door="one-way", supersedes=rule)
    kept = bound(held) == [rule]
    followed = decide(held, "drop the cache", supersedes=pending)
    step("binding-one-way-supersedes", kept and bound(held) == [followed], index(held))


def heartbeat(numbers, since=None):
    """The manager's heartbeat decision lines on NUMBERS, with decisions typed since SINCE when given."""
    import issue_state
    import team_gaps
    kept = issue_state.TYPED_SINCE
    issue_state.TYPED_SINCE = since or kept
    team_gaps.tabs, team_gaps.crowding, team_gaps.members = (lambda workspace: []), (lambda me, listed: []), (lambda me, listed: [])
    try:
        found = [issue for issue in board.issues("open") if issue["number"] in numbers]
        data = {"found": found, "everything": [], "prs": [], "outside": [], "feed": [], "links": []}
        lines = team_gaps.manager_actions({"name": "probe-manager", "workspace_id": ""}, [], data)
    finally:
        issue_state.TYPED_SINCE = kept
    return [line for line in lines if line.startswith(("question ", "answer ", "superseded twice ", "one-way ", "untyped "))]


def heartbeat_cases():
    later, earlier = file("Probe a later question"), file("Probe an earlier question")
    ask(earlier, "may the sync run", owner=True)
    time.sleep(1.1)  # the boards stamp to the second
    ask(later, "may the pane change", owner=True)
    lines = heartbeat({later, earlier})
    order = [int(found) for found in re.findall(r"^question #(\d+)", "\n".join(lines), re.M)]
    step("heartbeat-open-question", order == [earlier, later], lines)
    task = file("Probe a twice superseded rule")
    rule = decide(task, "cache for an hour")
    decide(task, "cache for a day", supersedes=rule)
    decide(task, "cache for a week", supersedes=rule)
    step("heartbeat-twice-superseded", any(line.startswith(f"superseded twice #{task}: {rule}") for line in heartbeat({task})), heartbeat({task}))
    gated = file("Probe an unfollowed door")
    worker = decide(gated, "drop the index", by="probe-worker", door="one-way")
    step("heartbeat-one-way", any(line.startswith(f"one-way #{gated}: probe-worker's {worker}") for line in heartbeat({gated})), heartbeat({gated}))
    redone = file("Probe a door its worker replaced")
    dropped = decide(redone, "drop the cache", by="probe-worker", door="one-way")
    decide(redone, "keep the cache", by="probe-worker", supersedes=dropped)
    asker = file("Probe a worker's question")
    asked_url = ask(asker, "which cache")
    answer_line = next((line for line in heartbeat({asker}) if line.startswith(f"answer #{asker}:")), "")
    step("heartbeat-answer-line", "`decide`" in answer_line and f"answers: {asked_url}" in answer_line, heartbeat({asker}))
    step("heartbeat-one-way-superseded", not any(line.startswith(f"one-way #{redone}:") for line in heartbeat({redone})), heartbeat({redone}))
    plain = file("Probe a plain decision")
    said = post(plain, "DECIDED: probe a decision with no block\n", "decide")
    post(plain, "DECIDED: probe-worker holds this\n\n```teamwork\nholders: probe-worker\n```\n", "decide")
    typed, legacy = heartbeat({plain}, since="0000"), heartbeat({plain}, since="9999")
    step("heartbeat-unblocked-decided", [line.split(" is ")[0] for line in typed if line.startswith("untyped ")] == [f"untyped #{plain}: {said}"], typed)
    step("heartbeat-legacy-quiet", not any(line.startswith("untyped ") for line in legacy), legacy)


def block(lines, number, strip=True):
    """NUMBER's row block in list-issue-board.py's LINES: from its row to the next row at any depth, guides stripped when STRIP."""
    start = next((i for i, line in enumerate(lines) if re.match(rf"^[\s│├└]*#{number} ", line)), len(lines))
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^[\s│├└]*#\d+ ", lines[i])), len(lines))
    return [line.lstrip(" │") if strip else line for line in lines[start:end]]


def pane_cases(listed, narrow, untrusted_lines, asker, decider, cutter, untrusted):
    """The pane's lines: LISTED at the pane's width, NARROW at 24 columns, UNTRUSTED_LINES with UNTRUSTED's decision marked untrusted."""
    step("pane-question", "? may the sync run" in block(listed, asker), block(listed, asker))
    marks = [line for line in block(listed, decider) if line.startswith("◆ ")]
    step("pane-latest-three", marks[:3] == ["◆ rule two", "◆ rule three", "◆ rule four"] and marks[3:] == ["◆ 1 more decided"], block(listed, decider))
    cut = block(narrow, cutter, strip=False)
    start = next((i for i, line in enumerate(cut) if "◆ " in line), len(cut))
    shown = cut[start:start + 3]
    mark = cut[start].find("◆") if shown else 0
    # a decision's later lines sit 2 cells right of its mark, so they read as its own
    step("pane-cut", len(shown) == 3 and shown[2].endswith("…") and all(line[mark:mark + 2] == "  " and line[mark + 2] != " " for line in shown[1:])
         and "beside the probe" not in "\n".join(cut), cut)
    step("pane-untrusted", not any(line.startswith("◆ ") for line in block(untrusted_lines, untrusted)), block(untrusted_lines, untrusted))


def board_pane():
    asker, decider, cutter, untrusted = file("Probe an asking task"), file("Probe a deciding task"), file("Probe a long rule"), file("Probe an outsider")
    ask(asker, "may the sync run", owner=True)
    for word in ("one", "two", "three", "four"):
        decide(decider, f"rule {word}", by="owner", door="one-way", quote=f"rule {word}")
    decide(cutter, LONG, by="owner", door="one-way", quote="only the sandbox")
    outsider = decide(untrusted, "probe the team's board", by="owner", door="one-way", quote="probe ours")
    listed = subprocess.run([sys.executable, str(LIST), "probe"], capture_output=True, text=True).stdout.splitlines()
    narrow = subprocess.run([sys.executable, str(LIST), "probe", "--width", "24"], capture_output=True, text=True).stdout.splitlines()
    import issue_board
    nodes = board.tree(None)
    for node in nodes:
        for comment in node["comments"]["nodes"]:
            comment["trusted"] = comment["url"] != outsider
    untrusted_lines = list(issue_board.lines(issue_board.board(nodes), issue_board.PANE_WIDTH))
    pane_cases(listed, narrow, untrusted_lines, asker, decider, cutter, untrusted)


def node(number, comments=()):
    return {"number": number, "title": f"Probe {number}", "url": f"https://github.com/o/r/issues/{number}", "body": body(), "authorAssociation": "OWNER",
            "state": "OPEN", "stateReason": None, "parent": None, "labels": {"nodes": []}, "subIssues": {"nodes": []}, "subIssuesSummary": {"total": 0},
            "blockedBy": {"nodes": []}, "comments": {"nodes": list(comments)}}


def comment(number, k, text, association="OWNER"):
    return {"body": text, "url": f"https://github.com/o/r/issues/{number}#issuecomment-{number}0{k}", "authorAssociation": association, "createdAt": f"2026-11-06T0{k}:00:00Z"}


def owner_decision(number, k, decision, association="OWNER"):
    return comment(number, k, f"DECIDED: {decision}\n\n> {decision}\n\n```decision\ndecision: {decision}\ndecided by: owner\ndoor: one-way\n```\n", association)


def nodes_pane():
    nodes = [node(1, [comment(1, 1, "BLOCKED: may the sync run\n\n```teamwork\nasks: owner\n```\n")]),
             node(2, [owner_decision(2, k, f"rule {word}") for k, word in enumerate(("one", "two", "three", "four"), 1)]),
             node(3, [owner_decision(3, 1, LONG)]), node(4, [owner_decision(4, 1, "probe the team's board", association="NONE")])]
    path = work / "nodes.json"
    path.write_text(json.dumps(nodes))
    listed = subprocess.run([sys.executable, str(LIST), "--nodes", str(path)], capture_output=True, text=True).stdout.splitlines()
    narrow = subprocess.run([sys.executable, str(LIST), "--nodes", str(path), "--width", "24"], capture_output=True, text=True).stdout.splitlines()
    pane_cases(listed, narrow, listed, 1, 2, 3, 4)
    import issue_board
    import issue_state
    original, parses = issue_state.records, [0]

    def counted(issue):
        parses[0] += 1
        return original(issue)

    def draw(count):
        parses[0] = 0
        issue_board.board(board.tree(None, [node(n, [comment(n, k % 10, f"DECIDED: rule {k}") for k in range(20)]) for n in range(1, count + 1)]))
        return parses[0]

    issue_state.records = counted
    try:
        small, large = draw(40), draw(80)
    finally:
        issue_state.records = original
    step("pane-linear", large <= 2.5 * small, f"{small} parses for 40 tasks, {large} for 80")


def main(args):
    global work, board
    if len(args) != 2 or args[0] != "--board" or args[1] not in ("files", "git", "github-nodes"):
        print(__doc__, file=sys.stderr)
        return 2
    kind = args[1]
    work = pathlib.Path(tempfile.mkdtemp(prefix="task-decisions-"))
    os.environ.update({"TEAMWORK_BOARD": "github" if kind == "github-nodes" else kind, "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "config")})
    if kind == "files":
        os.environ["TEAMWORK_BOARD_DIR"] = str(work / "board")
    elif kind == "git":
        subprocess.run(["git", "init", "-q", str(work / "repo")], check=True)
        os.chdir(work / "repo")
    sys.path.insert(0, str(ROOT / "lib"))
    import board  # noqa: E402  read here, since it reads the board set above when it loads

    if kind == "github-nodes":
        nodes_pane()
        return 1 if failures else 0
    record_cases()
    authority_cases()
    binding_cases()
    heartbeat_cases()
    board_pane()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
