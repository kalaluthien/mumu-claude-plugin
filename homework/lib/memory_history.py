"""The history of the auto-memory home: each change set as a commit of a bare git directory beside the home, `<home>.git`, which no git command of another repository reaches."""
import os
import pathlib
import shutil
import subprocess
import tempfile
import time

REF = "refs/heads/main"
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
RETRIES = 3
PACK_DAYS = 7
REPOSITORY_VARIABLES = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_NAMESPACE")
IDENTITY = {"GIT_AUTHOR_NAME": "homework", "GIT_AUTHOR_EMAIL": "homework@localhost",
            "GIT_COMMITTER_NAME": "homework", "GIT_COMMITTER_EMAIL": "homework@localhost"}


class Refused(Exception):
    """A snapshot or export the history will not make, with the reason."""


def environment(extra=None):
    """The caller's environment without the variables that point git at another repository, plus the snapshot's own identity and `extra`."""
    kept = {name: value for name, value in os.environ.items() if name not in REPOSITORY_VARIABLES}
    return {**kept, **IDENTITY, **(extra or {})}


def directory(home):
    """The git directory beside a memory home: `~/.claude/memory` keeps its history in `~/.claude/memory.git`."""
    home = pathlib.Path(home).absolute()
    return home.parent / f"{home.name}.git"


def git(git_dir, *args, env=None, cwd=None, check=True):
    """A git command on the history, its completed process; a failure raises Refused with git's message when check is set."""
    done = subprocess.run(["git", "--git-dir", str(git_dir), *args], capture_output=True, text=True, cwd=cwd,
                          env=environment(env), check=False)
    if check and done.returncode:
        raise Refused(f"git {args[0]} failed: {done.stderr.strip()}")
    return done


def start(git_dir):
    """Make the git directory when it is missing, its branch `main`, and say whether this call made it.

    It is built beside the target and renamed into place, so snapshots started together find either no directory or a whole one."""
    if git_dir.exists() and not git_dir.is_dir():
        raise Refused(f"{git_dir} is a file, not a git directory")
    if (git_dir / "HEAD").exists():
        return False
    building = git_dir.with_name(f"{git_dir.name}.{os.getpid()}.new")
    shutil.rmtree(building, ignore_errors=True)
    try:
        started = subprocess.run(["git", "init", "-q", "--bare", "--template=", str(building)], capture_output=True, text=True, check=False, env=environment())
        if started.returncode:
            raise Refused(f"git init failed: {started.stderr.strip()}")
        git(building, "symbolic-ref", "HEAD", REF)
        try:
            building.rename(git_dir)
        except OSError:
            if not (git_dir / "HEAD").exists():
                raise Refused(f"{git_dir} could not be made")
            return False
        return True
    finally:
        shutil.rmtree(building, ignore_errors=True)


def check_reach(home, git_dir):
    """Refuse a home whose history a surrounding repository would show, or that holds a repository below its root, since the first lets `git add -A` there
    commit every lesson ever kept and the second reaches the history only as a bare link."""
    inside = subprocess.run(["git", "-C", str(home.parent), "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True, check=False, env=environment())
    if inside.stdout.strip() == "true" and subprocess.run(["git", "-C", str(home.parent), "check-ignore", "-q", str(git_dir)], check=False, env=environment()).returncode:
        raise Refused(f"the repository around {home} does not ignore {git_dir.name}, so its git add would record the history; ignore /{git_dir.name} there")
    nested = next((path for path in home.rglob(".git") if path.parent != home), None)
    if nested:
        raise Refused(f"{nested.parent} is a git repository, which a snapshot records as a bare link without its files; move it out of {home}")


def pack(git_dir):
    """Pack the loose objects once a week, since nothing in a snapshot starts git's own packing."""
    stamp = git_dir / "last-pack"
    if stamp.exists() and time.time() - stamp.stat().st_mtime < PACK_DAYS * 86400:
        return
    git(git_dir, "gc", "-q", check=False)
    stamp.touch()


def snapshot(home, message):
    """Commit the home's files if they differ from the tip: (the commit, True), or (the tip, False) when nothing changed.

    Every file is added by `add -f`, whatever a global or in-home ignore rule says, since `._*` and `.DS_Store` are ignored by default and a memory file
    must not drop out of the history; an empty home is refused, since an unmounted folder would otherwise record every lesson as deleted.
    The old tip guards the write, so a snapshot that another one overtakes reads the tip again and tries up to three times.
    A refusal leaves no git directory behind that the call made."""
    home = pathlib.Path(home).absolute()
    if not home.is_dir():
        raise Refused(f"{home} is no folder")
    git_dir = directory(home)
    made = start(git_dir)
    try:
        check_reach(home, git_dir)
        return commit_tree(home, git_dir, message)
    except Refused:
        if made and not git(git_dir, "rev-parse", "--verify", "-q", REF, check=False).stdout.strip():
            shutil.rmtree(git_dir, ignore_errors=True)
        raise


def commit_tree(home, git_dir, message):
    """The tree of the home's files as a commit on the tip, with the retries `snapshot` describes."""
    with tempfile.TemporaryDirectory(prefix="memory-index-") as folder:
        env = {"GIT_INDEX_FILE": f"{folder}/index", "GIT_WORK_TREE": str(home)}
        git(git_dir, "add", "-A", "-f", ".", env=env, cwd=home)
        tree = git(git_dir, "write-tree", env=env).stdout.strip()
        if tree == EMPTY_TREE:
            raise Refused(f"{home} holds no file, so nothing was recorded")
        for _ in range(RETRIES):
            tip = git(git_dir, "rev-parse", "--verify", "-q", REF, check=False).stdout.strip()
            if tip and git(git_dir, "rev-parse", f"{tip}^{{tree}}").stdout.strip() == tree:
                return tip, False
            commit = git(git_dir, "commit-tree", tree, *(["-p", tip] if tip else []), "-m", message, env=env).stdout.strip()
            if git(git_dir, "update-ref", REF, commit, tip, check=False).returncode == 0:
                pack(git_dir)
                return commit, True
        raise Refused(f"the tip moved {RETRIES} times while the snapshot was made")


def export(home, destination):
    """Write the tip's files to `<destination>/<home>`, the layout the dream's backup has, replacing what was there only once the new copy is whole, and return how many files it wrote."""
    home = pathlib.Path(home).absolute()
    git_dir = directory(home)
    if not (git_dir / "HEAD").exists() or git(git_dir, "rev-parse", "--verify", "-q", REF, check=False).returncode:
        raise Refused(f"{git_dir} holds no snapshot yet")
    target = pathlib.Path(destination).absolute() / str(home).lstrip("/")
    building = target.with_name(f"{target.name}.{os.getpid()}.new")
    shutil.rmtree(building, ignore_errors=True)
    building.mkdir(parents=True)
    try:
        with tempfile.TemporaryDirectory(prefix="memory-index-") as folder:
            env = {"GIT_INDEX_FILE": f"{folder}/index"}
            git(git_dir, "read-tree", REF, env=env)
            git(git_dir, "--work-tree", str(building), "checkout-index", "-a", "-f", env=env, cwd=building)
        shutil.rmtree(target, ignore_errors=True)
        building.rename(target)
    finally:
        shutil.rmtree(building, ignore_errors=True)
    return len(git(git_dir, "ls-tree", "-r", "--name-only", REF).stdout.splitlines())
