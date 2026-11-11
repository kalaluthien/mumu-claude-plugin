#!/usr/bin/env python3
"""Do one board operation through the board port, so a session writes the same way on any board.

usage: use-board.py read <issue> [--as worker|judge] [--full] [--body]
usage: use-board.py comment <issue> <text-file> [--asks owner] [--option <answer>]...
usage: use-board.py decide <issue> <text-file> [--by <who>] [--one-way] [--supersedes <url>] [--answers <url>] [--holders <names>] [--live-runs <n>]
usage: use-board.py hold <issue> [<name>...]
usage: use-board.py depend <issue> [<number>...]
usage: use-board.py file <title> <body-file> [<label>...] [--scope <folder>] [--depends <numbers>]
usage: use-board.py edit <issue> <body-file> <keyword line> --base <sha>
usage: use-board.py title <issue> <title>
usage: use-board.py resolve <issue> <summary-file> [--not-planned]
usage: use-board.py reopen <issue>
usage: use-board.py label <issue> <name> [--remove]

`<issue>` is a task's number or its url. A write prints the url of what it wrote; one that breaks the grammar posts nothing, exits 2 and
names the fix. What each verb and option means: references/issue-grammar.md, and for `--scope` references/adapters/board.md."""
import difflib
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402
import criteria_check  # noqa: E402
import decisions  # noqa: E402
import issue_state  # noqa: E402
from judge_note import without_judge_note  # noqa: E402
import own_reports  # noqa: E402
import session  # noqa: E402
import team_names  # noqa: E402


MANY = "many"


class Unread(Exception):
    """A call the script cannot read, which prints the usage."""


def my_name():
    return session.sessions()[1].get("name")


def keep_own(url, text):
    """A manager's own report is news to no one, so its heartbeat is told not to feed it back."""
    if issue_state.keyword(text) == issue_state.INFORM and team_names.role(my_name()) == "manager":
        own_reports.note(url)


def read_text(path):
    return pathlib.Path(path).read_text()


def keyed(keyword, path):
    """The text of PATH, KEYWORD put first when it opens with no keyword, so a text the verb names gets its keyword rather than a refusal no caller can read,
    and one that opens with another verb's keeps it and is refused."""
    text = read_text(path)
    return text if issue_state.keyword(text) else f"{keyword} {text}"


def refuse(verb, found):
    if found:
        print(f"use-board: nothing posted, the {verb} has defects:\n- " + "\n- ".join(found) + f"\nthe grammar is {issue_state.GRAMMAR}", file=sys.stderr)
        sys.exit(2)


def numbers(words):
    """The task numbers WORDS name, `12` or `#12`, split by spaces."""
    found = [decisions.task_number(word) for word in " ".join(words).split()]
    if None in found:
        raise Unread
    return found


def summary(fields):
    """A stored comment's fields on one line, for a reader of its text."""
    return "; ".join(key.replace("_", " ") + (f": {' '.join(value) if isinstance(value, list) else value}" if value is not True else "")
                     for key, value in fields.items() if key not in ("decision", "options"))


def read_issue(operands, options):
    role = options.get("--as")
    if role not in (None, "worker", "judge"):
        raise Unread
    if "--body" in options:
        if len(options) > 1:
            raise Unread
        # the stored body and nothing else, so a file of it is what `edit` compares the new body with
        sys.stdout.write(board.body(operands[0]))
        return 0
    issues = decisions.read(operands[0], board.fresh)
    issue = issues[operands[0]]
    state = issue_state.compose(issue, board.blockers(issue["number"]))
    print(f"#{issue['number']} {issue_state.title(issue)}\nstate: {issue['state']}{', ' + state['waits'] if issue['state'] == 'OPEN' else ''}\nholders: {' '.join(state['holders'] or [])}\n"
          f"{'scope: ' + (issue['scope'] or '(repository root)') + chr(10) if 'scope' in issue else ''}labels: {', '.join(issue['labels'])}\nparent: {issue['parent']}\n"
          f"depends: {' '.join(f'#{number}' for number in issue['depends'])}\nbody sha: {board.body_sha(issue['body'])}\n\n{issue['body']}\n")
    print("\n".join(decisions.lines(issue["number"], issues, questions=role != "judge")))
    for comment in issue["comments"]:
        if role == "judge" and issue_state.keyword(comment["body"]) == issue_state.ASK:
            continue
        text = without_judge_note(comment["body"]) if role == "worker" else comment["body"]
        if "--full" not in options:
            text = issue_state.DIFF.sub(lambda found: f"(a diff of {found.group(2).count(chr(10))} lines, which `read --full` prints)", text)
        said = summary(comment.get("fields") or {})
        offered = "".join(f"\n{place}. {option}" for place, option in enumerate((comment.get("fields") or {}).get("options", []), 1))
        print(f"\n--- {comment['url']}{' (' + said + ')' if said else ''}\n{text}{offered}")
    return 0


def post_comment(operands, options):
    text = read_text(operands[1])
    offered = options.get("--option", [])
    if options.get("--asks", "owner") != "owner":
        refuse("comment", ["write `--asks owner` or drop `--asks`, since a question without it goes to the manager"])
    if options and issue_state.keyword(text) != issue_state.ASK:
        refuse("comment", [f"`--asks owner` and `--option` go only on a text that opens `{issue_state.ASK}:`"])
    if "--asks" in options and len(offered) < 2:
        refuse("comment", ["a question to the owner offers two answers or more, each as `--option '<answer>'`, since the owner answers with a number"])
    refuse("comment", issue_state.defects("comment", text))
    url = board.comment(operands[0], text, {**({"asks": "owner"} if "--asks" in options else {}), **({"options": offered} if offered else {})})
    keep_own(url, text)
    print(url)
    return 0


def decide_issue(operands, options):
    said = keyed(issue_state.ANSWER + ":", operands[1])
    found = issue_state.defects("decide", said)
    by = options.get("--by") or my_name()
    if not by:
        found.append("no session name tells who decides; pass `--by owner` or `--by <your session's name>`")
    if not options.get("--live-runs", "0").isdigit():
        found.append("`--live-runs` takes one count, as `--live-runs 12`")
    refuse("decide", found)
    fields = {"decision": issue_state.first_line(said), "by": by, **{key[2:]: options[key] for key in ("--supersedes", "--answers") if key in options}}
    fields.update({"one_way": True} if "--one-way" in options else {})
    fields.update({"holders": options["--holders"].split()} if "--holders" in options else {})
    fields.update({"live_runs": int(options["--live-runs"])} if "--live-runs" in options else {})
    refuse("decide", decisions.refusals(operands[0], said, fields, decisions.read(operands[0], board.fresh)))
    print(board.comment(operands[0], said, fields))
    return 0


def hold_issue(operands, options):
    names = operands[1:]
    print(board.comment(operands[0], f"{issue_state.ANSWER}: {' and '.join(names)} hold{'s' * (len(names) == 1)} this." if names else f"{issue_state.ANSWER}: no one holds this.",
                        {"holders": names}))
    return 0


def depend_issue(operands, options):
    print(board.depend(operands[0], numbers(operands[1:])))
    return 0


def file_issue(operands, options):
    title, body = operands[0], read_text(operands[1])
    # a Goal that names no flow of its changed part would sit on the board until a lint found it, so it is refused before it is filed
    refuse("file", issue_state.defects("file", body) + issue_state.defects("title", title) + criteria_check.goal_refusals(body))
    scope = {"scope": options["--scope"]} if "--scope" in options else {}
    print(board.fresh(board.file(title, body, operands[2:], depends=numbers([options.get("--depends", "")]), **scope), comments=False)["url"])
    return 0


def edit_body(operands, options):
    """Posts the keyword line with the diff from the stored body to the new one, then stores the new body, both or neither."""
    issue, body_file, line = operands
    if "--base" not in options:
        raise Unread
    new = read_text(body_file)
    refuse("edit", issue_state.defects("edit-line", line))
    if re.match(r"--- .*\n\+\+\+ .*\n@@ ", new):
        sys.exit(f"use-board: {body_file} is a diff, so nothing was posted or changed: hand the whole new body, which `read {issue} --body` prints to start from")
    refusal = []

    def land():
        # read again on each try: a board that lost a write race runs this again from the newer body, so --base holds against that write too
        refusal.clear()
        # the web editor saves CRLF, which a body written from the shown text never holds
        old = board.body(issue).replace("\r\n", "\n")
        if board.body_sha(old) != options["--base"]:
            refusal.append((1, f"#{issue}'s body changed since you read it (its body sha is {board.body_sha(old)}, not {options['--base']}), so nothing was posted or changed: "
                               "read it again and make the new body from that one"))
            return None
        if new.strip() == old.strip():
            refusal.append((1, f"{body_file} is #{issue}'s body as it stands, so nothing was posted or changed"))
            return None
        # a defect the body already held does not block the edit that may fix it
        found = issue_state.defects("edit-body", new, old) + criteria_check.goal_refusals(new, issue, old)
        if found:
            refusal.append((2, "nothing posted or changed, the edit has defects:\n- " + "\n- ".join(found) + f"\nthe grammar is {issue_state.GRAMMAR}"))
            return None
        try:
            board.check_links(issue, new)
        except LookupError as e:
            refusal.append((1, str(e)))
            return None
        # split at the newline alone: str.splitlines also splits at a form feed or U+2028, which a diff reads as part of a line
        old_lines, new_lines = (re.findall(r"[^\n]*\n|[^\n]+", text) for text in (old, new))
        diff = "".join(piece if piece.endswith("\n") else piece + "\n\\ No newline at end of file\n" for piece in difflib.unified_diff(old_lines, new_lines, "body", "body"))
        fence = "`" * max([3] + [len(run) + 1 for run in re.findall(r"`+", diff)])
        url = board.comment(issue, f"{line}\n\n{fence}diff\n{diff}{fence}\n")
        board.edit(issue, new)
        return url

    url = board.atomic(land)
    if refusal:
        code, message = refusal[0]
        print(f"use-board: {message}", file=sys.stderr)
        return code
    print(f"{url}\nuse-board: #{issue}'s body is the new one, and its new comment holds the diff")
    return 0


def resolve_issue(operands, options):
    text = keyed(issue_state.INFORM + ":", operands[1])
    refuse("resolve", issue_state.defects("resolve", text))
    board.resolve(operands[0], text, "--not-planned" not in options)
    closed = board.fresh(operands[0])
    if closed and closed["comments"]:
        keep_own(closed["comments"][-1]["url"], closed["comments"][-1]["body"])
    return 0


def retitle_issue(operands, options):
    refuse("title", issue_state.defects("title", operands[1]))
    board.retitle(*operands)
    return 0


def reopen_issue(operands, options):
    board.reopen(operands[0])
    return 0


def label_issue(operands, options):
    board.label(operands[0], operands[1], "--remove" in options)
    return 0


# verb -> (the operand counts it takes, None for any count from the first on; its options, each True when it takes a value and MANY when it may repeat; what it does)
VERBS = {"read": ((1,), {"--as": True, "--full": False, "--body": False}, read_issue),
         "comment": ((2,), {"--asks": True, "--option": MANY}, post_comment),
         "decide": ((2,), {"--by": True, "--one-way": False, "--supersedes": True, "--answers": True, "--holders": True, "--live-runs": True}, decide_issue),
         "hold": ((1, None), {}, hold_issue),
         "depend": ((1, None), {}, depend_issue),
         "file": ((2, None), {"--scope": True, "--depends": True}, file_issue),
         "edit": ((3,), {"--base": True}, edit_body),
         "title": ((2,), {}, retitle_issue),
         "resolve": ((2,), {"--not-planned": False}, resolve_issue),
         "reopen": ((1,), {}, reopen_issue),
         "label": ((2,), {"--remove": False}, label_issue)}


def split(words, known):
    """(operands, {option: its value, or True}) of WORDS; any other word that starts with `--` is an option the script does not know, never a title, a label or an option's value."""
    operands, options, at = [], {}, 0
    while at < len(words):
        word = words[at]
        if word in known and (not known[word] or at + 1 < len(words) and not words[at + 1].startswith("--")):
            options[word] = [*options.get(word, []), words[at + 1]] if known[word] == MANY else words[at + 1] if known[word] else True
            at += 1 + bool(known[word])
        elif word.startswith("--"):
            raise Unread
        else:
            operands.append(word)
            at += 1
    return operands, options


def main(args):
    verb, *words = args or [""]
    try:
        counts, known, run = VERBS.get(verb) or ((), {}, None)
        operands, options = split(words, known)
        if not (len(operands) in counts or None in counts and len(operands) >= counts[0]):
            raise Unread
        if verb != "file":
            # a caller holds a task as its number or as the url a write printed, so either names it
            operands[0] = decisions.task_number(operands[0])
            if operands[0] is None:
                raise Unread
        return run(operands, options)
    except Unread:
        print(__doc__, file=sys.stderr)
        return 2
    except issue_state.Refused as e:
        print(f"use-board: {e}", file=sys.stderr)
        return 2
    except (OSError, LookupError, subprocess.CalledProcessError) as e:
        sys.exit(f"use-board: {e}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
