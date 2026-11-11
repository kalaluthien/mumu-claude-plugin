#!/usr/bin/env python3
"""Play one task's round on a temporary git board, every datum passed as an option: the manager files and routes a root, a worker files a part that
waits on another, asks the owner a question with options, the manager answers it, the worker hands the task on, and a judge reads it. Print
`ok <case>` or `fail <case>: <detail>` per case, then the round's cost, and exit 1 on any failure:
- `calls`: each of the round's writes is one call that exits 0 and prints a url, the issue named by its number or by that url;
- `stored`: every comment the round wrote is a `.json` whose keys board-record-schema.json names, and no text holds a data fence;
- `read`: one `read` prints the task's holders, the task it waits on, the decision that binds it from its root, and the open question with its options numbered;
- `answered`: after the answer the question is closed and the answer binds; a judge's read shows no question;
- `prose-lines`: a text whose lines open `depends on:`, `holders:` or `asks:` posts as prose and changes no holder and no wait;
- `unread`: a verb given a word that is neither a task's number nor its url prints the usage and exits 2, with no traceback;
- `refused`: a text that carries a `teamwork` or `decision` fence posts nothing and names the option to use, an empty or keyword-only text posts nothing on `comment`, `decide`, `resolve` and `file`, nor does an empty title, an `edit` that leaves the body empty or a field the schema refuses;
- `older`: a comment written as text with fences, as records before the fields were, still gives its holder and its decision;
- `pane`: the issue pane's listing draws the round's holder and its decisions;
- `cost`: the round takes fewer calls and fewer written characters than MAIN_ROUND, the same round written as fences and read with `list-decisions.py`;
- `one-reader`: `list-decisions.py` is gone, only `legacy_records.py` holds a data fence's pattern, and no playbook names a fence, a decision key or that script.

usage: replay-task-round.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
SCHEMA = json.loads((ROOT / "skills" / "kick-off" / "assets" / "board-record-schema.json").read_text())
BODY = ("{summary}## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints ok; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints ok when it runs**: `echo ok` prints `ok`; on base nothing.\n")
OLDER = "DECIDED: older-worker holds this.\n\n```decision\ndecision: keep the older record readable\ndecided by: owner\ndoor: two-way\n```\n\n```teamwork\nholders: older-worker\n```\n"
# the same round at main's 7d2370dd: fences typed into each text, and `list-decisions.py` after each `read`
MAIN_ROUND = {"calls": 15, "written": 1490}
OLD_WORDS = ("```teamwork", "```decision", "decided by:", "door:", "list-decisions")
failed = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {str(detail).strip()[-600:]}", flush=True)
    if not ok:
        failed.append(name)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="task-round-"))
    repository = work / "repo"
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    os.environ.update(HOME=str(work), CLAUDE_CONFIG_DIR=str(work / "home"), GIT_AUTHOR_NAME="probe", GIT_AUTHOR_EMAIL="probe@example.com",
                      GIT_COMMITTER_NAME="probe", GIT_COMMITTER_EMAIL="probe@example.com")
    cost = {"calls": 0, "written": 0, "read": 0}

    def use(*argv, text=None):
        """One call, TEXT written to the file its `<file>` word names; (exit, stdout, stderr)."""
        if text is not None:
            (work / "text.md").write_text(text)
            cost["written"] += len(text)
        done = subprocess.run([sys.executable, str(USE), *[str(work / "text.md") if word == "<file>" else str(word) for word in argv]], cwd=repository, capture_output=True, text=True)
        cost["calls"] += 1
        return done.returncode, done.stdout.strip(), done.stderr

    def git(*argv):
        return subprocess.run(["git", *argv], cwd=repository, capture_output=True, text=True, check=True).stdout

    round_calls = [
        ("file", "Print ok from the probe", "<file>", BODY.format(summary="The probe prints ok.\n\n")),
        ("file", "Ship the first half", "<file>", BODY.format(summary="")),
        ("file", "Ship the second half", "<file>", "--depends", "2", BODY.format(summary="")),
        ("decide", "1", "<file>", "--by", "owner", "--holders", "probe-worker", 'DECIDED: the probe prints ok in two halves.\n\nOwner said: "make it print ok".\n'),
        ("comment", "3", "<file>", "--asks", "owner", "--option", "print it in lower case", "--option", "print it in capitals", "BLOCKED: which case does the probe print?\n"),
        ("hold", "3", "second-worker"),
    ]
    answers = []
    for *argv, last in round_calls:
        answers.append(use(*argv, text=last) if "<file>" in argv else use(*argv, last))
    step("calls", all(code == 0 and "teamwork-blackboard" in out for code, out, _ in answers), answers)
    root, question = answers[0][1], answers[4][1]
    # the root gains its parts by an edit, whose base is the sha `read` prints
    listed = use("read", "1")[1]
    sha = next(line.split(": ", 1)[1] for line in listed.splitlines() if line.startswith("body sha: "))
    (work / "old.md").write_text(BODY.format(summary="The probe prints ok.\n\n"))
    (work / "new.md").write_text(BODY.format(summary="The probe prints ok.\n\n") + "2. [task] #2 Ship the first half\n3. [task] #3 Ship the second half\n")
    diff = subprocess.run(["diff", "-u", str(work / "old.md"), str(work / "new.md")], capture_output=True, text=True).stdout
    (work / "parts.diff").write_text(diff)
    edited = use("edit", root, work / "parts.diff", "DECIDED: adds the two halves as parts.", "--base", sha)
    step("calls", edited[0] == 0, edited)

    tree = git("ls-tree", "-r", "--name-only", "refs/teamwork-blackboard").split()
    notes = [path for path in tree if "/comments/" in path]
    stored = [json.loads(git("show", f"refs/teamwork-blackboard:{path}")) for path in notes if path.endswith(".json")]
    step("stored", len(stored) == len(notes) >= 4 and all(set(note) <= set(SCHEMA["properties"]) and "```teamwork" not in note["text"] and "```decision" not in note["text"] for note in stored), notes)

    code, shown, _ = use("read", question.split("#")[0])
    cost["read"] += len(shown)
    wanted = ("holders: second-worker", "depends: #2", "waits on the owner", "- #1 owner: the probe prints ok in two halves.", "open questions: 1", "to the owner: which case does the probe print?",
              "1. print it in lower case", "2. print it in capitals")
    step("read", code == 0 and all(word in shown for word in wanted), [word for word in wanted if word not in shown] + [shown])

    answered = use("decide", question.split("#")[0], "<file>", "--by", "owner", "--answers", question, text='DECIDED: the probe prints ok in lower case.\n\nOwner said: "the first one, lower case".\n')
    after, judged = use("read", "3")[1], use("read", "3", "--as", "judge")[1]
    step("answered", answered[0] == 0 and "open questions: 0" in after and "- #3 owner: the probe prints ok in lower case." in after
         and "open questions" not in judged and "BLOCKED:" not in judged and "binding decisions: 2" in judged, [answered, after])

    step("cost", cost["calls"] < MAIN_ROUND["calls"] and cost["written"] < MAIN_ROUND["written"], cost)
    print(f"cost: {cost['calls']} calls against {MAIN_ROUND['calls']}, {cost['written']} characters written against {MAIN_ROUND['written']}, {cost['read']} characters in the one read")
    listing = subprocess.run([sys.executable, str(ROOT / "hooks" / "list-issue-board.py"), "", "--width", "80"], cwd=repository, capture_output=True, text=True).stdout
    drawn = ("second-worker", "the probe prints ok in two halves.", "the probe prints ok in lower case.")
    step("pane", all(word in listing for word in drawn), listing)
    bare_lines = use("comment", "3", "<file>", text="REPORTED: a note on the order.\n\ndepends on: #1\nholders: x-worker\nasks: owner\n")
    after_lines = use("read", "3")[1]
    step("prose-lines", bare_lines[0] == 0 and "holders: second-worker" in after_lines and "depends: #2" in after_lines, [bare_lines, after_lines])
    before = git("rev-parse", "refs/teamwork-blackboard")
    unread = [use("read", "/tmp/1")] + [use(verb, "no-issue", "<file>", "word") for verb in ("read", "comment", "decide", "hold", "depend", "edit", "title", "resolve", "reopen", "label")]
    step("unread", all(code == 2 and not out and "usage: use-board.py" in err and "Traceback" not in err for code, out, err in unread), unread)
    fenced = [use("comment", "3", "<file>", text="REPORTED: a note.\n\n```teamwork\nholders: x-worker\n```\n"),
              use("decide", "3", "<file>", "--by", "probe-worker", text="DECIDED: keep it.\n\n```decision\ndecision: keep it\ndecided by: probe-worker\ndoor: two-way\n```\n"),
              use("file", "Ship a third half", "<file>", text=BODY.format(summary="") + "\n```teamwork\ndepends on: #2\n```\n")]
    bare = [use(*argv, text=text) for text in ("", "\n", "DECIDED:\n", "REPORTED: \n", "BLOCKED:")
            for argv in (("comment", "3", "<file>"), ("decide", "3", "<file>", "--by", "probe-worker"), ("resolve", "2", "<file>"), ("file", "Ship a third half", "<file>"))]
    bare += [use("hold", "3", "Bad_Name"), use("comment", "3", "<file>", "--asks", "owner", "--option", "one", "--option", "", text="BLOCKED: which one?\n"), use("title", "2", ""), use("title", "2", "  "), use("file", "", "<file>", text=BODY.format(summary=""))]
    second = BODY.format(summary="")
    (work / "old.md").write_text(second)
    (work / "new.md").write_text("")
    (work / "empty.diff").write_text(subprocess.run(["diff", "-u", str(work / "old.md"), str(work / "new.md")], capture_output=True, text=True).stdout)
    emptied = use("edit", "2", work / "empty.diff", "DECIDED: drops the body.")
    bare.append((2 if emptied[0] else 0, *emptied[1:]))
    step("refused", all(code == 2 and not out and "option" in err for code, out, err in fenced) and all(code == 2 and not out for code, out, _ in bare)
         and git("rev-parse", "refs/teamwork-blackboard") == before, fenced + bare)

    sys.path.insert(0, str(ROOT / "lib"))
    import decisions
    import issue_state
    older = {"number": 9, "body": "A body.\n\n```teamwork\ndepends on: #2\n```\n", "trusted": True, "parent": None, "state": "OPEN",
             "comments": [{"body": OLDER, "url": "x#comment-1", "createdAt": "2026-11-06T00:00:00Z", "trusted": True}]}
    import task_links
    found = decisions.typed(9, older)
    step("older", issue_state.compose(older)["holders"] == ["older-worker"] and [decision["decision"] for decision in found] == ["keep the older record readable"]
         and found[0]["role"] == "owner" and task_links.depends(older) == [2], [issue_state.compose(older), found])

    code = [path for folder in ("lib", "hooks", "monitors", "skills/kick-off/scripts") for path in (ROOT / folder).glob("*.py") if path.name != "legacy_records.py"]
    pages = [*(ROOT / "skills" / "kick-off").glob("*.md"), *(ROOT / "skills" / "kick-off" / "references").rglob("*.md")]
    named = [f"{path.name}: {word}" for path in code + pages for word in OLD_WORDS if word in path.read_text() and not (word == "```decision" and path.name == "issue_state.py")]
    step("one-reader", not named and not (ROOT / "skills" / "kick-off" / "scripts" / "list-decisions.py").exists(), named)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
