"""What the scenario scripts of `skills/kick-off/fixtures/` and `hooks/fixtures/` share: a `gh` that logs and fails, a git
identity, a fake herdr, a file written in a scratch folder, a script run in a repository, the hook router fed one event,
and the failure line."""
import json
import os
import subprocess
import sys

IDENTITY = {"GIT_AUTHOR_NAME": "probe", "GIT_AUTHOR_EMAIL": "probe@example.com",
            "GIT_COMMITTER_NAME": "probe", "GIT_COMMITTER_EMAIL": "probe@example.com"}
HOLD = "DECIDED: probe-worker holds this.\n\n```teamwork\nholders: probe-worker\n```\n"
CHECK = "1. [check] **The probe prints PASS when it runs**: `echo ok` prints `ok`; on base nothing.\n"
GIT_CONFIG = "[user]\n\tname = probe\n\temail = probe@example.com\n[init]\n\tdefaultBranch = main\n"


def fail(why):
    print(f"FAIL: {why}")
    return 1


def write_text(folder, name, text):
    path = folder / name
    path.write_text(text)
    return path


def write_git_config(work):
    return write_text(work, "gitconfig", GIT_CONFIG)


def stub_gh(work):
    """The folder `WORK/bin` holding a `gh` that appends its arguments to `WORK/gh.log` and exits 1, so a call is seen and gets no answer."""
    folder = work / "bin"
    folder.mkdir(exist_ok=True)
    stub = write_text(folder, "gh", f'#!/bin/sh\necho "$@" >> {work}/gh.log\nexit 1\n')
    stub.chmod(0o755)
    return folder


def sh(*argv, cwd, environment, check=True, timeout=120):
    """The finished command ARGV; a nonzero exit raises RuntimeError with its output unless CHECK is false."""
    done = subprocess.run([str(word) for word in argv], cwd=cwd, env=environment, capture_output=True, text=True, timeout=timeout)
    if check and done.returncode:
        raise RuntimeError(f"{' '.join(map(str, argv))}: {done.stdout}{done.stderr}")
    return done


def run_python(script, repo, environment, *argv):
    return subprocess.run([sys.executable, str(script), *map(str, argv)], cwd=repo, capture_output=True, text=True, env=environment)


def fake_herdr(work, agents):
    """The folder `WORK/bin` holding a `herdr` that answers every call with AGENTS as the session list."""
    folder = work / "bin"
    folder.mkdir(exist_ok=True)
    stub = write_text(folder, "herdr", f"#!/bin/sh\necho '{json.dumps({'result': {'agents': agents}})}'\n")
    stub.chmod(0o755)
    return folder


def route_event(router, event, stubs):
    """The hook router's decoded answer to EVENT, run as the pane `p1` with the folder STUBS first on `PATH`."""
    environment = {**os.environ, "PATH": f"{stubs}:{os.environ['PATH']}", "HERDR_PANE_ID": "p1"}
    out = subprocess.run([str(router)], input=json.dumps(event), capture_output=True, text=True, env=environment).stdout
    return json.loads(out) if out.strip() else {}
