"""Where a project keeps the data teamwork writes for itself, `<main checkout>/.teamwork/<name>`, the same for every worktree of the project, and where its worktrees sit, `<main checkout>/.claude/worktrees/<name>`;
and the one `--repository <folder>` flag, which names the checkout a script call acts on."""
import os
import pathlib
import re
import subprocess
import sys

FLAG = "--repository"
WORKTREE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")
WORKTREES = pathlib.PurePath(".claude") / "worktrees"


def common_folder():
    """The git common folder of the current folder's repository; None outside one, or with no git."""
    try:
        run = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], capture_output=True, text=True)
    except OSError:
        return None
    return pathlib.Path(run.stdout.strip()) if run.returncode == 0 and run.stdout.strip() else None


def exclude(common, name):
    """Adds `/.teamwork/<name>/` to the common folder's `info/exclude`, so the data never reaches a commit while `.teamwork/settings.json` does."""
    line = f"/.teamwork/{name}/"
    path = common / "info" / "exclude"
    old = path.read_text() if path.exists() else ""
    if line not in old.splitlines():
        path.parent.mkdir(exist_ok=True)
        path.write_text(old + "\n" * bool(old and not old.endswith("\n")) + line + "\n")


def claim(common, name):
    """Moves a folder an older version kept in the common folder to the new place, never copied, since two copies would split the data."""
    old, new = common / "teamwork" / name, common.parent / ".teamwork" / name
    if old.is_dir() and not new.exists():
        new.parent.mkdir(exist_ok=True)
        old.rename(new)
        try:
            old.parent.rmdir()  # the folder an older version made, once nothing else is in it
        except OSError:
            pass


def folder(name):
    """The folder for NAME, claimed on first use; None outside a repository, or with no git.
    A common folder that is not a `.git` (a bare repository, a submodule) keeps the data inside itself, where git never lists it."""
    common = common_folder()
    if common is None:
        return None
    if common.name != ".git":
        return common / "teamwork" / name
    claim(common, name)
    exclude(common, name)
    return common.parent / ".teamwork" / name


def enter(args, doc):
    """ARGS without `--repository <folder>` or `--repository=<folder>`, the process moved into that folder, so every git call below it acts on that checkout, main or worktree, and
    a relative path among the other arguments (`--body`, `--text`, a body file) is read from that folder; ARGS as they were with no flag. A call with the flag twice or with no folder is refused as a call DOC cannot read, a
    folder in no git repository with one line, each on stderr with exit 2."""
    at = [index for index, word in enumerate(args) if word == FLAG or word.startswith(FLAG + "=")]
    if not at:
        return args
    joined = "=" in args[at[0]]
    folder = args[at[0]].partition("=")[2] if joined else "".join(args[at[0] + 1:at[0] + 2])
    if len(at) > 1 or not folder or folder.startswith("-"):
        print(doc, file=sys.stderr)
        sys.exit(2)
    try:
        os.chdir(folder)
    except OSError as e:
        print(f"{FLAG}: {folder}: {e.strerror}", file=sys.stderr)
        sys.exit(2)
    if common_folder() is None:
        print(f"{FLAG}: {folder} is in no git repository.", file=sys.stderr)
        sys.exit(2)
    return args[:at[0]] + args[at[0] + 1 + (not joined):]


def main_checkout():
    """The main checkout of the current folder's repository, the same from any of its worktrees; None outside one."""
    common = common_folder()
    return common.parent if common else None


def worktrees():
    """The folder `<main checkout>/.claude/worktrees` that holds every worktree; None outside a repository."""
    root = main_checkout()
    return root / WORKTREES if root else None


def worktree(name):
    """The path `<main checkout>/.claude/worktrees/<NAME>`; ValueError for a NAME that is not one segment of letters, digits and `-` opening with a letter or digit, or whose
    path is itself a link, which a removal would follow to another folder; LookupError outside a repository."""
    folder = worktrees()
    if folder is None:
        raise LookupError("run it inside the repository")
    if not WORKTREE_NAME.fullmatch(name):
        raise ValueError(f"{name!r} is no worktree name: use one word of letters, digits and `-`, as `<task>-worker`")
    path = folder / name
    if path.is_symlink():
        raise ValueError(f"{name!r} is a link in {folder}, not a worktree")
    return path
