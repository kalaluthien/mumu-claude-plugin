#!/usr/bin/env python3
"""Check that a question closes only by a decision that names it, on a scratch git board, and print `ok <case>` or `fail <case>: <what it saw>`
per case, then `PASS question links` or `FAIL question links`, and exit 1 on any failure:
- `first`: a worker asks `BLOCKED: which option?` twice, the first about the export format, the second about the retry count, and both stay open;
- `answer`: a manager's decision with `--answers` naming the first closes it, and `read` still lists the second as open, even after a decision
  with no `--answers` posted for the holder;
- `again`: a re-ask of the first, `--again <first url>`, joins it and closes with it, and the second stays the one open question;
- `refused`: a `--again` that names no question of the task, one that names another board's question, and a `--again` on a report, are refused, and post nothing;
- `not an answer`: a report carrying `answers` leaves the question it names open, a manager's decision naming a question to the owner, written past
  `decide`'s refusal, leaves it open, and a second answer to the first question leaves the first answer its answer.

usage: replay-question-links.py"""
import pathlib
import re
import sys

SKILL = pathlib.Path(__file__).resolve().parents[1]
LIB = SKILL.parents[1] / "lib"
sys.path.insert(0, str(LIB))
import board_refs  # noqa: E402
import replay_probe  # noqa: E402

USE = SKILL / "scripts" / "use-board.py"
URL = re.compile(r"\((git\+file:\S+?)\)$", re.M)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("question-links-") as work:
        return replay(replay_probe.Sandbox(work, [replay_probe.agent("probe-worker", 1), replay_probe.agent("probe-manager", 2)]))


def replay(box):
    cases = replay_probe.Cases("question links")
    step = cases.step

    def use(*argv, pane=None):
        return box.python(USE, *map(str, argv), pane=pane)

    def number(url):
        return int(url.strip().rsplit("/", 1)[-1])

    def ask(task, note, again=None):
        """A worker's `BLOCKED: which option?` on TASK, its rest the file NOTE, repeating the question at the url AGAIN when given."""
        argv = ["comment", task, "--blocked", "which option?", "--text", note] + (["--again", again] if again else [])
        return use(*argv, pane="w1:p1")

    def open_questions(read):
        """The stored refs of the open questions `read` lists, the lines after its `open questions:` count."""
        lines = read.stdout.splitlines()
        start = next((n for n, line in enumerate(lines) if line.startswith("open questions:")), len(lines))
        return [board_refs.stored(url) for url in URL.findall("\n".join(lines[start + 1:]))]

    def note(name, words):
        return replay_probe.write_text(box.work, f"{name}.md", words)

    filed = use("file", "--title", "Probe the question links", "--body", note("body", replay_probe.BODY))
    if not step("filed", filed.returncode == 0, filed.stderr):
        return cases.finish()
    task = number(filed.stdout)

    export, retry = note("export", "Export format: csv or xlsx?\n"), note("retry", "Retry count: 3 or 5?\n")
    first, second = ask(task, export), ask(task, retry)
    url_first, url_second = first.stdout.strip(), second.stdout.strip()
    step("first", first.returncode == 0 and second.returncode == 0 and open_questions(use("read", task)) == [board_refs.stored(url_first), board_refs.stored(url_second)],
         (first.stderr, second.stderr, use("read", task).stdout))

    answered = use("decide", task, "--decision", "Export as csv.", "--by", "probe-manager", "--answers", url_first)
    held = use("decide", task, "--decision", "probe-worker holds this.", "--by", "probe-manager", "--holders", "probe-worker")
    read = use("read", task)
    step("answer", answered.returncode == 0 and held.returncode == 0 and open_questions(read) == [board_refs.stored(url_second)],
         (answered.stderr, held.stderr, read.stdout))

    again = ask(task, export, again=url_first)
    read = use("read", task)
    step("again", again.returncode == 0 and open_questions(read) == [board_refs.stored(url_second)], (again.returncode, again.stderr, read.stdout))

    rean = ask(task, export, again=again.stdout.strip())
    read = use("read", task)
    step("again of again", rean.returncode == 0 and open_questions(read) == [board_refs.stored(url_second)], (rean.returncode, rean.stderr, read.stdout))

    before = box.git("rev-parse", "refs/teamwork-blackboard").strip()
    refused = ask(task, retry, again=answered.stdout.strip())
    foreign = ask(task, retry, again=url_first.replace("/repo/.git/", "/elsewhere/.git/"))
    reported = use("comment", task, "--reported", "a probe note", "--again", url_first, pane="w1:p1")
    step("refused", refused.returncode == 2 and "is no question" in refused.stderr and foreign.returncode == 2 and "belongs to the board of" in foreign.stderr
         and reported.returncode == 2 and "goes only on a question" in reported.stderr
         and box.git("rev-parse", "refs/teamwork-blackboard").strip() == before, (refused.stderr, foreign.stderr, reported.stderr))
    owner = use("comment", task, "--blocked", "which licence?", "--asks", "owner", "--option", "MIT", "--option", "BSD", pane="w1:p1").stdout.strip()
    box.evaluate(f"import board; board.comment({task}, 'REPORTED: retry count noted.', {{'answers': {url_second!r}}}); print(0)")
    box.evaluate(f"import board; board.comment({task}, 'DECIDED: MIT.', {{'decision': 'MIT.', 'by': 'probe-manager', 'answers': {owner!r}}}); print(0)")
    later = use("decide", task, "--decision", "Export as xlsx after all.", "--by", "probe-manager", "--answers", url_first)
    asked = box.evaluate(f"import board, decisions, json, task_state; print(json.dumps([q['answer'] and q['answer']['url'] for q in task_state.questions(decisions.as_task(board.fresh({task})))]))")
    step("not an answer", later.returncode == 0 and open_questions(use("read", task)) == [board_refs.stored(url_second), board_refs.stored(owner)]
         and asked[0] == answered.stdout.strip(), (later.stderr, asked))
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
