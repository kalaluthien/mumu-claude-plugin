#!/usr/bin/env python3
"""Replay how the board ref `refs/teamwork-blackboard` travels on each installed git, in temporary repositories, and run the commands that board.md's `Local only` bullet prints.
Print `ok <git> <case>` or `fail <git> <case>: <what it saw>` per case, then `PASS` as the last line when all hold, else `FAIL`; exit 1 on any fail.
- clone, fetch, push: a plain clone, fetch or push leaves the ref behind but brings the branches
- push-own-name, push-under-refs: a push to a ref directly under `refs/` is refused with `funny refname`, one to `refs/foo/bar` is not
- mirror-skips, mirror-deletes: `push --mirror` sends no board ref, and deletes it from a remote that holds it
- doc-copy-out, doc-copy-in, doc-clone, doc-fetch: each `git ...` command in the bullet, with `<remote>` and `<url>` filled in, copies the ref and keeps its commit
- doc-words: the bullet states each behaviour above and claims no send

usage: replay-board-travel.py [git...]
With no git named, it runs `git` on PATH and `/usr/bin/git`."""
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
BOARD_DOC = ROOT / "skills" / "kick-off" / "references" / "adapters" / "board.md"
REF = "refs/teamwork-blackboard"
SAYS = ("a plain clone, fetch or push leaves `refs/teamwork-blackboard` behind", "push --mirror` skips it", "deletes it from a remote that holds it", "funny refname", "directly under `refs/`")
CLAIMS_SEND = re.compile(r"\b(?:sends?|travels)\b", re.I)
failed = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {str(detail).strip()}", flush=True)
    if not ok:
        failed.append(name)


def bullet_text():
    return next((line for line in BOARD_DOC.read_text().splitlines() if line.startswith("- **Local only**")), "")


def replay(git, work, commands):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
           "GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "a@a", "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "a@a"}

    def run(*argv, cwd=work):
        return subprocess.run([git, *argv], cwd=cwd, env=env, capture_output=True, text=True)

    def refs(path):
        return run("for-each-ref", "--format=%(refname)", cwd=path).stdout.split()

    def bare(name):
        run("init", "-q", "--bare", name)
        return work / name

    def tip(path):
        return run("rev-parse", REF, cwd=path).stdout.strip()

    def command(text, folder, **fill):
        for key, value in fill.items():
            text = text.replace(f"<{key}>", str(value))
        return run(*shlex.split(text)[1:], cwd=folder)

    def named(prefix):
        return next((text for text in commands if text.startswith(prefix)), None)

    run("init", "-q", "-b", "main", "src")
    source = work / "src"
    run("commit", "-q", "--allow-empty", "-m", "init", cwd=source)
    board = run("commit-tree", "-m", "board", "HEAD^{tree}", cwd=source).stdout.strip()
    run("update-ref", REF, board, cwd=source)

    run("clone", "-q", "src", "clone")
    step(f"{git} clone", REF not in refs(work / "clone") and "refs/remotes/origin/main" in refs(work / "clone"), refs(work / "clone"))
    run("init", "-q", "fetch")
    run("remote", "add", "origin", str(source), cwd=work / "fetch")
    run("fetch", "-q", "origin", cwd=work / "fetch")
    step(f"{git} fetch", REF not in refs(work / "fetch") and "refs/remotes/origin/main" in refs(work / "fetch"), refs(work / "fetch"))
    plain = bare("plain.git")
    run("push", "-q", str(plain), "main", cwd=source)
    step(f"{git} push", REF not in refs(plain) and "refs/heads/main" in refs(plain), refs(plain))

    own = run("push", str(bare("own.git")), REF, cwd=source)
    under = run("push", str(bare("under.git")), f"{REF}:refs/two", cwd=source)
    step(f"{git} push-own-name", "funny refname" in own.stderr and "funny refname" in under.stderr, (own.stderr, under.stderr))
    deep = run("push", str(bare("deep.git")), f"{REF}:refs/foo/bar", cwd=source)
    step(f"{git} push-under-refs", deep.returncode == 0, deep.stderr)

    mirror = bare("mirror.git")
    run("push", "--mirror", str(mirror), cwd=source)
    step(f"{git} mirror-skips", REF not in refs(mirror) and "refs/heads/main" in refs(mirror), refs(mirror))
    holder = bare("holder.git")
    run("fetch", "-q", str(source), f"{REF}:{REF}", cwd=holder)
    run("push", "--mirror", str(holder), cwd=source)
    step(f"{git} mirror-deletes", REF not in refs(holder), refs(holder))

    out, into, clone, fetch = (named("git push <remote>"), named("git fetch <remote>"), named("git clone --mirror"), named("git fetch <url>"))
    relay = bare("relay.git")
    done = command(out, source, remote=relay) if out else None
    step(f"{git} doc-copy-out", done is not None and done.returncode == 0 and len(refs(relay)) == 1, done.stderr if done else "no command")
    run("init", "-q", "back")
    done = command(into, work / "back", remote=relay) if into else None
    step(f"{git} doc-copy-in", done is not None and done.returncode == 0 and tip(work / "back") == board, done.stderr if done else "no command")
    done = run(*shlex.split(clone)[1:], "src", "mirrored.git") if clone else None
    step(f"{git} doc-clone", done is not None and done.returncode == 0 and tip(work / "mirrored.git") == board, done.stderr if done else "no command")
    run("init", "-q", "named")
    done = command(fetch, work / "named", url=source) if fetch else None
    step(f"{git} doc-fetch", done is not None and done.returncode == 0 and tip(work / "named") == board, done.stderr if done else "no command")


def main(args):
    if any(arg.startswith("-") for arg in args):
        print(__doc__, file=sys.stderr)
        return 2
    gits = args or sorted({shutil.which("git"), "/usr/bin/git"} - {None}, key=lambda path: path != shutil.which("git"))
    bullet = bullet_text()
    commands = re.findall(r"`(git [^`]+)`", bullet)
    for git in gits:
        work = pathlib.Path(tempfile.mkdtemp(prefix="board-travel-"))
        replay(git, work, commands)
        shutil.rmtree(work)
    missing = [phrase for phrase in SAYS if phrase not in bullet]
    claims = CLAIMS_SEND.findall(bullet)
    step("doc-words", not missing and not claims, (missing, claims))
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
