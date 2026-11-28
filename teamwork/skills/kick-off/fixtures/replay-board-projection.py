#!/usr/bin/env python3
"""Write a scratch git board and read it as the board's readers do, and print `ok <case>` or `fail <case>: <what it saw>` per case, then
`PASS board projection` or `FAIL board projection`; exit 1 on any failure:
- `saved`: after each write the projection a read keeps equals the tree of the board's commit, read whole;
- `changed-only`: a reader in a new process, after one comment, reads only the blobs that comment's write changed;
- `unchanged`: a reader in a new process with no write since reads no blob and leaves the projection file as it was;
- `damaged`: a projection file cut short is read again from the tree, the same tasks found, and kept whole again;
- `gone`: after a commit by plain git that deletes a file of the board, the projection holds the tree without it;
- `many`: a board of 201 open tasks gives the heartbeat's task read all 201;
- `elsewhere`: a write to another repository's board leaves this repository's change signal as it was;
- `live`: on a copy of this repository's board, every task the code before the change read equals what this code reads, at the first fold and from the
  saved projection, and the task pane's rows are the same; the code before the change is the commit before the one that added the projection, HEAD while
  none has; `skip live` when the repository has no board or this is no git checkout.

usage: replay-board-projection.py"""
import io
import json
import pathlib
import subprocess
import sys
import tarfile

HERE = pathlib.Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
sys.path.insert(0, str(PLUGIN / "lib"))
import replay_probe  # noqa: E402

REF = "refs/teamwork-blackboard"
# every task as the board port reads it, and the blobs the read took, which the code before the change does not count, printed as one JSON line
READ = """import json, sys
sys.path.insert(0, sys.argv[1])
import board, board_git
found = board.tasks("all", comments=True)
print(json.dumps([found, getattr(board_git.STORE, "blobs_read", None)]))"""


def tree(box, cwd=None):
    """{path: text} of the board commit's tree, read whole by git itself."""
    listing = box.git("ls-tree", "-r", "-z", "--name-only", REF, cwd=cwd).split("\0")
    return {path: box.git("cat-file", "blob", f"{REF}:{path}", cwd=cwd) for path in listing if path}


def saved(cwd):
    path = pathlib.Path(cwd) / ".teamwork" / "board-projection" / "tree.json"
    if not path.exists():
        return None, None
    tip, files = path.read_text().split("\n", 1)
    return tip, json.loads(files)


def read(box, plugin, cwd=None):
    done = box.run([sys.executable, "-c", READ, str(plugin / "lib")], cwd=cwd, claude=["--name", "probe-manager"])
    return json.loads(done.stdout) if done.returncode == 0 else [f"exit {done.returncode}: {done.stderr[-300:]}", None]


def base_code(box):
    """The plugin before the commit that added the projection, HEAD while none has, extracted under the work folder; None outside a git checkout,
    such as the export a hunk sweep runs in."""
    found = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=PLUGIN, capture_output=True, text=True)
    if found.returncode:
        return None
    top = pathlib.Path(found.stdout.strip())
    prefix = PLUGIN.relative_to(top).as_posix()
    added = subprocess.run(["git", "log", "-Sboard-projection", "--format=%H", "--", f"{prefix}/lib/board_git.py"], cwd=top, capture_output=True, text=True).stdout.split()
    archive = subprocess.run(["git", "archive", f"{added[-1]}^" if added else "HEAD", prefix], cwd=top, capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(box.work / "base")
    return box.work / "base" / prefix


def live_copy(box):
    """A scratch repository holding this repository's board; None when it has none."""
    common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=PLUGIN, capture_output=True, text=True).stdout.strip()
    if not common or subprocess.run(["git", "--git-dir", common, "rev-parse", "-q", "--verify", REF], capture_output=True).returncode:
        return None
    copy = box.init(box.work / "live")
    box.git("fetch", "-q", "--no-tags", common, f"+{REF}:{REF}", cwd=copy)
    return copy


def pane(box, plugin, cwd):
    done = box.run([sys.executable, str(plugin / "hooks" / "list-task-board.py"), "teamwork", "--json", "--width", "60"], cwd=cwd, claude=["--name", "teamwork-manager"])
    return done.stdout if done.returncode == 0 else f"exit {done.returncode}: {done.stderr[-300:]}"


def write(box, code, cwd=None, timeout=120):
    """CODE run with the board port imported as `board`, as the probe's manager writes; its run."""
    return box.run([sys.executable, "-c", f"import sys; sys.path.insert(0, sys.argv[1]); import board\n{code}", str(PLUGIN / "lib")],
                   cwd=cwd, claude=["--name", "probe-manager"], timeout=timeout)


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases("board projection")
    with replay_probe.scratch("board-projection-") as work:
        box = replay_probe.Sandbox(work)
        mismatched = []
        for step in range(3):
            write(box, f"board.file('Task {step}', 'A task.', []); board.comment(1, 'REPORTED: step {step}')")
            read(box, PLUGIN)
            tip, files = saved(box.repository)
            if tip != box.git("rev-parse", REF).strip() or files != tree(box):
                mismatched.append(f"after write {step}: kept {tip}")
        cases.step("saved", not mismatched, mismatched)

        write(box, "board.comment(2, 'REPORTED: one more')")
        found, blobs = read(box, PLUGIN)
        # the write adds the comment and saves the task's updatedAt
        cases.step("changed-only", blobs == 2, f"{blobs} blobs read")

        kept = box.repository / ".teamwork" / "board-projection" / "tree.json"
        before = kept.stat().st_mtime_ns
        same, blobs = read(box, PLUGIN)
        cases.step("unchanged", same == found and blobs == 0 and kept.stat().st_mtime_ns == before, f"{blobs} blobs read, file {'kept' if kept.stat().st_mtime_ns == before else 'written'}")

        kept.write_text(kept.read_text()[:100])
        again, _ = read(box, PLUGIN)
        cases.step("damaged", again == found and saved(box.repository)[1] == tree(box), f"tasks the same: {again == found}")

        gone = next(path for path in tree(box) if "/comments/" in path)
        index = {**box.environment, "GIT_INDEX_FILE": str(work / "gone-index")}
        plain = lambda *argv: replay_probe.sh("git", *argv, cwd=box.repository, environment=index).stdout.strip()
        plain("read-tree", REF)
        plain("update-index", "--force-remove", gone)
        plain("update-ref", REF, plain("commit-tree", plain("write-tree"), "-p", REF, "-m", "Delete a comment by plain git"))
        read(box, PLUGIN)
        files = saved(box.repository)[1]
        cases.step("gone", files == tree(box) and gone not in files, f"{gone} kept: {gone in files}")

        many = box.init(work / "many")
        done = write(box, "for k in range(201): board.file(f'Task {k}', 'A task.', [])", cwd=many, timeout=300)
        counted = box.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import team_gaps; print(len(team_gaps.tasks()))", str(PLUGIN / "lib")], cwd=many)
        cases.step("many", done.returncode == 0 and counted.stdout.strip() == "201", f"{done.stderr[-200:]} {counted.stdout.strip()} {counted.stderr[-200:]}")

        stamp = "import sys; sys.path.insert(0, sys.argv[1]); import team_signal; print(team_signal.stamp())"
        before = box.run([sys.executable, "-c", stamp, str(PLUGIN / "lib")]).stdout
        write(box, "board.comment(1, 'REPORTED: elsewhere')", cwd=many)
        after = box.run([sys.executable, "-c", stamp, str(PLUGIN / "lib")]).stdout
        cases.step("elsewhere", before == after and before.strip() != "0", f"{before.strip()} then {after.strip()}")

        copy, base = live_copy(box), base_code(box)
        if copy is None or base is None:
            print("skip live: no board or no git checkout")
        else:
            old = read(box, base, copy)[0]
            first = read(box, PLUGIN, copy)[0]
            again = read(box, PLUGIN, copy)
            rows_old, rows_new = pane(box, base, copy), pane(box, PLUGIN, copy)
            cases.step("live", old == first == again[0] and again[1] == 0 and rows_old == rows_new,
                       f"tasks the same at the first fold: {old == first}, from the projection: {old == again[0]} reading {again[1]} blobs; pane rows the same: {rows_old == rows_new}; "
                       f"the first task that differs: {next(([a, b] for a, b in zip(old, first) if a != b), str(old)[:300])}")
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
