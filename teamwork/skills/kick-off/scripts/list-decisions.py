#!/usr/bin/env python3
"""Print a task's binding set, the decisions on it and its ancestors that bind it now, then the open questions on them, so a worker
starts from these instead of every thread; exit 1 when the board read failed. With `--as judge` it omits the open questions, since a
judge scores the change and not the worker's doubts.

usage: list-decisions.py <issue> [--as judge]"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402
import decisions  # noqa: E402
import issue_state  # noqa: E402


def main(args):
    judge = args[1:] == ["--as", "judge"]
    number = decisions.task_number(args[0]) if args and (len(args) == 1 or judge) else None
    if number is None:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        issues = decisions.read(number, board.fresh)
    except LookupError as e:
        print(f"list-decisions: {e}, so nothing is listed", file=sys.stderr)
        return 1
    bound = decisions.binding(number, issues)
    print(f"#{number} binding set: {len(bound)} decisions")
    for decision in bound:
        door = f", {decision['door']}" if decision["door"] else ""
        links = [f"supersedes {decision['supersedes']}"] * bool(decision["supersedes"]) + [f"answers {decision['answers']}"] * bool(decision["answers"])
        links += [f"waits on {' '.join(f'#{n}' for n in decision['depends'])}"] * bool(decision["depends"])
        print(f"- #{decision['task']} {decision['decider']}{door}: {decision['decision']} ({decision['url']})" + "".join(f"; {link}" for link in links))
    if judge:
        return 0
    asked = [(task, question) for task in decisions.chain(number, issues) for question in issue_state.open_questions(decisions.as_issue(issues[task]))]
    print(f"open questions: {len(asked)}")
    for task, question in asked:
        audience = question["fields"].get(issue_state.WORD["audience"]) or "manager"
        print(f"- #{task} to the {audience}: {decisions.first_line(question['ask'])} ({question['ask']['url']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
