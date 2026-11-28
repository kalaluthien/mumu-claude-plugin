"""The board kept in git: the records `board_records` lays out, as the tree of the commit `refs/teamwork-blackboard` names in the current folder's repository,
which every worktree shares. A reader keeps the tree it last read, with that commit as its cursor, in the repository's `.teamwork/board-projection/`, and reads
only the files changed since, so a new process reads what the last one did not. Each write is one commit, swapped in only while the ref still names the commit the write read, else run again from
the new one, so concurrent writers never lose each other's records; `git log refs/teamwork-blackboard` shows every write. Nothing here pushes the ref."""
import json
import os
import pathlib
import random
import subprocess
import threading
import time

import board_records
import board_refs
import data_folder

REF = board_refs.REF
TRIES = 100  # 40 writers racing gc on one task needed at most 34 in the probes
STALE = 10  # seconds a ref lock may stand before it is taken for a killed writer's, since a live write holds it for milliseconds
WRITER = {"GIT_AUTHOR_EMAIL": "teamwork@localhost", "GIT_COMMITTER_NAME": "teamwork", "GIT_COMMITTER_EMAIL": "teamwork@localhost"}


class GitFailed(Exception):
    pass


class Ref(board_records.Store):
    def __init__(self):
        self.common, self.tip, self.files, self.folders, self.places, self.memo = None, None, {}, {}, {}, {}
        self.blobs_read = 0  # the blobs the last refresh read, which a reader's cost follows
        self.loaded = None  # the commit of the projection this reader loaded whole, if any

    def git(self, *args, data=None, env=None, check=True):
        if self.common is None:
            found = data_folder.common_folder()
            if found is None:
                raise LookupError("the git board needs a git repository: run this inside a project's checkout")
            self.common = str(found)
        run = subprocess.run(["git", f"--git-dir={self.common}", *args], capture_output=True, input=data, env={**os.environ, **(env or {})})
        if check and run.returncode:
            raise GitFailed(f"git {args[0]}: {run.stderr.decode(errors='replace').strip()}")
        return run

    def blobs(self, ids):
        """The texts of the blobs IDS, read in one batch."""
        output = self.git("cat-file", "--batch", data="".join(f"{blob}\n" for blob in ids).encode()).stdout if ids else b""
        texts, at = [], 0
        for _ in ids:
            header_end = output.index(b"\n", at)
            size = int(output[at:header_end].split()[2])
            texts.append(output[header_end + 1:header_end + 1 + size].decode())
            at = header_end + 1 + size + 1
        self.blobs_read += len(ids)
        return texts

    def fold(self, tip):
        """The files of TIP's tree, from the kept tree of an earlier commit and only the files changed since it, else from the whole tree."""
        base, files = self.tip, self.files
        if not base:
            self.loaded, files = self.saved()
            base = self.loaded
        if base and tip:
            changed = self.git("diff-tree", "-r", "-z", "--no-renames", base, tip, check=False)
            if changed.returncode == 0:
                fields = changed.stdout.decode().split("\0")
                gone, paths, ids = [], [], []
                for head, path in zip(fields[0::2], fields[1::2]):
                    blob, status = head.split()[3], head.split()[4]
                    (gone.append(path) if status == "D" else (paths.append(path), ids.append(blob)))
                files = {**files, **dict(zip(paths, self.blobs(ids)))}
                for path in gone:
                    files.pop(path, None)
                return files
        if not tip:
            return {}
        entries = [line.split("\t", 1) for line in self.git("ls-tree", "-r", "-z", tip).stdout.decode().split("\0") if line]
        return dict(zip([path for _, path in entries], self.blobs([head.split()[2] for head, _ in entries])))

    def projection(self):
        """The projection file; only a refresh, which ran git in this repository first, asks for it, so its folder exists."""
        return data_folder.folder("board-projection") / "tree.json"

    def saved(self):
        """The commit and files the last reader of this repository kept, or (None, {}) when none was kept or it cannot be read."""
        try:
            tip, files = self.projection().read_text().split("\n", 1)
            return tip, json.loads(files)
        except (OSError, ValueError):  # a projection cut short or damaged is read again from the tree
            return None, {}

    def save(self):
        """Keeps the tree just read, its commit on the first line, replacing the file at once, so a reader racing this one reads one whole projection or the last;
        a projection this reader loaded whole at the same commit is left as it is."""
        if self.loaded == self.tip:
            return
        path = self.projection()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            spare = path.with_name(f"{path.name}.{os.getpid()}-{threading.get_ident()}")
            spare.write_text(f"{self.tip}\n{json.dumps(self.files)}")
            os.replace(spare, path)
        except OSError:  # a reader that cannot keep its projection still read the board
            pass

    def refresh(self):
        """Reads the tree of the ref's commit, once per commit, since a reader such as the task pane reads again on every signal."""
        tip = self.git("rev-parse", "-q", "--verify", f"{REF}^{{commit}}", check=False).stdout.decode().strip()
        if tip == self.tip:
            return
        self.blobs_read = 0
        files = self.fold(tip)
        folders = {}
        for path in files:
            parts = path.split("/")
            for depth in range(len(parts)):
                folders.setdefault("/".join(parts[:depth]), set()).add(parts[depth])
        places = {}
        for path in files:
            *folder, number, name = ["", *path.split("/")]
            if name == board_records.RECORD and number.isdigit():
                places[int(number)] = "/".join(folder[1:])
        self.tip, self.files, self.folders, self.places, self.memo = tip, files, folders, places, {}
        if tip:
            self.save()

    def homes(self):
        return self.places

    def load(self, path):
        if path not in self.files:
            raise FileNotFoundError(f"{REF}:{path}")
        return self.files[path]

    def names(self, folder=""):
        return self.folders.get(folder, ())

    def url(self, path):
        scope, _, number = path.rpartition("/")
        return board_refs.url(scope, int(number))

    def commit(self, staged):
        """A commit on the read tip with STAGED's files over its tree, built in an index of its own, since the checkout's index is the person's."""
        index = pathlib.Path(self.common) / f"teamwork-board-index-{os.getpid()}-{threading.get_ident()}"
        env = {"GIT_INDEX_FILE": str(index), **WRITER, "GIT_AUTHOR_NAME": self.author or "teamwork"}
        try:
            self.git("read-tree", *([self.tip] if self.tip else ["--empty"]), env=env)
            listing = "".join(f"0 {'0' * 40}\t{path}\n" if text is None else f"100644 {self.git('hash-object', '-w', '--stdin', data=text.encode()).stdout.decode().strip()}\t{path}\n"
                              for path, text in staged.items())
            self.git("update-index", "--index-info", data=listing.encode(), env=env)
            tree = self.git("write-tree", env=env).stdout.decode().strip()
            message = "write " + ", ".join(staged)
            return self.git("commit-tree", tree, *(["-p", self.tip] if self.tip else []), "-m", message, env=env).stdout.decode().strip(), message
        finally:
            index.unlink(missing_ok=True)

    def keep(self, change):
        """Runs CHANGE on the newest board and swaps its commit in, again from the newer board on any git failure, since a lost race and a
        concurrent gc both surface as one."""
        failure = None
        for _ in range(TRIES):
            self.refresh()
            self.pending = {}
            try:
                result = change()
                staged = self.pending
            finally:
                self.pending = None
            if not staged:
                return result
            try:
                new, message = self.commit(staged)
                self.git("update-ref", "--create-reflog", "-m", message, REF, new, self.tip or "")
                return result
            except GitFailed as e:
                failure = e
            lock = pathlib.Path(self.common) / f"{REF}.lock"
            try:
                if time.time() - lock.stat().st_mtime > STALE:
                    raise LookupError(f"{lock} has stood {STALE} seconds, likely left by a killed writer: remove it once no board write is running, then write again")
            except FileNotFoundError:
                pass
            time.sleep(random.uniform(0, 0.02))
        raise LookupError(f"the board write failed {TRIES} times; the last failure: {failure}")


STORE = Ref()
globals().update(board_records.bind(STORE))


def author(name):
    """Names NAME as the author of each later write's comments and commit, so a comment and `git log refs/teamwork-blackboard` show who wrote it;
    a comment by no named session is `unknown`'s, its commit `teamwork`'s."""
    STORE.author = name or None
