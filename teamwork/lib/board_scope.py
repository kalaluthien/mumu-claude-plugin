"""Which folder of the repository a project's records live in: the top-level folder named like the project, else the repository root (''), and no setting.
A folder is a path from the repository root, `teamwork` or `teamwork/hooks`; the folder of a record holds `<n>/issue.json`."""
import pathlib
import subprocess

import session
import team_names


def top():
    """The repository root of the current folder; LookupError outside a repository."""
    found = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if found.returncode or not found.stdout.strip():
        raise LookupError("a board scope needs a git repository: run this inside a project's checkout")
    return pathlib.Path(found.stdout.strip())


def named(name):
    """Whether NAME is a top-level folder of the repository that can hold records: not hidden, and not digits, which number a record."""
    return bool(name) and "/" not in name and not name.startswith(".") and not name.isdigit() and (top() / name).is_dir()


def folder_of(project):
    return project if named(project) else ""


def check(folder):
    """FOLDER as a clean path from the repository root, '' for the root itself; LookupError when it names no folder of the repository."""
    clean = folder.strip("/")
    parts = clean.split("/") if clean else []
    if any(part in ("", ".", "..") or part.startswith(".") or part.isdigit() for part in parts) or (parts and not (top() / clean).is_dir()):
        raise LookupError(f"--scope {folder!r} names no folder of this repository: give a folder path from its root, or '' for the root")
    return clean


def default():
    """The folder a record is filed in when the caller names none: a manager's own project folder, else the root."""
    name = session.sessions()[1].get("name")
    return folder_of(team_names.project(name)) if team_names.role(name) == "manager" else ""


def within(folder, scope):
    """Whether a record in FOLDER belongs to SCOPE: the folder and below, but the root scope holds only the root's own records."""
    return folder == scope or (scope != "" and folder.startswith(scope + "/"))
