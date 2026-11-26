#!/usr/bin/env python3
"""Check typed decisions on a board, writing only through use-board.py and reading through its `read`, and print `ok <case>` or
`fail <case>: <what it saw>` per case, then `PASS` or `FAIL`; exit 1 on any fail. git runs every case, in a scratch repository whose
manager and worker live in a fake herdr, its heartbeat lines printed by print-team-gaps.py; nodes the pane's, from task nodes written here by hand.
A record written past use-board.py's checks, and the pane's rows where a script prints none, are made by the plugin's lib in a process of the
scratch repository's own. The git board trusts every comment, so pane-untrusted there marks one of the board's own decision comments untrusted,
as an outsider's is marked, before the rows are laid out.
- record-fields, record-event, record-supersedes, record-unknown-supersedes, record-answers-elsewhere, record-answers-own: `decide`
  stores a decision `read` prints back, its `--answers` an open question on its own task
- authority-refuses, authority-unquoted, authority-comment, authority-owner, authority-manager: who may supersede an owner decision;
  authority-owner-question, authority-owner-answers: only a decision `--by owner` answers a question to the owner, one written or stored by another leaving it open
- binding-ancestors, binding-stopped-root, binding-answered, binding-event-keeps-question, binding-one-way-waits,
  binding-one-way-supersedes, binding-successor: a task's binding set and open questions
- heartbeat-open-question, heartbeat-twice-superseded, heartbeat-one-way, heartbeat-one-way-superseded, heartbeat-answer-line:
  the manager's heartbeat lines
- event-answers: a `DECIDED:` holding no decision whose `answers` lists questions, one to the owner among them, settles them all and binds nothing, and the schema takes that list but refuses one holding a value that is no comment url
- route-own-depends, route-parts-blocked, route-after-close: no `route` line for a task that waits on an open task,
  or whose open parts all do, until that task closes
- pane-question, pane-every-decision, pane-cut, pane-untrusted, pane-question-next-line: list-task-board.py's `?` and `◆` lines; pane-linear, on nodes
  only: one draw parses each task's comments a bounded number of times, however many tasks there are
- row-no-deferral, row-finished-parent, row-one-color, on nodes: a `deferred:` line sets no wait; a parent
  whose parts are all done shows its next step in full among its always-shown lines; and every row's number takes the color of its own state, drawn by one Button

usage: replay-task-decisions.py [--board <git|nodes>]   (no argument: both in turn)"""
import json
import pathlib
import re
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LIB = ROOT / "lib"
sys.path.insert(0, str(LIB))
import replay_probe  # noqa: E402

USE = HERE.parent / "scripts" / "use-board.py"
LIST = ROOT / "hooks" / "list-task-board.py"
GAPS = ROOT / "monitors" / "print-team-gaps.py"
LONG = "probe only the sandbox repository and keep every raw response it sends as a fixture beside the probe"
HEARTBEAT = re.compile(r"^(?:question|answer|superseded twice|one-way|route) #(\d+)")
cases = replay_probe.Cases()


def evaluate(code):
    """The JSON value the last line of CODE prints, run with the plugin's lib in the sandbox's repository and environment."""
    return sandbox.evaluate(f"import json\n{code}")


def body(parts=()):
    items = [replay_probe.CHECK] + [f"{i}. [task] #{n} Probe part {n}\n" for i, n in enumerate(parts, 2)]
    return f"## Goal\n\nProbe typed decisions.\n\nPath: caller: the probe run; meets: the owner\n\n## Definition of done\n\n{''.join(items)}"


def use(*argv, **options):
    return sandbox.python(USE, *map(str, argv), **options)


def write(text):
    return replay_probe.write_text(sandbox.work, "text.md", text)


def file(title, parts=(), depends=()):
    done = use("file", "--title", title, "--body", write(body(parts)), "--depends", " ".join(map(str, depends)))
    if done.returncode:
        raise SystemExit(f"replay-task-decisions: cannot file {title}: {done.stderr}")
    return int(done.stdout.strip().rsplit("/", 1)[1])


def decide(number, decision, by="probe-manager", door="two-way", supersedes="", answers="", quote=None):
    """Posts a decision by `use-board.py decide`, run as BY or, for `owner`, as a manager in whose session the owner typed QUOTE; its url, or the finished call when it exited non-zero."""
    session, said = sandbox.decider(by, quote or "")
    options = [*(said if quote or by != "owner" else said[:2]), *(["--one-way"] if door == "one-way" else []), *(["--supersedes", supersedes] if supersedes else []), *(["--answers", answers] if answers else [])]
    done = use("decide", number, "--decision", decision, *options, **session)
    return done.stdout.strip() if done.returncode == 0 else done


def post(number, option, line, *options):
    """Posts a comment whose keyword line is OPTION's, `--blocked` or `--reported`, with LINE."""
    return use("comment", number, option, line, *options).stdout.strip()


def ask(number, question, owner=False):
    return post(number, "--blocked", question, *(["--asks", "owner", "--option", "yes", "--option", "no"] if owner else []))


def stored(number, record):
    """The url of RECORD, a comment's `{"text", ...fields}`, written straight to the board as NUMBER's next comment, past every check `use-board.py` makes."""
    return evaluate(f"""import board_git, board_records
store = board_git.STORE

def change():
    position = len(board_records.comment_paths(store, {number})) + 1
    store.stage(f"{{board_records.home(store, {number})}}/comments/{{position:04d}}.json", {json.dumps(record)!r})
    return f"{{store.url(board_records.home(store, {number}))}}#comment-{{position}}"
print(json.dumps(store.write(change)))""")


def index(number):
    """What `read` prints of NUMBER's binding decisions and open questions."""
    return re.search(r"^binding decisions: .*?(?=^\n--- |\Z)", use("read", number).stdout, re.M | re.S).group(0)


def bound(number):
    """The urls in NUMBER's binding set, as `read` prints them."""
    return re.findall(r"^- .*? \((\S+)\)(?:; |$)", index(number).split("open questions:")[0], re.M)


def asked(number):
    return re.findall(r"\((\S+)\)$", index(number).split("open questions:")[1], re.M)


def comments(number):
    return evaluate(f"import board\nprint(len(board.fresh({number})['comments']))")


def refused(name, number, call, *said):
    """CALL, a decide on NUMBER, exits 2 naming each of SAID, and posts nothing."""
    before = comments(number)
    done = call()
    text = done.stderr if isinstance(done, subprocess.CompletedProcess) else f"posted {done}"
    cases.step(name, isinstance(done, subprocess.CompletedProcess) and done.returncode == 2 and all(word in text for word in said) and comments(number) == before, text)


def record_cases():
    root, other = file("Probe a decided root"), file("Probe another root")
    question = ask(root, "which board")
    first = decide(root, "use the git board")
    full = decide(root, "use the git board", door="one-way", supersedes=first, answers=question)
    line = next((line for line in index(root).splitlines() if f"({full})" in line), "")
    cases.step("record-fields", all(part in line for part in (f"#{root} probe-manager, one-way: use the git board", f"supersedes {first}", f"answers {question}")), index(root))
    event = use("hold", root, "--holders", "probe-worker").stdout.strip()
    report = post(root, "--reported", "probe findings")
    cases.step("record-event", event not in bound(root) and report not in bound(root) and bound(root) == [full], index(root))
    part = file("Probe a part")
    parent = file("Probe a parent", parts=[part])
    ruled = decide(parent, "keep the parent's rule")
    replaced = decide(part, "the part's rule replaces it", supersedes=ruled)
    cases.step("record-supersedes", isinstance(replaced, str) and ruled not in bound(parent) and ruled not in bound(part) and replaced in bound(part), [index(parent), index(part)])
    refused("record-unknown-supersedes", other, lambda: decide(other, "replace another tree's rule", supersedes=ruled), ruled, "no decision")
    child = file("Probe an asked part")
    asking = file("Probe an asking parent", parts=[child])
    asked_url = ask(asking, "which cache")
    refused("record-answers-elsewhere", child, lambda: decide(child, "keep the cache", answers=asked_url), asked_url, f"#{asking}")
    answered = decide(asking, "keep the cache", answers=asked_url)
    cases.step("record-answers-own", isinstance(answered, str) and asked(asking) == [], index(asking))


def authority_cases():
    task = file("Probe an owner's task")
    owner = decide(task, "no external service", by="owner", door="one-way", quote="no external service")
    refused("authority-refuses", task, lambda: decide(task, "an external service is fine", supersedes=owner), owner, "owner")
    refused("authority-unquoted", task, lambda: decide(task, "an external service is fine", by="owner", supersedes=owner), "--owner-said <file>")
    refused("authority-comment", task, lambda: use("comment", task, "--reported", "an external service is fine", "--text", write("DECIDED: an external service is fine\n")), "--decision")
    again = decide(task, "only the sandbox service", by="owner", door="one-way", supersedes=owner, quote="the sandbox is fine")
    cases.step("authority-owner", isinstance(again, str) and bound(task) == [again], index(task))
    managed = file("Probe a manager's task")
    first = decide(managed, "build it in Python")
    second = decide(managed, "build it in TypeScript", supersedes=first)
    cases.step("authority-manager", isinstance(second, str) and bound(managed) == [second], index(managed))
    asking = file("Probe a question to the owner")
    question = ask(asking, "may the sync run", owner=True)
    refused("authority-owner-question", asking, lambda: decide(asking, "the sync may run", answers=question), question, "asks the owner")
    stored(asking, {"text": "DECIDED: the sync may run\n", "decision": "the sync may run", "by": "probe-manager", "answers": question})
    kept = asked(asking) == [question]
    answer = decide(asking, "the sync may run", by="owner", answers=question, quote="yes, run it")
    cases.step("authority-owner-answers", kept and isinstance(answer, str) and asked(asking) == [], index(asking))


def binding_cases():
    left, right = file("Probe a left part"), file("Probe a right part")
    middle = file("Probe a middle task", parts=[left, right])
    root = file("Probe a binding root", parts=[middle])
    on_root, on_middle, on_left, on_right = (decide(n, f"rule on the {place}") for n, place in ((root, "root"), (middle, "middle"), (left, "left"), (right, "right")))
    seen = bound(left)
    cases.step("binding-ancestors", {on_root, on_middle, on_left} <= set(seen) and on_right not in seen, index(left))
    use("resolve", root, "--summary", "probe stopped", "--not-planned")
    cases.step("binding-stopped-root", bound(left) == [] and bound(root) == [], index(left))
    task = file("Probe a question")
    question = ask(task, "which width counts")
    use("hold", task, "--holders", "probe-worker")
    cases.step("binding-event-keeps-question", asked(task) == [question], index(task))
    other = ask(task, "which height counts")
    decide(task, "any height counts", answers=other)
    # a decision naming another question leaves this one open
    named_other = asked(task) == [question]
    decide(task, "24 to 80 columns count", answers=question)
    cases.step("binding-answered", named_other and asked(task) == [], index(task))
    gated = file("Probe a one-way door")
    worker = decide(gated, "drop the cache", by="probe-worker", door="one-way")
    waited = worker not in bound(gated)
    decide(gated, "drop the cache")
    cases.step("binding-one-way-waits", waited and worker in bound(gated), index(gated))
    held = file("Probe a door over a manager's rule")
    rule = decide(held, "keep the cache")
    pending = decide(held, "drop the cache", by="probe-worker", door="one-way", supersedes=rule)
    kept = bound(held) == [rule]
    followed = decide(held, "drop the cache", supersedes=pending)
    cases.step("binding-one-way-supersedes", kept and bound(held) == [followed], index(held))
    handed = file("Probe a successor's follow")
    door = decide(handed, "drop the index", by="probe-worker", door="one-way")
    decide(handed, "drop the index", by="probe-manager-next")
    cases.step("binding-successor", door in bound(handed), index(handed))


def heartbeat(numbers):
    """The manager's heartbeat decision lines on NUMBERS, as print-team-gaps.py prints them in one poll."""
    done = sandbox.python(GAPS, "--polls", "1", pane="w1:p1")
    lines = [line for line in done.stdout.splitlines() if (found := HEARTBEAT.match(line)) and int(found.group(1)) in numbers]
    return lines if done.returncode == 0 else [f"exit {done.returncode}: {done.stderr}"]


def route_cases():
    blocker = file("Probe a blocking task")
    waiter, part = file("Probe a waiting task", depends=(blocker,)), file("Probe a blocked part", depends=(blocker,))
    parent = file("Probe a parent of a blocked part", parts=(part,))
    routed = lambda numbers: {int(found) for found in re.findall(r"^route #(\d+)", "\n".join(heartbeat(numbers)), re.M)}
    before = routed({blocker, waiter, part, parent})
    cases.step("route-own-depends", waiter not in before and blocker in before, before)
    cases.step("route-parts-blocked", parent not in before and part not in before, before)
    use("resolve", blocker, "--summary", "probe done")
    after = routed({waiter, part, parent})
    cases.step("route-after-close", {waiter, part, parent} <= after, after)


def heartbeat_cases():
    later, earlier = file("Probe a later question"), file("Probe an earlier question")
    ask(earlier, "may the sync run", owner=True)
    time.sleep(1.1)  # the boards stamp to the second
    ask(later, "may the pane change", owner=True)
    task = file("Probe a twice superseded rule")
    rule = decide(task, "cache for an hour")
    decide(task, "cache for a day", supersedes=rule)
    decide(task, "cache for a week", supersedes=rule)
    gated = file("Probe an unfollowed door")
    worker = decide(gated, "drop the index", by="probe-worker", door="one-way")
    redone = file("Probe a door its worker replaced")
    dropped = decide(redone, "drop the cache", by="probe-worker", door="one-way")
    decide(redone, "keep the cache", by="probe-worker", supersedes=dropped)
    asker = file("Probe a worker's question")
    asked_url = ask(asker, "which cache")
    lines = heartbeat({later, earlier, task, gated, redone, asker})
    order = [int(found) for found in re.findall(r"^question #(\d+)", "\n".join(lines), re.M) if int(found) in (later, earlier)]
    cases.step("heartbeat-open-question", order == [earlier, later], lines)
    cases.step("heartbeat-twice-superseded", any(line.startswith(f"superseded twice #{task}: {rule}") for line in lines), lines)
    cases.step("heartbeat-one-way", any(line.startswith(f"one-way #{gated}: probe-worker's {worker}") for line in lines), lines)
    answer_line = next((line for line in lines if line.startswith(f"answer #{asker}:")), "")
    cases.step("heartbeat-answer-line", "`decide`" in answer_line and f"--answers {asked_url}" in answer_line, lines)
    cases.step("heartbeat-one-way-superseded", not any(line.startswith(f"one-way #{redone}:") for line in lines), lines)


def event_cases():
    task = file("Probe an event that answers")
    questions = [ask(task, "may the sync run", owner=True), ask(task, "which cache")]
    stored(task, {"text": "DECIDED: both settled\n", "answers": questions})
    settled = use("read", task).stdout
    shapes = evaluate(f"import task_state\nprint(json.dumps([task_state.invalid({{'text': 'DECIDED: x\\n', 'answers': value}}) for value in {[questions, ['x']]!r}]))")
    cases.step("event-answers", "open questions: 0" in settled and "binding decisions: 0" in settled and shapes[0] is None and shapes[1], [settled, shapes])


def block(lines, number, strip=True):
    """NUMBER's row block in list-task-board.py's LINES: from its row to the next row at any depth, guides stripped when STRIP."""
    start = next((i for i, line in enumerate(lines) if re.match(rf"^[\s│├└]*#{number} ", line)), len(lines))
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^[\s│├└]*#\d+ ", lines[i])), len(lines))
    return [line.lstrip(" │") if strip else line for line in lines[start:end]]


def pane_cases(listed, narrow, untrusted_lines, asker, decider, cutter, untrusted):
    """The pane's lines: LISTED at the pane's width, NARROW at 24 columns, UNTRUSTED_LINES with UNTRUSTED's decision marked untrusted."""
    cases.step("pane-question", "? may the sync run" in block(listed, asker), block(listed, asker))
    marks = [line for line in block(listed, decider) if line.startswith("◆ ")]
    timed = [re.sub(r"^◆ \[\d\d/\d\d \d\d:\d\d\] ", "◆ ", line) for line in marks]  # each decision opens with its time, which the run's clock sets
    cases.step("pane-every-decision", timed == ["◆ rule four", "◆ rule three", "◆ rule two", "◆ rule one"] and marks[0] != timed[0]
         and "more decided" not in "\n".join(block(listed, decider)) and "..." not in "\n".join(block(listed, decider)), block(listed, decider))
    cut = block(narrow, cutter, strip=False)
    start = next((i for i, line in enumerate(cut) if "◆ " in line), len(cut))
    shown = cut[start:start + 3]
    mark = cut[start].find("◆") if shown else 0
    # a decision's later lines sit 2 cells right of its mark, so they read as its own
    cases.step("pane-cut", len(shown) == 3 and shown[2].endswith("…") and all(line[mark:mark + 2] == "  " and line[mark + 2] != " " for line in shown[1:])
         and "beside the probe" not in "\n".join(cut), cut)
    if untrusted:
        cases.step("pane-untrusted", not any(line.startswith("◆ ") for line in block(untrusted_lines, untrusted)), block(untrusted_lines, untrusted))


def board_pane():
    asker, decider, cutter, untrusted = file("Probe an asking task"), file("Probe a deciding task"), file("Probe a long rule"), file("Probe an outsider")
    ask(asker, "may the sync run", owner=True)
    later = file("Probe a question on its second line")
    stored(later, {"text": "BLOCKED:\nwhich width counts\n"})
    for word in ("one", "two", "three", "four"):
        decide(decider, f"rule {word}", by="owner", door="one-way", quote=f"rule {word}")
    decide(cutter, LONG, by="owner", door="one-way", quote="only the sandbox")
    outsider = decide(untrusted, "probe the team's board", by="owner", door="one-way", quote="probe ours")
    listed = sandbox.python(LIST, "probe").stdout.splitlines()
    narrow = sandbox.python(LIST, "probe", "--width", "24").stdout.splitlines()
    untrusted_lines = evaluate(f"""import board, task_board
nodes = board.tree(None)
for node in nodes:
    for comment in node["comments"]["nodes"]:
        comment["trusted"] = comment["url"] != {outsider!r}
print(json.dumps(list(task_board.lines(task_board.board(nodes), task_board.PANE_WIDTH))))""")
    pane_cases(listed, narrow, untrusted_lines, asker, decider, cutter, untrusted)
    cases.step("pane-question-next-line", "? which width counts" in block(listed, later), block(listed, later))


def node(number, comments=()):
    return {"number": number, "title": f"Probe {number}", "url": f"https://github.com/o/r/issues/{number}", "body": body(), "authorAssociation": "OWNER",
            "state": "OPEN", "stateReason": None, "parent": None, "labels": {"nodes": []}, "parts": {"nodes": []}, "partsSummary": {"total": 0},
            "blockedBy": {"nodes": []}, "comments": {"nodes": list(comments)}}


def comment(number, k, text, association="OWNER", **fields):
    return {"body": text, "fields": fields, "url": f"https://github.com/o/r/issues/{number}#issuecomment-{number}0{k}", "authorAssociation": association, "createdAt": f"2026-11-06T0{k}:00:00Z"}


def owner_decision(number, k, decision, association="OWNER"):
    return comment(number, k, f"DECIDED: {decision}\n\n> {decision}\n", association, decision=decision, by="owner", one_way=True)


def nodes_pane():
    nodes = [node(1, [comment(1, 1, "BLOCKED: may the sync run\n", asks="owner")]),
             node(2, [owner_decision(2, k, f"rule {word}") for k, word in enumerate(("one", "two", "three", "four"), 1)]),
             node(3, [owner_decision(3, 1, LONG)]), node(4, [owner_decision(4, 1, "probe the team's board", association="NONE")])]
    path = replay_probe.write_text(sandbox.work, "nodes.json", json.dumps(nodes))
    listed = sandbox.python(LIST, "--nodes", path).stdout.splitlines()
    narrow = sandbox.python(LIST, "--nodes", path, "--width", "24").stdout.splitlines()
    pane_cases(listed, narrow, None, 1, 2, 3, None)
    many = [replay_probe.write_text(sandbox.work, f"many-{count}.json", json.dumps([node(n, [comment(n, k % 10, f"DECIDED: rule {k}") for k in range(20)])
                                                                                    for n in range(1, count + 1)])) for count in (40, 80)]
    # the parses one draw makes, counted by wrapping the parse in the drawing process
    small, large = evaluate(f"""import board, pathlib, task_board, task_state
original, parses = task_state.records, [0]

def counted(task):
    parses[0] += 1
    return original(task)

def draw(path):
    parses[0] = 0
    task_board.board(board.tree(None, json.loads(pathlib.Path(path).read_text())))
    return parses[0]

task_state.records = counted
print(json.dumps([draw(path) for path in {list(map(str, many))!r}]))""")
    cases.step("pane-linear", large <= 2.5 * small, f"{small} parses for 40 tasks, {large} for 80")
    later = replay_probe.write_text(sandbox.work, "deferred.json", json.dumps([node(1, [comment(1, 1, "DECIDED: later\n\ndeferred: waits on the probe\n", holders=[])])]))
    drawn = sandbox.python(LIST, "--nodes", later).stdout.splitlines()
    cases.step("row-no-deferral", any(line.startswith("#1 ") for line in drawn) and not any("deferred" in line or "no holder" in line for line in drawn), drawn)
    finished = [node(n, [comment(n, 1, text)] if text else []) for n, text in ((1, "REPORTED: batch landed; next step: probe the pane"), (2, ""))]
    for parent in finished[:2]:
        part = node(parent["number"] + 10)
        part.update({"state": "CLOSED", "stateReason": "COMPLETED", "parent": {"number": parent["number"]}})
        parent["body"] = body((part["number"],))
        finished.append(part)
    done = replay_probe.write_text(sandbox.work, "finished.json", json.dumps(finished))
    shown = {row["number"]: row["lines"]["notes"] for row in json.loads(sandbox.python(LIST, "--nodes", done, "--json").stdout or "[]")}
    cases.step("row-finished-parent", "next step: probe the pane" in shown.get(1, []) and shown.get(2) == [], shown)
    rows = json.loads(sandbox.python(LIST, "--nodes", path, "--json").stdout or "[]")
    pane = (ROOT / "hooks" / "draw-task-pane.tsx").read_text()
    cases.step("row-one-color", rows and not any("kind" in row for row in rows) and 'numeral(task.number, label, spans(\'title\', 0), numberColor)' in pane, [sorted(row) for row in rows[:1]])


def main(args):
    global sandbox
    if not args:
        return replay_probe.run_every(__file__, "--board", ("git", "nodes"))
    if len(args) != 2 or args[0] != "--board" or args[1] not in ("git", "nodes"):
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("task-decisions-") as work:
        sandbox = replay_probe.Sandbox(work, [replay_probe.agent("probe-manager", 1), replay_probe.agent("probe-worker", 2)])
        for kind in (nodes_pane,) if args[1] == "nodes" else (record_cases, authority_cases, binding_cases, heartbeat_cases, event_cases, route_cases, board_pane):
            kind()
    return cases.finish()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
