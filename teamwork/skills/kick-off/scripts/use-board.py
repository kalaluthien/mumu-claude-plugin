#!/usr/bin/env python3
"""Do one board operation through the board port, so a session writes the same way on any board.

usage: use-board.py <operation> <args>

A text is Markdown a person reads: no code reads it for data, which every call takes as options and keeps as board-record-schema.json says.
A write that breaks the grammar posts nothing, exits 2 and names the fix: a comment that opens with neither `BLOCKED:` nor `REPORTED:`, a text that
is empty or its keyword alone or holds a `teamwork` or `decision` fence, a misspelt section heading, a title, summary line, criterion name or decision beyond the Plain words caps,
or, in a `file` or an `edit` of a task numbered at or above the Goal cut-off, a `## Goal` that names no flow of its changed part, unless the body edited held that defect already.

  read <issue> [--as worker|judge] [--full]   print its title, state, labels, parent, body, the decisions that bind it, its open questions and its comments, each
                                        body edit's diff cut to one line unless `--full`; as a worker without each `Judge note:` paragraph,
                                        which names probes of a criterion's implementation, as a judge without the open questions and each `BLOCKED:` comment, which are worker history
  comment <issue> <body-file> [--asks owner] [--option <answer>]...   append the file's text, which opens `BLOCKED:` to ask a question or `REPORTED:` to say anything else;
                                        each `--option` one answer the question offers, shown numbered in the order given; `--asks owner` on a question
                                        the owner answers, not the manager, which takes two options or more
  decide <issue> <body-file> [--by <who>] [--one-way] [--supersedes <url>] [--answers <url>] [--holders <names>] [--live-runs <n>]
                                        post a decision, `DECIDED: ` put first when the text lacks it: its first line is the binding sentence, decided `--by owner`,
                                        the owner's words quoted in the text, else by the calling session; `--one-way` when it is hard to undo; `--supersedes` the url
                                        of the decision it replaces, `--answers` that of the `BLOCKED:` it settles; `--holders 'a-worker b-worker'` sets who holds
                                        the task and `--live-runs` its cap; refused, nothing posted, when it breaks a rule of the grammar's Decisions section
  hold <issue> [<name>...]              set the sessions that hold the task, no one when none is named, as an event, which binds nothing
  depend <issue> [<number>...]          set the tasks it waits on, none when none is named, refused when they make a cycle or name an unknown issue
  file <title> <body-file> [label...] [--scope <folder>] [--depends <numbers>]   open an issue in the folder, a path from the repository root ('' the root; a manager's own
                                        project folder when none is given, else the root), refused when the repository has no such folder; print its url;
                                        its `[task]` lines and `--depends '12 13'` link it, refused when they make a cycle, a second parent or name an unknown issue
  edit <issue> <diff-file> <line> --base <sha>   change the body by a diff, with the keyword line [edit-issue-body.py](edit-issue-body.py) posts first;
                                        refused when the body no longer has the `body sha` `read` printed, the sha given as `--base`
  title <issue> <title>                 change the title
  resolve <issue> <summary-file> [--not-planned]   close it with the summary, `REPORTED: ` put first when it lacks it
  reopen <issue>                        open a closed issue again
  label <issue> <name> [--remove]"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
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
    return subprocess.run([sys.executable, str(HERE / "edit-issue-body.py"), *map(str, operands), *(["--base", options["--base"]] if "--base" in options else [])]).returncode


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
VERBS = {"read": ((1,), {"--as": True, "--full": False}, read_issue),
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
