#!/usr/bin/env python3
"""Do one board operation through the board port, so a session writes the same way on any board.

usage: use-board.py read <task> [--as worker|judge] [--full] [--body]
usage: use-board.py comment <task> (--blocked <question> | --reported <line>) [--text <file>] [--asks owner] [--option <answer>]...
usage: use-board.py decide <task> --decision <sentence> [--text <file>] [--by <who>] [--one-way] [--supersedes <url>] [--answers <url>] [--holders <names>] [--live-runs <n>]
usage: use-board.py hold <task> --holders <names>
usage: use-board.py depend <task> --depends <numbers>
usage: use-board.py file --title <title> --body <file> [--label <name>]... [--scope <folder>] [--depends <numbers>]
usage: use-board.py edit <task> --body <file> --reason <what changed> --base <sha>
usage: use-board.py title <task> --title <title>
usage: use-board.py resolve <task> --summary <line> [--text <file>] [--not-planned]
usage: use-board.py reopen <task>
usage: use-board.py label <task> --label <name> [--remove]

`<task>` is a number or url. The script writes the keyword line, so `--text` holds what follows it; `<names>` and `<numbers>`
split by spaces, `""` for none. A write prints its url; a refused one posts nothing, exits 2 and names the fix. Meanings:
references/task-grammar.md; `--scope`: references/adapters/board.md."""
import difflib
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402
import criteria_check  # noqa: E402
import decisions  # noqa: E402
import task_state  # noqa: E402
from judge_note import without_judge_note  # noqa: E402
import own_reports  # noqa: E402
import session  # noqa: E402
import team_names  # noqa: E402
import usage_parser  # noqa: E402

# the option that carries each keyword's line, so a text file that opens with a keyword is refused naming it
LINE_OPTIONS = {task_state.ASK: "--blocked", task_state.INFORM: "--reported", task_state.ANSWER: "--decision"}


def my_name():
    return session.own_name()


def keep_own(url, text):
    """A manager's own report is news to no one, so its heartbeat is told not to feed it back."""
    if task_state.keyword(text) == task_state.INFORM and team_names.role(my_name()) == "manager":
        own_reports.note(url)


def read_text(path):
    return pathlib.Path(path).read_text()


def composed(verb, keyword, line, option, path):
    """The comment `KEYWORD: LINE`, then the text of PATH when one is given; refused, naming the option, when LINE is not one line
    or the text opens with a keyword, since the script writes the keyword line and a text holds only what follows it."""
    found = [] if line.strip() and "\n" not in line.strip() else [f"`{option}` takes one line that is not empty, as `{option} '<one line>'`; put the rest in `--text <file>`"]
    rest = read_text(path) if path else ""
    if task_state.keyword(rest):
        found.append(f"{path} opens `{task_state.keyword(rest)}:`, a keyword line the script writes itself; pass that line's words as "
                     f"`{LINE_OPTIONS[task_state.keyword(rest)] if verb == 'comment' else option} '<line>'` and keep only what follows it in the file")
    refuse(verb, found)
    return f"{keyword}: {line.strip()}" + (f"\n\n{rest.lstrip(chr(10))}" if rest.strip() else "\n")


def refuse(verb, found):
    if found:
        print(f"use-board: nothing posted, the {verb} has defects:\n- " + "\n- ".join(found) + f"\nthe grammar is {task_state.GRAMMAR}", file=sys.stderr)
        sys.exit(2)


def numbers(words, option="--depends"):
    """The task numbers WORDS names, `12` or `#12`, split by spaces."""
    found = [decisions.task_number(word) for word in words.split()]
    refuse("write", [f"`{option}` takes task numbers split by spaces, as `{option} '12 #13'`"] if None in found else [])
    return found


def summary(fields):
    """A stored comment's fields on one line, for a reader of its text."""
    return "; ".join(key.replace("_", " ") + (f": {' '.join(value) if isinstance(value, list) else value}" if value is not True else "")
                     for key, value in fields.items() if key not in ("decision", "options"))


def read_task(options):
    role = options.as_role
    if options.body:
        if role or options.full:
            print("use-board: `--body` prints the stored body alone; drop `--as` and `--full`", file=sys.stderr)
            usage_parser.refuse(__doc__)
        # the stored body and nothing else, so a file of it is what `edit` compares the new body with
        sys.stdout.write(board.body(options.task))
        return 0
    tasks = decisions.read(options.task, board.fresh)
    task = tasks[options.task]
    state = task_state.compose(task, board.blockers(task["number"]))
    print(f"#{task['number']} {task_state.title(task)}\nstate: {task['state']}{', ' + state['waits'] if task['state'] == 'OPEN' else ''}\nholders: {' '.join(state['holders'] or [])}\n"
          f"{'scope: ' + (task['scope'] or '(repository root)') + chr(10) if 'scope' in task else ''}labels: {', '.join(task['labels'])}\nparent: {task['parent']}\n"
          f"depends: {' '.join(f'#{number}' for number in task['depends'])}\nbody sha: {board.body_sha(task['body'])}\n\n{task['body']}\n")
    print("\n".join(decisions.lines(task["number"], tasks, questions=role != "judge")))
    for comment in task["comments"]:
        if role == "judge" and task_state.keyword(comment["body"]) == task_state.ASK:
            continue
        text = without_judge_note(comment["body"]) if role == "worker" else comment["body"]
        if not options.full:
            text = task_state.DIFF.sub(lambda found: f"(a diff of {found.group(2).count(chr(10))} lines, which `read --full` prints)", text)
        said = summary(comment.get("fields") or {})
        offered = "".join(f"\n{place}. {option}" for place, option in enumerate((comment.get("fields") or {}).get("options", []), 1))
        print(f"\n--- {comment['url']}{' (' + said + ')' if said else ''}\n{text}{offered}")
    return 0


def post_comment(options):
    keyword, line, option = (task_state.ASK, options.blocked, "--blocked") if options.blocked is not None else (task_state.INFORM, options.reported, "--reported")
    text = composed("comment", keyword, line, option, options.text)
    offered = options.option
    if options.asks not in (None, "owner"):
        refuse("comment", ["write `--asks owner` or drop `--asks`, since a question without it goes to the manager"])
    if (options.asks or offered) and keyword != task_state.ASK:
        refuse("comment", ["`--asks owner` and `--option` go only on a question, `--blocked '<question>'`"])
    if options.asks and len(offered) < 2:
        refuse("comment", ["a question to the owner offers two answers or more, each as `--option '<answer>'`, since the owner answers with a number"])
    refuse("comment", task_state.defects("comment", text))
    url = board.comment(options.task, text, {**({"asks": "owner"} if options.asks else {}), **({"options": offered} if offered else {})})
    keep_own(url, text)
    print(url)
    return 0


def decide_task(options):
    said = composed("decide", task_state.ANSWER, options.decision, "--decision", options.text)
    found = task_state.defects("decide", said)
    by = options.by or my_name()
    if not by:
        found.append("no session name tells who decides; pass `--by owner` or `--by <your session's name>`")
    if not (options.live_runs or "0").isdigit():
        found.append("`--live-runs` takes one count, as `--live-runs 12`")
    refuse("decide", found)
    fields = {"decision": task_state.first_line(said), "by": by, **{key: getattr(options, key) for key in ("supersedes", "answers") if getattr(options, key) is not None}}
    fields.update({"one_way": True} if options.one_way else {})
    fields.update({"holders": options.holders.split()} if options.holders is not None else {})
    fields.update({"live_runs": int(options.live_runs)} if options.live_runs is not None else {})
    refuse("decide", decisions.refusals(options.task, said, fields, decisions.read(options.task, board.fresh)))
    print(board.comment(options.task, said, fields))
    return 0


def hold_task(options):
    names = options.holders.split()
    print(board.comment(options.task, f"{task_state.ANSWER}: {' and '.join(names)} hold{'s' * (len(names) == 1)} this." if names else f"{task_state.ANSWER}: no one holds this.",
                        {"holders": names}))
    return 0


def depend_task(options):
    print(board.depend(options.task, numbers(options.depends)))
    return 0


def file_task(options):
    title, body = options.title, read_text(options.body)
    # a Goal that names no flow of its changed part would sit on the board until a lint found it, so it is refused before it is filed
    refuse("file", task_state.defects("file", body) + task_state.defects("title", title) + criteria_check.body_refusals(body))
    scope = {"scope": options.scope} if options.scope is not None else {}
    print(board.fresh(board.file(title, body, options.label, depends=numbers(options.depends or ""), **scope), comments=False)["url"])
    return 0


def edit_body(options):
    """Posts the keyword line `DECIDED: <reason>` with the diff from the stored body to the new one, then stores the new body, both or neither."""
    task, body_file, base = options.task, options.body, options.base
    refuse("edit", task_state.defects("reason", options.reason))
    line = f"{task_state.ANSWER}: {options.reason.strip()}"
    new = read_text(body_file)
    if re.match(r"--- .*\n\+\+\+ .*\n@@ ", new):
        sys.exit(f"use-board: {body_file} is a diff, so nothing was posted or changed: hand the whole new body, which `read {task} --body` prints to start from")
    refusal = []

    def land():
        # read again on each try: a board that lost a write race runs this again from the newer body, so --base holds against that write too
        refusal.clear()
        # the web editor saves CRLF, which a body written from the shown text never holds
        old = board.body(task).replace("\r\n", "\n")
        if board.body_sha(old) != base:
            refusal.append((2, f"#{task}'s body changed since you read it (its body sha is {board.body_sha(old)}, not `--base {base}`), so nothing was posted or changed: "
                               "read it again and make the new body from that one"))
            return None
        if new.strip() == old.strip():
            refusal.append((1, f"{body_file} is #{task}'s body as it stands, so nothing was posted or changed"))
            return None
        # a defect the body already held does not block the edit that may fix it
        found = task_state.defects("edit-body", new, old) + criteria_check.body_refusals(new, task, old)
        if found:
            refusal.append((2, "nothing posted or changed, the edit has defects:\n- " + "\n- ".join(found) + f"\nthe grammar is {task_state.GRAMMAR}"))
            return None
        try:
            board.check_links(task, new)
        except LookupError as e:
            refusal.append((1, str(e)))
            return None
        # split at the newline alone: str.splitlines also splits at a form feed or U+2028, which a diff reads as part of a line
        old_lines, new_lines = (re.findall(r"[^\n]*\n|[^\n]+", text) for text in (old, new))
        diff = "".join(piece if piece.endswith("\n") else piece + "\n\\ No newline at end of file\n" for piece in difflib.unified_diff(old_lines, new_lines, "body", "body"))
        fence = "`" * max([3] + [len(run) + 1 for run in re.findall(r"`+", diff)])
        url = board.comment(task, f"{line}\n\n{fence}diff\n{diff}{fence}\n")
        board.edit(task, new)
        return url

    url = board.atomic(land)
    if refusal:
        code, message = refusal[0]
        print(f"use-board: {message}", file=sys.stderr)
        return code
    print(f"{url}\nuse-board: #{task}'s body is the new one, and its new comment holds the diff")
    return 0


def resolve_task(options):
    text = composed("resolve", task_state.INFORM, options.summary, "--summary", options.text)
    refuse("resolve", task_state.defects("resolve", text))
    board.resolve(options.task, text, not options.not_planned)
    closed = board.fresh(options.task)
    if closed and closed["comments"]:
        keep_own(closed["comments"][-1]["url"], closed["comments"][-1]["body"])
    return 0


def retitle_task(options):
    refuse("title", task_state.defects("title", options.title))
    board.retitle(options.task, options.title)
    return 0


def reopen_task(options):
    board.reopen(options.task)
    return 0


def label_task(options):
    board.label(options.task, options.label, options.remove)
    return 0


TEXT = ("--text", {"metavar": "FILE"})
# verb -> (what it does, whether it names a task by place, its options as (flag, argparse keywords)); a flag with no keywords takes one value
VERBS = {"read": (read_task, True, [("--as", {"dest": "as_role", "choices": ("worker", "judge")}), ("--full", {"action": "store_true"}), ("--body", {"action": "store_true"})]),
         "comment": (post_comment, True, [("--blocked", {"group": "line"}), ("--reported", {"group": "line"}), TEXT, ("--asks", {}), ("--option", {"action": "append", "default": []})]),
         "decide": (decide_task, True, [("--decision", {"required": True}), TEXT, ("--by", {}), ("--one-way", {"action": "store_true"}), ("--supersedes", {}),
                                        ("--answers", {}), ("--holders", {}), ("--live-runs", {})]),
         "hold": (hold_task, True, [("--holders", {"required": True})]),
         "depend": (depend_task, True, [("--depends", {"required": True})]),
         "file": (file_task, False, [("--title", {"required": True}), ("--body", {"required": True}), ("--label", {"action": "append", "default": []}), ("--scope", {}),
                                     ("--depends", {})]),
         "edit": (edit_body, True, [("--body", {"required": True}), ("--reason", {"required": True}), ("--base", {"required": True})]),
         "title": (retitle_task, True, [("--title", {"required": True})]),
         "resolve": (resolve_task, True, [("--summary", {"required": True}), TEXT, ("--not-planned", {"action": "store_true"})]),
         "reopen": (reopen_task, True, []),
         "label": (label_task, True, [("--label", {"required": True}), ("--remove", {"action": "store_true"})])}


def parser():
    """The parser of every verb, each refusing a call it cannot read by naming what argparse found wrong, then the usage."""
    def refused(message):
        print(f"use-board: {message}", file=sys.stderr)
        usage_parser.refuse(__doc__)
    made = usage_parser.parser(__doc__, prog="use-board.py", allow_abbrev=False)
    made.error = refused
    verbs = made.add_subparsers(dest="verb", required=True)
    for verb, (run, by_place, flags) in VERBS.items():
        each = verbs.add_parser(verb, add_help=False, allow_abbrev=False)
        each.error = refused
        each.set_defaults(run=run)
        if by_place:
            each.add_argument("task")
        groups = {}
        for flag, keywords in flags:
            keywords = dict(keywords)
            group = keywords.pop("group", None)
            if group and group not in groups:
                groups[group] = each.add_mutually_exclusive_group(required=True)
            (groups[group] if group else each).add_argument(flag, **keywords)
    return made


def main(args):
    options = parser().parse_args(args)
    try:
        if getattr(options, "task", None) is not None:
            # a caller holds a task as its number or as the url a write printed, so either names it
            number = decisions.task_number(options.task)
            if number is None:
                print(f"use-board: {options.task!r} names no task; give its number or its url", file=sys.stderr)
                usage_parser.refuse(__doc__)
            options.task = number
        return options.run(options)
    except task_state.Refused as e:
        print(f"use-board: {e}", file=sys.stderr)
        return 2
    except (OSError, LookupError, subprocess.CalledProcessError) as e:
        sys.exit(f"use-board: {e}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
