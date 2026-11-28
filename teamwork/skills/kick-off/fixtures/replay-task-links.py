#!/usr/bin/env python3
"""Check that every link to a task or a comment reads back to its own record, through use-board.py in a scratch git repository whose folder has a space in
its name and whose tasks sit in the scope `My Docs`, and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS task links` or `FAIL task links`;
exit 1 on any failure:
- `other-board`, `pull-request`: `comment` with the link of a task of another board, and `read` of a GitHub pull request url, each exit 2 naming the board the link belongs to,
  post nothing, and leave the board ref where it was, though the other board holds a task of the same number;
- `callers`: `list-additions.py`, `check-criteria.py` (a task and `--task`), `run-criteria.py`, `estimate-task-time.py` and `backtest-estimate.py --tasks`
  each refuse that link naming its board, as `depend --depends` does, and `list-additions.py`, `check-criteria.py --task` and `backtest-estimate.py --tasks`
  read this board's own link, `check-criteria.py --task` refusing a body file that is not there;
- `moved`: once the board ref is copied to a checkout at another path, a decision a later one supersedes stays superseded, a question a decision answers stays answered,
  and an owner's decision a body edit folded by its url stays folded for `list-additions.py`;
- `moved-gaps`: in that checkout the heartbeat names the one decision two later ones supersede, one by the encoded url and one by the decoded, as its first
  superseder wrote it; the pane drops the superseded decisions, a manager decision a worker's decision superseded and that worker's decision a manager's
  superseded among them, and lists
  an owner's question with its options and two team questions of one first line; `decide` there refuses, for urls of the first checkout given in this one's
  form, an answer to the owner's question by a manager, an answer naming no question,
  pointing to the question's own task when a part holds it, a supersede naming no decision, and a supersede of the owner's decision by a manager, and an answer or a supersede given in the first checkout's
  form, naming that board, posting nothing, while the owner supersedes it; `read` there binds the manager's latest;
- `parent`: `file --parent` files the part in its parent's folder `My Docs` and adds its `[task]` line, the next number after the parent's last criterion, to the
  end of the parent's Definition of done, in one board commit, its diff fenced past the parent's own backtick fence, with the parent's labels unless `--label`
  names others, the `--depends` given, held by the session that holds the parent; an owner's decision on the parent is no addition of the part's, and a decision
  on the part does not bind the parent; a parent
  whose Definition of done ends the body gets a trailing newline; a parent the board does not hold, of another board or given with `--scope` is refused and nothing is filed;
- `parse`: `TaskRef.parse` reads `7`, `#7`, a task's url in `My Docs` or at the root and a comment's url into their scope, number and comment, and refuses
  a url of this board with a query, a fragment other than a comment's or a path not ending in a number, a link of another scheme or with no board ref, a
  url that does not parse, a number with spaces or a newline around it, a url ending in a tab or a newline, or after a space, or holding a control character, and text that is no link, each naming why, and reads a task's url decoded; `stored`
  reads a task's and a comment's url, encoded or not, and gives (0, the text) for text that is no board link and (0, '') for no text;
- `scoped-comment`: a comment in `My Docs` keeps the time it was written, and its url is the percent-encoded path of the board's folder, which names it again.

usage: replay-task-links.py"""
import pathlib
import sys
import time
import urllib.parse

SKILL = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL.parents[1] / "lib"))
import replay_probe  # noqa: E402

USE = SKILL / "scripts" / "use-board.py"
CALLERS = {"list-additions": SKILL / "references" / "worker" / "scripts" / "list-additions.py", "check-criteria": SKILL / "scripts" / "check-criteria.py",
           "run-criteria": SKILL / "scripts" / "run-criteria.py", "estimate-task-time": SKILL / "references" / "estimation" / "scripts" / "estimate-task-time.py",
           "backtest-estimate": SKILL / "references" / "estimation" / "scripts" / "backtest-estimate.py"}
REF = "refs/teamwork-blackboard"
SCOPE = "My Docs"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("task-links-") as work:
        return replay(replay_probe.Sandbox(work, [replay_probe.agent("probe-worker", 1)]), work)


def replay(box, work):
    cases = replay_probe.Cases("task links")
    step = cases.step
    repository, other, copy = (box.init(work / name) for name in ("spaced repo", "otherboard", "moved copy"))
    (repository / SCOPE).mkdir()

    def use(*argv, cwd=repository, pane=None):
        """use-board.py ARGV run from CWD, a `--by <name>` in it run as that decider's session, since the write gate takes the writer only from its session."""
        argv, session = as_decider(box, argv)
        return box.python(USE, *argv, cwd=cwd, pane=pane, **session)

    def ref(cwd=repository):
        return box.git("rev-parse", REF, cwd=cwd).strip()

    def number(url):
        return int(url.strip().rsplit("#", 1)[0].rsplit("/", 1)[1])

    body = replay_probe.write_text(work, "body.md", replay_probe.BODY)
    foreign = use("file", "--title", "Probe another board", "--body", body, cwd=other)
    task = use("file", "--title", "Probe a scoped task", "--body", body, "--scope", SCOPE)
    if foreign.returncode or task.returncode:
        step("filed", False, [foreign.stderr, task.stderr])
        return cases.finish()
    mine = number(task.stdout)

    for name, link, board in (("other-board", foreign.stdout.strip(), f"the board of {other.resolve()}/.git"), ("pull-request", "https://github.com/o/r/pull/1", "github.com")):
        before = ref()
        done = use("comment", link, "--reported", "must not land") if name == "other-board" else use("read", link)
        step(name, done.returncode == 2 and f"belongs to {board}" in done.stderr and ref() == before and number(foreign.stdout) == mine,
             f"exit {done.returncode}, board moved {ref() != before}, same task number {number(foreign.stdout) == mine}, {done.stderr}")

    def call(name, *argv, cwd=repository):
        return box.python(CALLERS[name], *map(str, argv), cwd=cwd)

    link, board, before = foreign.stdout.strip(), f"belongs to the board of {other.resolve()}/.git", ref()
    refusals = {"list-additions": call("list-additions", link), "check-criteria": call("check-criteria", link),
                "check-criteria --task": call("check-criteria", "--task", link, body), "run-criteria": call("run-criteria", link),
                "estimate-task-time": call("estimate-task-time", link), "backtest-estimate": call("backtest-estimate", "--tasks", link)}
    refused = {name: done.returncode != 0 and board in done.stderr and "Traceback" not in done.stderr and (link in done.stderr or name != "check-criteria --task")
               and (done.returncode == 2 or name.split()[0] in ("check-criteria", "run-criteria")) for name, done in refusals.items()}
    refusals["depend"] = use("depend", mine, "--depends", link)
    refused["depend"] = refusals["depend"].returncode == 2 and board in refusals["depend"].stderr
    own = task.stdout.strip()
    listed, checked = call("list-additions", own), call("check-criteria", "--task", own, body)
    missing, scored = call("check-criteria", "--task", own, work / "missing.md"), call("backtest-estimate", "--as-of", "2030-01-01", "--tasks", own)
    step("callers", all(refused.values()) and ref() == before and listed.returncode == 0 and listed.stdout.startswith(f"#{mine} body sha: ")
         and checked.returncode == 0 and not checked.stderr and missing.returncode != 0 and "is no file here" in missing.stderr
         and scored.returncode == 0 and "the 1 scored tasks left out" in scored.stdout,
         [(name, done.returncode, done.stderr[-300:]) for name, done in refusals.items() if not refused[name]]
         + [listed.stdout, listed.stderr, checked.returncode, checked.stderr, missing.stderr, scored.stdout, scored.stderr])

    parse_case(step, box, repository, mine)
    before = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    noted = use("comment", mine, "--reported", "a probe note")
    after = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    common = box.git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=repository).strip()
    expected = "git+file://" + urllib.parse.quote(f"{common}/{REF}/{SCOPE}/{mine}") + "#comment-1"
    shown = box.evaluate(f"import board, json; print(json.dumps(board.fresh({mine})['comments'][0]))", cwd=repository)
    step("scoped-comment", noted.stdout.strip() == expected == shown["url"] and before <= shown["created"] <= after, f"printed {noted.stdout!r}, expected {expected}, stored {shown}")

    asked = use("comment", mine, "--blocked", "which way?").stdout.strip()
    first = use("decide", mine, "--decision", "go left.", "--by", "probe-manager").stdout.strip()
    right = use("decide", mine, "--decision", "go right.", "--by", "probe-manager", "--supersedes", first).stdout.strip()
    use("decide", mine, "--decision", "ask nobody.", "--by", "probe-manager", "--answers", asked)
    wish = "The probe keeps its output short"
    owner = use("decide", mine, "--decision", f"{wish}.", "--text", replay_probe.write_text(work, "owner.md", f"> {wish}.\n"), "--by", "owner")
    owned = owner.stdout.strip()
    sha = call("list-additions", mine).stdout.split("body sha: ", 1)[-1].split("\n", 1)[0]
    folded = use("edit", mine, "--body", replay_probe.write_text(work, "folded.md", replay_probe.BODY + f"2. [check] **{wish}**: `basename PASS` prints `PASS`; on base `FAIL`.\n"),
                 "--reason", f"folds {owned}", "--base", sha)
    box.git("fetch", "-q", str(repository), f"{REF}:{REF}", cwd=copy)
    read = use("read", mine, cwd=copy).stdout
    additions = call("list-additions", mine, cwd=copy)
    step("moved", folded.returncode == 0 and "binding decisions: 3" in read and "open questions: 0" in read
         and "go left" not in read.split("binding decisions")[1].split("open questions")[0] and "owner additions not in the body: 0" in additions.stdout,
         [owner.stderr, folded.stderr, read, additions.stdout, additions.stderr])
    gaps_case(step, use, mine, right, owned, ref, box, copy)
    parent_case(step, use, call, ref, number, mine, link, board, work, box, repository)
    return cases.finish()


def as_decider(box, argv):
    """(ARGV without its `--by <name>`, the `run` options of that decider's session, the owner's words added as `box.decider` gives them, which replace
    any `--text`, since the gate reads every `>` line as the owner's); ARGV as it is with no `--by`."""
    argv = [str(word) for word in argv]
    if "--by" not in argv:
        return argv, {}
    k = argv.index("--by")
    by, argv = argv[k + 1], argv[:k] + argv[k + 2:]
    if by == "owner" and "--text" in argv:
        k = argv.index("--text")
        argv = argv[:k] + argv[k + 2:]
    session, said = box.decider(by, argv[argv.index("--decision") + 1] if by == "owner" else "")
    return argv + said, session


def parse_case(step, box, repository, mine):
    common = box.git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=repository).strip()
    task = "git+file://" + urllib.parse.quote(f"{common}/{REF}/{SCOPE}/{mine}")
    root = "git+file://" + urllib.parse.quote(f"{common}/{REF}/5")
    texts = ["7", "#7", task, task + "#comment-2", root, task + "?x=1", task + "#notes", task.rsplit("/", 1)[0] + "/notes", "go left", "notes",
             "git+file:///tmp/a b/1", f"https://example.com/{REF}/1", "git+file:///tmp/nothing/1", "http://[abc", " 1 ", "1\n", urllib.parse.unquote(task), task + "\t", task + "\n", " " + task, "\x0c" + task, task + "\x01#comment-2"]
    code = ("import board_refs, json, sys\nout = []\nfor text in sys.argv[1:]:\n    try:\n        ref = board_refs.TaskRef.parse(text)\n"
            "        out.append([ref.scope, ref.number, ref.comment])\n    except board_refs.Refused as e:\n        out.append(str(e))\nprint(json.dumps(out))")
    found = box.evaluate(code, *texts, cwd=repository)
    read = box.evaluate("import board_refs, json, sys; print(json.dumps([board_refs.stored(text) for text in [*sys.argv[1:], None]]))",
                        task, urllib.parse.unquote(task) + "#comment-2", "go left", cwd=repository)
    link, none = "is no task link of this board: it ends `<scope>/<n>` or `<scope>/<n>#comment-<k>`", "names no task; give its number or its url"
    here = f", not to this board, which is {common}"
    step("parse", found == [[None, 7, None], [None, 7, None], [SCOPE, mine, None], [SCOPE, mine, 2], ["", 5, None], link, link, link, none, none, "belongs to git+file" + here,
                            "belongs to example.com" + here, "belongs to git+file" + here, none, none, none, [SCOPE, mine, None], none, none, none, none, none]
         and read == [[mine, 0], [mine, 2], [0, "go left"], [0, ""]], [found, read])


def gaps_case(step, use, mine, right, owned, ref, box, copy):
    def moved(url):
        """URL, a link the first checkout wrote, as this checkout names it, since `decide` refuses a link of another board."""
        return url.replace(urllib.parse.quote("spaced repo"), urllib.parse.quote("moved copy"))

    def decide(*argv):
        return use("decide", mine, *argv, cwd=copy).stdout.strip()

    north = decide("--decision", "go north.", "--by", "probe-manager")
    south = decide("--decision", "go south.", "--by", "probe-worker", "--supersedes", north)
    decide("--decision", "go west.", "--by", "probe-manager", "--supersedes", urllib.parse.unquote(south))
    shorter = decide("--decision", "take the short path.", "--by", "probe-worker")
    decide("--decision", "take the long path.", "--by", "probe-worker", "--supersedes", shorter)
    up = decide("--decision", "go up.", "--by", "probe-manager", "--supersedes", moved(right))
    down = decide("--decision", "go down.", "--by", "probe-manager", "--supersedes", urllib.parse.unquote(moved(right)))
    colour = use("comment", mine, "--blocked", "which colour?", "--asks", "owner", "--option", "red", "--option", "blue", cwd=copy).stdout.strip()
    use("comment", mine, "--blocked", "which size?", cwd=copy)
    use("comment", mine, "--blocked", "which size?", cwd=copy)
    body = replay_probe.write_text(copy, "other.md", replay_probe.BODY)
    (copy / SCOPE).mkdir()  # a part is filed in its parent's folder, which this checkout must hold
    other = int(use("file", "--title", "Probe a part of it", "--body", body, "--parent", mine, cwd=copy).stdout.strip().rsplit("/", 1)[1])
    elsewhere = use("comment", other, "--blocked", "which day?", cwd=copy).stdout.strip()
    held = ref(copy)
    refusals = [use("decide", mine, "--decision", "pick red.", "--by", "probe-manager", *argv, cwd=copy) for argv in (
        ("--answers", urllib.parse.unquote(colour)), ("--answers", urllib.parse.unquote(moved(right))), ("--answers", elsewhere),
        ("--supersedes", urllib.parse.unquote(colour)), ("--supersedes", urllib.parse.unquote(moved(owned))), ("--answers", right), ("--supersedes", right))]
    said = ["asks the owner, so only a decision `--by owner`", "which is no question on", f"post the decision on #{other}, the question's own task",
            "which is no decision in", "was decided by the owner, so only a decision `--by owner`", "belongs to the board of", "belongs to the board of"]
    refused = [done.returncode == 2 and words in done.stderr for done, words in zip(refusals, said)] + [ref(copy) == held]
    again = use("decide", mine, "--decision", "keep it shorter still.", "--text", replay_probe.write_text(copy, "again.md", "> keep it shorter still.\n"),
                "--by", "owner", "--supersedes", urllib.parse.unquote(moved(owned)), cwd=copy)
    binding = use("read", mine, cwd=copy).stdout.split("binding decisions", 1)[-1].split("open questions", 1)[0]
    refused += [again.returncode == 0, "keep it shorter still" in binding, "go west" in binding]
    found = box.evaluate(f"import board, decisions, json; node = board.fresh({mine}); print(json.dumps([decisions.gaps([node]), decisions.shown(node, decisions.superseded_in([node]))]))", cwd=copy)
    lines, shown = found
    twice = [line for line in lines if line.startswith("superseded twice")]
    decided = [entry["decision"] for entry in shown["decided"]]
    step("moved-gaps", all(refused) and twice == [f"superseded twice #{mine}: {moved(right)} is superseded by {up} and {down}; keep one by a decision that supersedes the other"]
         and "go west." in decided and "take the long path." in decided and not any(word in decided for word in ("go left.", "go right.", "take the short path.", "go north.", "go south."))
         and shown["questions"][-3:] == ["which colour?", "which size?", "which size?"] and shown["team_questions"] == [len(shown["questions"]) - 2, len(shown["questions"]) - 1]
         and shown["options"][-3:] == [["red", "blue"], [], []], [refused, [done.stderr for done in refusals], again.stderr, found])


def parent_case(step, use, call, ref, number, mine, link, board, work, box, repository):
    fence = "~~~\n## another example\n~~~\n\n```\n## an example\n1. an item\n```\n"
    parent_body = replay_probe.BODY.replace("## Definition of done\n\n", f"## Definition of done\n\n{fence}\n") + "\n## Notes\n\nA tail.\n"
    parent = number(use("file", "--title", "Probe a parent", "--body", replay_probe.write_text(work, "parent.md", parent_body), "--scope", SCOPE, "--label", "probe").stdout)
    use("hold", parent, "--holders", "probe-worker")
    wish = "The parent keeps its parts small"
    use("decide", parent, "--decision", f"{wish}.", "--text", replay_probe.write_text(work, "wish.md", f"> {wish}.\n"), "--by", "owner")
    commits = lambda: int(box.git("rev-list", "--count", REF, cwd=repository))
    before = commits()
    done = box.python(USE, "file", "--title", "Probe a part", "--body", replay_probe.write_text(work, "part.md", replay_probe.BODY), "--parent", parent, "--depends", mine,
                      cwd=repository, pane="w1:p1")
    count = commits()
    part = number(done.stdout) if done.returncode == 0 else 0  # two commits: the part with its `[task]` line, then the hold its filer's holding gives it

    def record(task):
        return box.evaluate(f"import board, json, record_types, task_state; task = board.fresh({task}); print(json.dumps([task['body'], record_types.shown(task['comments'][-1]) if task['comments'] else '', "
                            f"task['scope'], task['labels'], task['depends'], task_state.holder_values(task)]))", cwd=repository)

    found = record(parent) + record(part)[2:] if part else None
    expected = parent_body.replace("\n\n## Notes", f"\n2. [task] #{part} Probe a part\n\n## Notes")
    additions = call("list-additions", part).stdout if part else ""
    use("decide", part, "--decision", "keep the part tiny.", "--by", "probe-manager")
    binding = use("read", parent).stdout.split("binding decisions", 1)[-1].split("open questions", 1)[0]
    filed = (bool(found) and found[0] == expected and "\n````diff\n" in found[1] and found[6:10] == [SCOPE, ["probe"], [mine], [["probe-worker"]]]
             and count == before + 2 and "owner additions not in the body: 0" in additions and wish in binding and "keep the part tiny" not in binding)
    last = number(use("file", "--title", "Probe a last parent", "--body", replay_probe.write_text(work, "last.md", replay_probe.BODY.rstrip("\n"))).stdout)
    labelled = use("file", "--title", "Probe a labelled part", "--body", replay_probe.write_text(work, "labelled.md", replay_probe.BODY), "--parent", last, "--label", "other")
    tail = record(last) + record(number(labelled.stdout))[3:4] if labelled.returncode == 0 else None
    ended = bool(tail) and tail[0] == replay_probe.BODY.rstrip("\n") + f"\n2. [task] #{number(labelled.stdout)} Probe a labelled part\n" and tail[6] == ["other"]
    held = ref()
    lost = replay_probe.write_text(work, "lost.md", replay_probe.BODY)
    missing, foreign, scoped = (use("file", "--title", "Probe a lost part", "--body", lost, "--parent", target, *extra)
                                for target, extra in ((9999, ()), (link, ()), (parent, ("--scope", SCOPE))))
    step("parent", filed and ended and missing.returncode != 0 and "does not hold" in missing.stderr
         and foreign.returncode == 2 and board in foreign.stderr and scoped.returncode == 2 and "`--scope` goes" in scoped.stderr and ref() == held,
         [done.returncode, done.stderr, found, expected, additions, labelled.stderr, tail, missing.stderr, foreign.stderr, scoped.stderr])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
