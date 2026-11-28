#!/usr/bin/env python3
"""Convert a board in the form before records carry their kind by convert-records.py, and print `ok <case>` or `fail <case>: <what it saw>` per case,
then `PASS record migration` or `FAIL record migration`; exit 1 on any failure:
- `shapes`: old-board.json holds every shape count-record-shapes.py counts on this repository's board in the old form, its backup once converted;
- `refused`: a read of an old task, one with comments and one with none, exits 2 naming its task record and convert-records.py by a path that exists, and a
  read of a task in the new form whose comment is in the old form names that comment, as `refused-comment` once the board is converted;
- `converted`: convert-records.py converts the board, keeps the board as it was in its backup ref, and a second run finds nothing to convert;
- `authors`: a comment the own-reports file lists is by its scope's manager, one it does not list or of a task in no scope by `unknown`, one with `by` by that name, `again`
  becomes a ref, a keyword with no space after its colon makes a note, a comment its task keeps no time for takes the time of the commit that
  added it, and the conversion leaves the repository's own index as it was;
- `no-board`: in a repository with no board it prints `nothing to convert` and exits 0, `--help` prints its usage and exits 0, and a word it does not
  take exits 2;
- `unfit`: a board whose comment links a task alone, which no record's type takes, exits 1 naming the record and leaves the board as it was;
- `round-trip`: the board holds as many tasks and comments as before, and each record loads and dumps back to what is stored;
- `read`, `board`: `use-board.py read <n>`, plain and `--as worker`, of each task, and `list-task-board.py`, print what the code before the change printed
  of the old board, apart from what TABLE names; each side renders every task in one process, the code before the change taken from the commit before
  the one that added lib/record_types.py; `skip read, board` outside a git checkout, which holds no such commit;
- `backup-held`: with the backup ref naming another commit than the board's, convert-records.py exits 1 naming the ref and leaves the board as it was;
- `backup-same`: with the backup ref naming the board's own commit, it converts and leaves the backup ref where it was;
- `live`: a copy of this repository's board in the old form, its backup once converted, converts, and each of its records round-trips; `skip live: no ref`
  when the repository has no board.

usage: replay-record-migration.py"""
import io
import json
import pathlib
import re
import subprocess
import sys
import tarfile

HERE = pathlib.Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
sys.path.insert(0, str(PLUGIN / "lib"))
import iso_time  # noqa: E402
import replay_probe  # noqa: E402

SCRIPTS = HERE.parent / "scripts"
REF, BACKUP = "refs/teamwork-blackboard", "refs/teamwork-blackboard-backup/4"
# old-board.json's links name the checkout it was written in, which the new form stores as refs
OLD_URL = re.compile(r"git\+file:///old/checkout/\.git/refs/teamwork-blackboard/(?:[^\s;)#]*/)?(\d+)#comment-(\d+)")
NOTE = re.compile(r"^(?:DECIDED: )?\**Judge note:\**.*?(?=\n\s*\n|\n```|\Z)\s*", re.M | re.S)
LABEL = re.compile(r"^(?:DECIDED: )?\**Judge note:\**\s*")
STATES = {("OPEN", ""): "open", ("CLOSED", "COMPLETED"): "completed", ("CLOSED", "NOT_PLANNED"): "stopped"}


def relative(text):
    return OLD_URL.sub(lambda found: f"{found.group(1)}#comment-{found.group(2)}", text)


def moved_note(block):
    """A comment's text with its judge note paragraphs moved to its end, as `Judge note: <words>`, where the new form shows its field."""
    notes = [LABEL.sub("", found.group(0)).strip() for found in NOTE.finditer(block)]
    if not notes:
        return block
    kept = NOTE.sub(lambda found: "DECIDED:\n\n" if found.group(0).startswith("DECIDED: ") else "", block).rstrip("\n")
    return f"{kept}\n\nJudge note: {chr(10).join(notes)}\n" if block.endswith("\n") else f"{kept}\n\nJudge note: {chr(10).join(notes)}"


# what the new form prints otherwise, each a (name, change of the old code's output)
TABLE = [
    ("a task's state is open, completed or stopped", lambda text, state: re.sub(r"^state: (OPEN|CLOSED)", f"state: {state}", text, count=1, flags=re.M)),
    ("a binding decision names no door", lambda text, state: re.sub(r"^(- #\d+ [^:\n]*?), one-way:", r"\1:", text, flags=re.M)),
    ("a comment's fields hold no door", lambda text, state: re.sub(r"^(--- \S+ \()([^\n]*)\)$", lambda found: (found.group(1) + "; ".join(part for part in found.group(2).split("; ") if part != "one way") + ")")
                                                               if found.group(2) != "one way" else found.group(1)[:-2], text, flags=re.M)),
    ("a binding line's list of answers is refs, not a Python list", lambda text, state: re.sub(r"^(- #\d+ .*; answers )\[([^\]\n]*)\]$", lambda found: found.group(1) + " ".join(
        part.strip("'") for part in found.group(2).split(", ")), text, flags=re.M)),
    ("a link in a comment's fields or a binding line is a ref", lambda text, state: re.sub(r"^((?:--- \S+ \(|- #\d+ .*?\(\S+\)).*)$", lambda found: relative(found.group(1)), text, flags=re.M)),
]


def normalised(text, state, worker):
    for _, change in TABLE:
        text = change(text, state)
    if worker:
        return text
    # a judge note leaves the text for its own field, which the new form prints after the text; the table cannot name it as one line
    head, *blocks = re.split(r"(?m)^(?=--- )", text)
    return head + "".join(moved_note(block.rstrip("\n")) + "\n" * (len(block) - len(block.rstrip("\n"))) for block in blocks)


RENDER = """import contextlib, importlib.util, io, json, sys
spec = importlib.util.spec_from_file_location("use_board", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
shown = {}
for number in sys.argv[2:]:
    for view in ([], ["--as", "worker"]):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            try:
                code = module.main(["read", number, *view])
            except SystemExit as e:
                code = e.code
        shown[" ".join([number, *view])] = [code, out.getvalue()]
print(json.dumps(shown))"""

LOADS = """import json, subprocess, sys
import record_types
ref = sys.argv[1]
paths = [path for path in subprocess.run(["git", "ls-tree", "-r", "--name-only", "-z", ref], capture_output=True, text=True, check=True).stdout.split("\\0")
         if path.endswith("/task.json") or "/comments/" in path]
# one batch read, since a read per record of a live board outlasts the run's limit
output = subprocess.run(["git", "cat-file", "--batch"], input="".join(f"{ref}:{path}\\n" for path in paths).encode(), capture_output=True, check=True).stdout
texts, at = [], 0
for _ in paths:
    header_end = output.index(b"\\n", at)
    size = int(output[at:header_end].split()[2])
    texts.append(output[header_end + 1:header_end + 1 + size].decode())
    at = header_end + 1 + size + 1
wrong, tasks, comments = [], 0, 0
for path, text in zip(paths, texts):
    stored = json.loads(text)
    kind = record_types.Task if path.endswith("/task.json") else record_types.Comment
    tasks, comments = tasks + (kind is record_types.Task), comments + (kind is record_types.Comment)
    if kind.load(stored, path).dump(path) != stored:
        wrong.append(path)
print(json.dumps([tasks, comments, wrong[:5]]))"""


def git(box, *argv, cwd=None, data=None):
    return box.run(["git", *argv], cwd=cwd, input=data).stdout


def seed(box, board, cwd=None):
    """BOARD, {path: record or text}, committed as the board ref of the repository at CWD."""
    lines = []
    for path, value in board.items():
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=1)
        lines.append(f"100644 blob {git(box, 'hash-object', '-w', '--stdin', cwd=cwd, data=text).strip()}\t{path}")
    index = {"GIT_INDEX_FILE": str(box.work / "seed-index")}
    (box.work / "seed-index").unlink(missing_ok=True)  # each seed holds BOARD alone, not the files an earlier seed added
    box.run(["git", "update-index", "--add", "--index-info"], cwd=cwd, input="".join(line.replace("100644 blob ", "100644 ") + "\n" for line in lines), **index)
    tree = box.run(["git", "write-tree"], cwd=cwd, **index).stdout.strip()
    git(box, "update-ref", REF, git(box, "commit-tree", tree, "-m", "seed the old board", cwd=cwd).strip(), cwd=cwd)


def loads(box, cwd=None):
    """[tasks, comments, the paths of up to 5 records that do not round-trip] of the board at CWD, read by the plugin's record_types; a failed read is one such path."""
    try:
        return box.evaluate(LOADS, REF, cwd=cwd)
    except RuntimeError as e:
        return [None, None, [str(e).splitlines()[-1]]]


def counts(box, cwd=None):
    names = git(box, "ls-tree", "-r", "--name-only", REF, cwd=cwd).split()
    return sum(name.endswith("/task.json") for name in names), sum("/comments/" in name for name in names)


def shapes(box, cwd):
    done = box.python(HERE / "count-record-shapes.py", "--repository", cwd)
    return {line.split("\t", 1)[1] for line in done.stdout.splitlines() if "\t" in line}


def base_code(box):
    """The plugin as it was before lib/record_types.py was added, extracted under the work folder; None when no commit adds it, and "" outside a
    git checkout, such as the export a hunk sweep runs in, which holds no history to take it from."""
    found = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=PLUGIN, capture_output=True, text=True)
    if found.returncode:
        return ""
    top = pathlib.Path(found.stdout.strip())
    prefix = PLUGIN.relative_to(top).as_posix()
    added = subprocess.run(["git", "log", "--diff-filter=A", "--format=%H", "--", f"{prefix}/lib/record_types.py"], cwd=top, capture_output=True, text=True).stdout.split()
    if not added:
        return None
    archive = subprocess.run(["git", "archive", f"{added[-1]}^", prefix], cwd=top, capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(box.work / "base")
    return box.work / "base" / prefix


def render(box, plugin, numbers):
    done = box.run([sys.executable, "-c", RENDER, str(plugin / "skills" / "kick-off" / "scripts" / "use-board.py"), *numbers], claude=["--name", "probe-manager"])
    listed = box.run([sys.executable, str(plugin / "hooks" / "list-task-board.py"), "probe", "--width", "80"], claude=["--name", "probe-manager"])
    return (json.loads(done.stdout) if done.returncode == 0 else {"exit": [done.returncode, done.stderr[-400:]]}), listed.stdout + listed.stderr[-400:]


def differences(old, new, states):
    found = []
    for key in sorted(set(old) | set(new)):
        number, worker = key.split(" ")[0], "--as" in key
        before, after = old.get(key, [None, ""]), new.get(key, [None, ""])
        expected = normalised(before[1], states.get(number, ""), worker)
        if before[0] != after[0] or expected != after[1]:
            lines = [line for line in zip(expected.splitlines(), after[1].splitlines()) if line[0] != line[1]][:2]
            found.append(f"read {key}: exit {before[0]} then {after[0]}, first lines that differ {lines or 'none, one is longer'}")
    return found


def live_copy(box):
    """A scratch repository holding this repository's board in the old form, its backup once converted; None when it has neither."""
    common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=PLUGIN, capture_output=True, text=True).stdout.strip()
    source = next((ref for ref in (BACKUP, REF) if common and subprocess.run(["git", "--git-dir", common, "rev-parse", "-q", "--verify", ref], capture_output=True).returncode == 0), None)
    if source is None:
        return None
    copy = box.init(box.work / "live")
    git(box, "fetch", "-q", "--no-tags", common, f"+{source}:{REF}", cwd=copy)
    return copy


def live(box, cases, copy):
    if copy is None:
        print("skip live: no ref")
        return
    before = counts(box, copy)
    converted = box.python(SCRIPTS / "convert-records.py", "--repository", copy)
    loaded = loads(box, copy)
    cases.step("live", converted.returncode == 0 and loaded[:2] == list(before) and not loaded[2],
               f"exit {converted.returncode} {converted.stdout}{converted.stderr[-400:]}; {before} records before, {loaded[:2]} after, not round-tripping {loaded[2]}")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases("record migration")
    board = json.loads((HERE / "old-board.json").read_text())
    states = {path.removesuffix("/task.json").rsplit("/", 1)[-1]: STATES[(record["state"], record["reason"])] for path, record in board.items() if path.endswith("/task.json")}
    numbers = sorted(states, key=int)
    with replay_probe.scratch("record-migration-") as work:
        box = replay_probe.Sandbox(work, [replay_probe.agent("probe-manager", 1), replay_probe.agent("probe-worker", 2)])
        seed(box, board)
        before = counts(box)
        copy = live_copy(box)
        live_old = shapes(box, copy) if copy else None
        fixture = shapes(box, box.repository)
        cases.step("shapes", live_old is None or live_old <= fixture, f"the live board's shapes the fixture lacks: {sorted((live_old or set()) - fixture)}")
        refusals = {number: box.python(SCRIPTS / "use-board.py", "read", number) for number in ("1", "5")}
        named = [re.search(r"python3 (\S+convert-records\.py)", run.stderr) for run in refusals.values()]
        cases.step("refused", all(run.returncode == 2 and f"{number}/task.json is a board record" in run.stderr for number, run in refusals.items())
                   and all(found and pathlib.Path(found.group(1)).is_file() for found in named), "; ".join(f"#{n} exit {run.returncode}: {run.stderr[-300:]}" for n, run in refusals.items()))
        base = base_code(box)
        old = render(box, base, numbers) if base else ({}, "")
        tip = git(box, "rev-parse", REF).strip()
        reports = box.repository / ".teamwork" / "own-reports"
        reports.mkdir(parents=True, exist_ok=True)
        (reports / "urls").write_text("".join(f"git+file:///old/checkout/.git/refs/teamwork-blackboard/{ref}\n" for ref in ("probe/4#comment-7", "6#comment-2")))
        index = box.repository / ".git" / "index"
        index_before = index.read_bytes() if index.exists() else None
        converted = box.python(SCRIPTS / "convert-records.py")
        again = box.python(SCRIPTS / "convert-records.py")
        cases.step("converted", converted.returncode == 0 and converted.stdout.startswith(f"converted {before[0]} tasks and {before[1]} comments")
                   and git(box, "rev-parse", BACKUP).strip() == tip and again.returncode == 0 and again.stdout.startswith("nothing to convert"),
                   f"exit {converted.returncode} {converted.stdout}{converted.stderr[-600:]}; again exit {again.returncode} {again.stdout}")
        stored = {path: json.loads(git(box, "show", f"{REF}:{path}")) for path in ("probe/4/comments/0007.json", "probe/4/comments/0008.json", "6/comments/0002.json", "1/comments/0002.json")}
        added = iso_time.stamp(int(git(box, "log", "-1", "--format=%ct", tip).strip()))
        cases.step("authors", [record["author"] for record in stored.values()] == ["probe-manager", "unknown", "unknown", "probe-manager"]
                   and stored["probe/4/comments/0008.json"]["again"] == "1#comment-2" and stored["6/comments/0002.json"]["kind"] == "note"
                   and stored["6/comments/0002.json"]["created"] == added and (index.read_bytes() if index.exists() else None) == index_before,
                   f"{stored}; added {added}; index kept {(index.read_bytes() if index.exists() else None) == index_before}")
        bare = box.init(box.work / "no-board")
        empty = box.python(SCRIPTS / "convert-records.py", "--repository", bare)
        helped = box.python(SCRIPTS / "convert-records.py", "--help", "--repository", bare)
        extra = box.python(SCRIPTS / "convert-records.py", "--repository", bare, "now")
        cases.step("no-board", empty.returncode == 0 and empty.stdout.startswith(f"nothing to convert: this repository has no {REF}")
                   and helped.returncode == 0 and "usage: convert-records.py" in helped.stdout and extra.returncode == 2 and "usage: convert-records.py" in extra.stderr,
                   f"exit {empty.returncode} {empty.stdout}{empty.stderr[-400:]}; --help exit {helped.returncode}; extra word exit {extra.returncode}")
        unfit = box.init(box.work / "unfit")
        seed(box, {"1/task.json": board["1/task.json"], "1/comments/0001.json": {"text": "A note.\n", "supersedes": "git+file:///old/checkout/.git/refs/teamwork-blackboard/1"}}, cwd=unfit)
        unfit_tip = git(box, "rev-parse", REF, cwd=unfit).strip()
        refused = box.python(SCRIPTS / "convert-records.py", "--repository", unfit)
        cases.step("unfit", refused.returncode == 1 and "nothing was changed" in refused.stderr and "1/comments/0001.json" in refused.stderr
                   and git(box, "rev-parse", REF, cwd=unfit).strip() == unfit_tip, f"exit {refused.returncode} {refused.stdout} {refused.stderr[-600:]}")
        mixed = box.init(box.work / "mixed")
        seed(box, {"1/task.json": json.loads(git(box, "show", f"{REF}:1/task.json")), "1/comments/0001.json": board["1/comments/0001.json"]}, cwd=mixed)
        half = box.python(SCRIPTS / "use-board.py", "read", "1", "--repository", mixed)
        cases.step("refused-comment", half.returncode == 2 and "1/comments/0001.json is a board record" in half.stderr, f"exit {half.returncode}: {half.stderr[-400:]}")
        loaded = loads(box)
        cases.step("round-trip", loaded[:2] == list(before) and not loaded[2], f"{before} records before, {loaded[:2]} after, not round-tripping {loaded[2]}")
        new = render(box, PLUGIN, numbers)
        drawn = all(old[0].get(key, [1, ""])[0] == 0 and f"#{key.split()[0]} " in old[0][key][1] for key in (f"{n}{view}" for n in numbers for view in ("", " --as worker")))
        if base == "":
            print("skip read, board: no git checkout to take the code before the change from")
        else:
            cases.step("read", base is not None and drawn and not differences(old[0], new[0], states),
                       "no commit adds lib/record_types.py" if base is None else differences(old[0], new[0], states) or old[0])
            cases.step("board", base is not None and old[1] == new[1] and "#1 " in new[1], f"before:\n{old[1]}\nafter:\n{new[1]}")
        converted_tip = git(box, "rev-parse", REF).strip()
        git(box, "update-ref", BACKUP, converted_tip)
        seed(box, board)
        held_tip = git(box, "rev-parse", REF).strip()
        held = box.python(SCRIPTS / "convert-records.py")
        cases.step("backup-held", held.returncode == 1 and f"{BACKUP} names {converted_tip}" in held.stderr and git(box, "rev-parse", REF).strip() == held_tip,
                   f"exit {held.returncode} {held.stdout}{held.stderr[-600:]}")
        git(box, "update-ref", BACKUP, held_tip)
        same = box.python(SCRIPTS / "convert-records.py")
        cases.step("backup-same", same.returncode == 0 and same.stdout.startswith("converted ") and git(box, "rev-parse", BACKUP).strip() == held_tip
                   and git(box, "rev-parse", REF).strip() != held_tip, f"exit {same.returncode} {same.stdout}{same.stderr[-600:]}")
        live(box, cases, copy)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
