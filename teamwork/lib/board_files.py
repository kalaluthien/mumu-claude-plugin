"""The board in plain files: the records `board_records` lays out, each a file under `TEAMWORK_BOARD_DIR`, written under the folder's lock."""
import fcntl
import os
import pathlib

import board_records
import claude_config
import data_folder


def default_folder():
    """The main checkout's `.teamwork/board`, the same for every worktree of a project and never committed; outside a repository, or with no git, the Claude config folder's."""
    return data_folder.folder("board") or claude_config.folder() / "teamwork" / "board"

FOLDER = pathlib.Path(os.environ.get("TEAMWORK_BOARD_DIR") or default_folder())


def put(path, text):
    """Writes PATH whole by a rename, so a reader that takes no lock never sees it half written."""
    part = path.with_name(f".{path.name}.{os.getpid()}.part")
    part.write_text(text)
    os.replace(part, path)


class Folder(board_records.Store):
    def load(self, path):
        return (FOLDER / path).read_text()

    def names(self, folder=""):
        try:
            return [path.name for path in (FOLDER / folder).iterdir() if not path.name.startswith(".")]
        except OSError:
            return []

    def written(self, path):
        return (FOLDER / path).stat().st_mtime

    def url(self, path):
        return f"file://{FOLDER}/{path}"

    def refresh(self):
        pass

    def keep(self, change):
        """Runs CHANGE once under the folder's lock, since two sessions writing at once would number or read-modify-write over each other,
        then writes its files in the order it staged them."""
        FOLDER.mkdir(parents=True, exist_ok=True)
        with open(FOLDER / ".lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.pending = {}
            try:
                result = change()
                for path, text in self.pending.items():
                    (FOLDER / path).parent.mkdir(parents=True, exist_ok=True)
                    put(FOLDER / path, text)
                return result
            finally:
                self.pending = None


STORE = Folder()
globals().update(board_records.bind(STORE))
