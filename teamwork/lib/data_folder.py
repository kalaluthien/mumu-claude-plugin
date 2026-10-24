"""Where a project keeps the data teamwork writes for itself: `<main checkout>/.teamwork/<name>`, the same for every worktree of the project."""
import pathlib
import subprocess


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
