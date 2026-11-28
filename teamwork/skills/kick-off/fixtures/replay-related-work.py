#!/usr/bin/env python3
"""Replay a worker's read of a task on a scratch repository with a git board, written only through use-board.py, and print `ok <case>` or
`fail <case>: <what it saw>` per case, then `PASS` or `FAIL`; exit 1 on any fail:
- linked-first: the task's parent, a sibling part and a task it waits on come first, newest first, each with its state: open, completed or stopped;
- file-commits: tasks whose commits, marked `(task <n>)` or `(#<n>)` in the subject, touched a file the task names come next, newest task first
  whatever the commits' order, each naming that file; a linked task whose commits touched it too is listed once;
- named-files: in a task scoped to a folder, a name that ends one file's path under the folder names it, a name that ends two names none, a name
  that ends a path in a sibling folder sharing the scope's prefix is not under the folder, a path from the root names its file, a backticked command
  names its first word's file, and a file named twice is listed once; in a root task a name ends any path, and its own part is listed;
- five-tasks: of more than five related tasks the read lists five, so a task sharing two title words is left out after them;
- title-words: a task with no link and no named file lists the tasks sharing two of its title words, digits counting as words, newest first,
  counting them, with no commit line, none sharing one or only stop words, and says it names no tracked file;
- two-decisions: a listed task shows its latest decision, cut to 120 characters, and the newest that reversed an earlier one, naming the comment it
  reversed, and no other;
- thirty-days: of the commits on the named files, the read lists the newest five from the last 30 days, each with its sha, and none older; a task
  whose named file has none says so, and one with nothing related says that;
- board-and-git: the reads call no `gh`;
- worker-only: a read as judge, or with no role, prints no related work.

usage: replay-related-work.py"""
import datetime
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

USE = HERE.parent / "scripts" / "use-board.py"
HEADER = "related work, from the board and git log:"
LATEST = "the latest word " + "extraordinarily " * 10 + "end"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("related-work-") as work:
        sandbox = replay_probe.Sandbox(work)
        now = datetime.datetime.now(datetime.timezone.utc)

        def use(*argv, **options):
            done = sandbox.python(USE, *map(str, argv), **options)
            if done.returncode:
                raise SystemExit(f"replay-related-work: use-board.py {' '.join(map(str, argv[:2]))} failed: {done.stderr}")
            return done.stdout.strip()

        def file(title, text="", depends=(), scope=None, part=None):
            body = f"## Goal\n\nProbe related work. {text}\n\nPath: caller: the probe run; meets: the owner\n\n## Definition of done\n\n{replay_probe.CHECK}"
            if part:
                body = body.replace(replay_probe.CHECK.strip(), f"{replay_probe.CHECK.strip()}\n2. [task] #{part} Probe a root part")
            url = use("file", "--title", title, "--body", replay_probe.write_text(sandbox.work, "body.md", body), "--depends", " ".join(map(str, depends)),
                      *(["--scope", scope] if scope else []))
            return int(url.rsplit("/", 1)[1])

        def decide(number, decision, supersedes=""):
            session, said = sandbox.decider("probe-manager")
            return use("decide", number, "--decision", decision, *said, *(["--supersedes", supersedes] if supersedes else []), **session)

        def commit(path, subject, days):
            target = sandbox.repository / path
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a") as handle:
                handle.write(subject + "\n")
            sandbox.clock((now - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ"))
            sandbox.git("add", path)
            sandbox.git("commit", "-q", "-m", subject)
            sandbox.clock(None)

        def read(number, *role):
            done = sandbox.python(USE, "read", number, *role)
            return done.stdout.split(HEADER, 1)[-1] if done.returncode == 0 and HEADER in done.stdout else f"no block: {done.stdout[-300:]} {done.stderr}"

        def listed(block):
            return [int(n) for n in re.findall(r"^- #(\d+) ", block, re.M)]

        for path in ("pkg/tool.py", "pkg/docs/notes.md", "other/docs/notes.md", "pkg/a/same.md", "pkg/b/same.md", "old.py", "lib/deep.py", "pkgx/tool.py"):
            commit(path, f"Begin {path}", 40)
        waited = file("Probe the awaited thing")
        older_words = file("Measure gizmo speed")
        touch_old = file("Probe an older code toucher")
        touch_new = file("Probe the code toucher")
        two_words = file("Measure 2026 spinning")
        stop_only = file("Read the list of pumps")
        one_word = file("Measure nothing else")
        task = file("Measure gizmo latency", "Run `tool.py --fast`, change `docs/notes.md`, again `docs/notes.md`, `same.md` and `other/docs/notes.md`.", depends=[waited], scope="pkg")
        sibling = file("Probe a sibling")
        parent = file("Probe the parent")
        parent_body = use("read", parent, "--body").replace(replay_probe.CHECK.strip(), f"{replay_probe.CHECK.strip()}\n2. [task] #{task} Measure gizmo latency\n3. [task] #{sibling} Probe a sibling")
        use("edit", parent, "--body", replay_probe.write_text(sandbox.work, "parent.md", parent_body + "\n"), "--reason", "add parts",
            "--base", re.search(r"body sha: (\w+)", use("read", parent))[1])
        lonely = file("Probe lonely zebra", "Read `old.py`.")
        wide = file("Measure the speed of gizmo 2026 widths")
        root_part = file("Probe a root part")
        root_names = file("Probe root names", "Read `deep.py`.", part=root_part)

        first = decide(waited, "use the first way")
        second = decide(waited, "use the second way", supersedes=first)
        decide(waited, "a plain middle decision")
        decide(waited, "use the third way", supersedes=second)
        decide(waited, LATEST)

        commit("pkg/tool.py", f"Shape the tool (task {parent})", 10)
        for n, (path, days) in enumerate((("pkg/tool.py", 9), ("pkg/docs/notes.md", 8), ("other/docs/notes.md", 7), ("pkg/tool.py", 6), ("pkg/docs/notes.md", 5), ("pkg/tool.py", 4))):
            commit(path, f"Tune the tool {n} (task {touch_new})", days)
        commit("pkg/tool.py", f"Fix the tool (#{touch_old})", 3)
        commit("pkg/a/same.md", f"Change a same file (task {one_word})", 2)
        use("resolve", touch_old, "--summary", "done")
        use("resolve", sibling, "--summary", "stopped", "--not-planned")
        commit("lib/deep.py", "Deepen the library", 2)

        block = read(task, "--as", "worker")
        found = listed(block)
        heads = re.findall(r"^- #\d+ .*$", block, re.M)
        cases.step("linked-first", heads[:3] == [f"- #{parent} open: Probe the parent (its parent)", f"- #{sibling} stopped: Probe a sibling (a sibling part)",
                                                 f"- #{waited} open: Probe the awaited thing (a task it waits on)"], block)
        cases.step("file-commits", heads[3:] == [f"- #{touch_new} open: Probe the code toucher (its commits touched tool.py)",
                                                 f"- #{touch_old} completed: Probe an older code toucher (its commits touched tool.py)"], block)
        deep = read(root_names, "--as", "worker")
        cases.step("named-files", "commits in the last 30 days on tool.py, notes.md, notes.md:" in block and one_word not in found
                   and "commits in the last 30 days on deep.py:" in deep and f"- #{root_part} open: Probe a root part (its part)" in deep and "Deepen the library" in deep, block + deep)
        cases.step("five-tasks", len(found) == 5 and two_words not in found, block)
        titles = read(wide, "--as", "worker")
        cases.step("title-words", listed(titles) == [task, two_words, older_words] and stop_only not in listed(titles)
                   and f"- #{two_words} open: Measure 2026 spinning (shares 2 title words)" in titles
                   and not re.search(r"^- [0-9a-f]{7,} ", titles, re.M)
                   and f"- #{older_words} open: Measure gizmo speed (shares 3 title words)" in titles
                   and "commits: the body names no tracked file" in titles, titles)
        waited_lines = block.split(f"- #{waited} ", 1)[-1].split("\n- ", 1)[0].splitlines()[1:]
        reversed_comment = second.rsplit("#comment-", 1)[1]
        cases.step("two-decisions", waited_lines == [f"  DECIDED: use the third way (reverses #{waited} comment {reversed_comment})", "  DECIDED: " + LATEST[:120]], block)
        commits = re.findall(r"^- ([0-9a-f]{7,}) \S+ (.*)$", block, re.M)
        lone = read(lonely, "--as", "worker")
        cases.step("thirty-days", [subject for _, subject in commits] == [f"Fix the tool (#{touch_old})"] + [f"Tune the tool {n} (task {touch_new})" for n in (5, 4, 3, 2)]
                   and "Begin" not in block + lone and lone.strip().splitlines() == ["- no linked task, none whose commits touched a file it names, none sharing two title words",
                                                                                    "commits in the last 30 days on old.py:", "- none in the last 30 days"], block + lone)
        cases.step("board-and-git", not sandbox.gh_calls(), sandbox.gh_calls())
        others = read(task, "--as", "judge") + read(task)
        cases.step("worker-only", others.count("no block:") == 2, others)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
