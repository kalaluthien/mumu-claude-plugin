"""The board kept in git: the records `board_records` lays out, as the tree of the commit `refs/teamwork-blackboard` names in the current folder's repository,
which every worktree shares. Each write is one commit, swapped in only while the ref still names the commit the write read, else run again from
the new one, so concurrent writers never lose each other's records; `git log refs/teamwork-blackboard` shows every write. Nothing here pushes the ref."""
import os
import pathlib
import random
import subprocess
import threading
import time

import board_records

REF = "refs/teamwork-blackboard"
TRIES = 100  # 40 writers racing gc on one issue needed at most 34 in the probes
STALE = 10  # seconds a ref lock may stand before it is taken for a killed writer's, since a live write holds it for milliseconds
WRITER = {"GIT_AUTHOR_NAME": "teamwork", "GIT_AUTHOR_EMAIL": "teamwork@localhost", "GIT_COMMITTER_NAME": "teamwork", "GIT_COMMITTER_EMAIL": "teamwork@localhost"}


class GitFailed(Exception):
    pass


class Ref(board_records.Store):
    def __init__(self):
        self.common, self.tip, self.files, self.folders, self.times, self.timed, self.places = None, None, {}, {}, {}, None, {}

    def git(self, *args, data=None, env=None, check=True):
        if self.common is None:
            found = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], capture_output=True, text=True)
            if found.returncode or not found.stdout.strip():
                raise LookupError("the git board needs a git repository: run this inside a project's checkout")
            self.common = found.stdout.strip()
        run = subprocess.run(["git", f"--git-dir={self.common}", *args], capture_output=True, input=data, env={**os.environ, **(env or {})})
        if check and run.returncode:
            raise GitFailed(f"git {args[0]}: {run.stderr.decode(errors='replace').strip()}")
        return run

    def refresh(self):
        """Reads the tree of the ref's commit, once per commit, since a reader such as the issue pane reads again on every signal."""
        tip = self.git("rev-parse", "-q", "--verify", f"{REF}^{{commit}}", check=False).stdout.decode().strip()
        if tip == self.tip:
            return
        files = {}
        if tip:
            entries = [line.split("\t", 1) for line in self.git("ls-tree", "-r", "-z", tip).stdout.decode().split("\0") if line]
            output = self.git("cat-file", "--batch", data="".join(f"{head.split()[2]}\n" for head, _ in entries).encode()).stdout
            at = 0
            for _, path in entries:
                header_end = output.index(b"\n", at)
                size = int(output[at:header_end].split()[2])
                files[path] = output[header_end + 1:header_end + 1 + size].decode()
                at = header_end + 1 + size + 1
        folders = {}
        for path in files:
            parts = path.split("/")
            for depth in range(len(parts)):
                folders.setdefault("/".join(parts[:depth]), set()).add(parts[depth])
        places = {}
        for path in files:
            *folder, number, name = ["", *path.split("/")]
            if name == "issue.json" and number.isdigit():
                places[int(number)] = "/".join(folder[1:])
        self.tip, self.files, self.folders, self.places = tip, files, folders, places

    def homes(self):
        return self.places

    def load(self, path):
        if path not in self.files:
            raise FileNotFoundError(f"{REF}:{path}")
        return self.files[path]

    def names(self, folder=""):
        return self.folders.get(folder, ())

    def written(self, path):
        """When PATH's commit was made, read from the log once per commit, since a comment's time is not in its file."""
        if self.timed != self.tip:
            self.times = {}
            log = self.git("log", "--format=%x00%ct", "--name-only", "--diff-filter=A", self.tip).stdout.decode() if self.tip else ""
            for commit in log.split("\0")[1:]:
                seconds, *paths = commit.split()
                for added in paths:
                    self.times[added] = int(seconds)  # the log runs newest first, so the oldest add stays
            self.timed = self.tip
        return self.times.get(path, 0)

    def url(self, path):
        return f"git+file://{self.common}/{REF}/{path}"

    def commit(self, staged):
        """A commit on the read tip with STAGED's files over its tree, built in an index of its own, since the checkout's index is the person's."""
        index = pathlib.Path(self.common) / f"teamwork-board-index-{os.getpid()}-{threading.get_ident()}"
        env = {"GIT_INDEX_FILE": str(index), **WRITER}
        try:
            self.git("read-tree", *([self.tip] if self.tip else ["--empty"]), env=env)
            listing = "".join(f"100644 {self.git('hash-object', '-w', '--stdin', data=text.encode()).stdout.decode().strip()}\t{path}\n" for path, text in staged.items())
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
