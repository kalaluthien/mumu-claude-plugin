#!/usr/bin/env python3
"""Play one task's round on a temporary git board, its two workers live in a fake herdr, every datum passed as an option: the manager files and routes a root, a worker files a part that
waits on another, asks the owner a question with options, the manager answers it, the worker hands the task on, and a judge reads it. Print
`ok <case>` or `fail <case>: <detail>` per case, then the round's cost, and exit 1 on any failure:
- `calls`: each of the round's writes is one call that exits 0 and prints a url, the task named by its number or by that url;
- `stored`: every comment the round wrote is a `.json` whose keys board-record-schema.json names, and no text holds a data fence;
- `read`: one `read` prints the task's holders, the task it waits on, the decision that binds it from its root, and the open question with its options numbered;
- `answered`: after the answer the question is closed and the answer binds; a judge's read shows no question;
- `prose-lines`: a text whose lines open `depends on:`, `holders:` or `asks:` posts as prose and changes no holder and no wait;
- `unread`: a verb given a word that is neither a task's number nor its url prints the usage and exits 2, with no traceback;
- `refused`: a `--text` that carries a `teamwork` or `decision` fence posts nothing and names the option to use, so does an empty or two-line `--blocked`, `--reported`, `--decision` or `--summary`, a `--text` that opens with a keyword, an empty body on `file`, an empty title, an `edit` that leaves the body empty or whose `--reason` opens `DECIDED:` or holds two lines, or a field the schema refuses;
- `pane`: the task pane's listing draws the round's holder and its decisions;
- `cost`: the round takes fewer calls and fewer written characters than MAIN_ROUND, the same round written as fences and read with `list-decisions.py`;
- `no-fence-reader`: `list-decisions.py` and `legacy_records.py` are gone, and no code or playbook names a data fence or a decision key.

usage: replay-task-round.py"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
SCHEMA = json.loads((ROOT / "skills" / "kick-off" / "assets" / "board-record-schema.json").read_text())
BODY = ("{summary}## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints ok; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints ok when it runs**: `basename PASS` prints `PASS`; on base `FAIL`.\n")
# the same round at main's 7d2370dd: fences typed into each text, and `list-decisions.py` after each `read`
MAIN_ROUND = {"calls": 15, "written": 1490}
OLD_WORDS = ("```teamwork", "```decision", "decided by:", "door:", "list-decisions")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("task-round-") as work:
        # live, since the pane draws only a holder herdr lists
        return replay(replay_probe.Sandbox(work, [replay_probe.agent("probe-worker", 2), replay_probe.agent("second-worker", 3)]))


def replay(sandbox):
    work, cases = sandbox.work, replay_probe.Cases()
    cost = {"calls": 0, "written": 0, "read": 0}

    def use(*argv, text=None):
        """One call, TEXT written to the file its `<file>` word names, a decision `--by owner` run as the manager the owner typed its words to; (exit, stdout, stderr)."""
        if text is not None:
            (work / "text.md").write_text(text)
            cost["written"] += len(text)
        done = sandbox.python(USE, *[str(work / "text.md") if word == "<file>" else str(word) for word in argv], **(owner if "--by" in argv else {}))
        cost["calls"] += 1
        return done.returncode, done.stdout.strip(), done.stderr

    owner = sandbox.session("probe-manager", "make it print ok", "the first one, lower case")
    git = sandbox.git
    round_calls = [
        (("file", "--title", "Print ok from the probe", "--body", "<file>"), BODY.format(summary="The probe prints ok.\n\n")),
        (("file", "--title", "Ship the first half", "--body", "<file>"), BODY.format(summary="")),
        (("file", "--title", "Ship the second half", "--body", "<file>", "--depends", "2"), BODY.format(summary="")),
        (("decide", "1", "--decision", "the probe prints ok in two halves.", "--owner-said", "<file>", "--by", "owner", "--holders", "probe-worker"), "make it print ok\n"),
        (("comment", "3", "--blocked", "which case does the probe print?", "--asks", "owner", "--option", "print it in lower case", "--option", "print it in capitals"), None),
        (("hold", "3", "--holders", "second-worker"), None),
    ]
    answers = [use(*argv, text=text) for argv, text in round_calls]
    cases.step("calls", all(code == 0 and "teamwork-blackboard" in out for code, out, _ in answers), answers)
    root, question = answers[0][1], answers[4][1]
    # the root gains its parts by an edit, whose base is the sha `read` prints
    listed = use("read", "1")[1]
    sha = next(line.split(": ", 1)[1] for line in listed.splitlines() if line.startswith("body sha: "))
    (work / "new.md").write_text(BODY.format(summary="The probe prints ok.\n\n") + "2. [task] #2 Ship the first half\n3. [task] #3 Ship the second half\n")
    edited = use("edit", root, "--body", work / "new.md", "--reason", "adds the two halves as parts.", "--base", sha)
    cases.step("calls", edited[0] == 0, edited)

    tree = git("ls-tree", "-r", "--name-only", "refs/teamwork-blackboard").split()
    notes = [path for path in tree if "/comments/" in path]
    stored = [json.loads(git("show", f"refs/teamwork-blackboard:{path}")) for path in notes if path.endswith(".json")]
    cases.step("stored", len(stored) == len(notes) >= 4 and all(set(note) <= set(SCHEMA["definitions"]["comment"]["properties"]) and "```teamwork" not in note["text"] and "```decision" not in note["text"] for note in stored), notes)

    code, shown, _ = use("read", question.split("#")[0])
    cost["read"] += len(shown)
    wanted = ("holders: second-worker", "depends: #2", "waits on the owner", "- #1 owner: the probe prints ok in two halves.", "open questions: 1", "to the owner: which case does the probe print?",
              "1. print it in lower case", "2. print it in capitals")
    cases.step("read", code == 0 and all(word in shown for word in wanted), [word for word in wanted if word not in shown] + [shown])

    answered = use("decide", question.split("#")[0], "--decision", "the probe prints ok in lower case.", "--owner-said", "<file>", "--by", "owner", "--answers", question,
                    text="the first one, lower case\n")
    after, judged = use("read", "3")[1], use("read", "3", "--as", "judge")[1]
    cases.step("answered", answered[0] == 0 and "open questions: 0" in after and "- #3 owner: the probe prints ok in lower case." in after
         and "open questions" not in judged and "BLOCKED:" not in judged and "binding decisions: 2" in judged, [answered, after])

    cases.step("cost", cost["calls"] < MAIN_ROUND["calls"] and cost["written"] < MAIN_ROUND["written"], cost)
    print(f"cost: {cost['calls']} calls against {MAIN_ROUND['calls']}, {cost['written']} characters written against {MAIN_ROUND['written']}, {cost['read']} characters in the one read")
    listing = sandbox.python(ROOT / "hooks" / "list-task-board.py", "", "--width", "80").stdout
    drawn = ("second-worker", "the probe prints ok in two halves.", "the probe prints ok in lower case.")
    cases.step("pane", all(word in listing for word in drawn), listing)
    bare_lines = use("comment", "3", "--reported", "a note on the order.", "--text", "<file>", text="depends on: #1\nholders: x-worker\nasks: owner\n")
    after_lines = use("read", "3")[1]
    cases.step("prose-lines", bare_lines[0] == 0 and "holders: second-worker" in after_lines and "depends: #2" in after_lines, [bare_lines, after_lines])
    before = git("rev-parse", "refs/teamwork-blackboard")
    needed = {"comment": ("--reported", "x"), "decide": ("--decision", "x"), "hold": ("--holders", "x"), "depend": ("--depends", "2"), "edit": ("--body", "<file>", "--reason", "x", "--base", "abc123"),
              "title": ("--title", "x"), "resolve": ("--summary", "x"), "reopen": (), "label": ("--label", "x")}
    unread = [use("read", "/tmp/1")] + [use(verb, "no-task", *options, text="Body.\n") for verb, options in needed.items()] + [use("read", "no-task")]
    cases.step("unread", all(code == 2 and not out and "usage: use-board.py" in err and "Traceback" not in err for code, out, err in unread), unread)
    fenced = [use("comment", "3", "--reported", "a note.", "--text", "<file>", text="```teamwork\nholders: x-worker\n```\n"),
              use("decide", "3", "--decision", "keep it.", "--text", "<file>", text="```decision\ndecision: keep it\ndecided by: probe-worker\ndoor: two-way\n```\n"),
              use("file", "--title", "Ship a third half", "--body", "<file>", text=BODY.format(summary="") + "\n```teamwork\ndepends on: #2\n```\n")]
    bare = [use(*argv) for line in ("", "  ", "a\nb") for argv in (("comment", "3", "--blocked", line), ("comment", "3", "--reported", line), ("decide", "3", "--decision", line), ("resolve", "2", "--summary", line))]
    bare += [use(*argv, "x", "--text", "<file>", text=text) for text in ("DECIDED: x\n", "REPORTED: x\n", "BLOCKED: x\n")
             for argv in (("comment", "3", "--reported"), ("decide", "3", "--decision"), ("resolve", "2", "--summary"))]
    bare += [use("file", "--title", "Ship a third half", "--body", "<file>", text=text) for text in ("", "\n")]
    bare += [use("hold", "3", "--holders", "Bad_Name"), use("comment", "3", "--blocked", "which one?", "--asks", "owner", "--option", "one", "--option", ""), use("title", "2", "--title", ""), use("title", "2", "--title", "  "),
             use("file", "--title", "", "--body", "<file>", text=BODY.format(summary=""))]
    (work / "new.md").write_text("")
    base = next(line.split(": ", 1)[1] for line in use("read", "2")[1].splitlines() if line.startswith("body sha: "))
    emptied = use("edit", "2", "--body", work / "new.md", "--reason", "drops the body.", "--base", base)
    bare.append((2 if emptied[0] else 0, *emptied[1:]))
    bare += [use("edit", "2", "--body", work / "new.md", "--reason", reason, "--base", base) for reason in ("DECIDED: drops the body.", "a\nb")]
    cases.step("refused", all(code == 2 and not out and "option" in err for code, out, err in fenced) and all(code == 2 and not out for code, out, _ in bare)
         and git("rev-parse", "refs/teamwork-blackboard") == before, fenced + bare)

    code = [path for folder in ("lib", "hooks", "monitors", "skills/kick-off/scripts") for path in (ROOT / folder).glob("*.py")]
    pages = [*(ROOT / "skills" / "kick-off").glob("*.md"), *(ROOT / "skills" / "kick-off" / "references").rglob("*.md")]
    named = [f"{path.name}: {word}" for path in code + pages for word in OLD_WORDS if word in path.read_text()]
    gone = [path.name for path in (ROOT / "skills" / "kick-off" / "scripts" / "list-decisions.py", ROOT / "lib" / "legacy_records.py") if path.exists()]
    cases.step("no-fence-reader", not named and not gone, named + gone)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
