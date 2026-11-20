#!/usr/bin/env python3
"""Run `.github/check-repository.py` on a temporary git repository of three plugins and `.github` whose fixture runners log each run, one of the plugins naming `.github`. Print `ok <case>`
or `fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `same-files-once`: a second run on the same files runs no runner and its summary counts all five replayed;
- `one-plugin-runs`: a change to one plugin's file runs that plugin's runners, the runner that names `.github` and the runner of `.github`, no other;
- `root-file-runs`: a change to a file at the root runs every runner;
- `github-runs-all`: a change under `.github/` runs every runner;
- `untracked-file-runs`: a file not yet added to git runs the runners of its plugin and the one naming `.github`;
- `claude-plugin-file-runs`: a change under `.claude-plugin/` runs every runner;
- `second-runner-runs`: a failing second runner of a plugin whose first runner passed is not hidden by it;
- `fresh-runs`: `--fresh` runs every runner on the same files;
- `no-git-runs`: a folder that is no git checkout runs every runner on every call and keeps no memory;
- `failure-runs`: a failing runner runs on every call, and its `fixture` line is printed each time.

usage: replay-runner-cache.py"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

CHECK = pathlib.Path(__file__).resolve().parents[1] / "check-repository.py"
RUNNER = ("import os, pathlib, sys\nopen(os.environ['RUNNERS_LOG'], 'a').write('{name}\\n')\n"
          "sys.exit(1 if pathlib.Path('{name}', '{fail}').exists() else 0)\n")
results = {}


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[:900]}", flush=True)
    results[name] = ok


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="runner-cache-"))
    log = work.parent / f"{work.name}-runs.log"
    os.environ.update(HOME=str(work), RUNNERS_LOG=str(log), GIT_AUTHOR_NAME="probe", GIT_AUTHOR_EMAIL="probe@example.com",
                      GIT_COMMITTER_NAME="probe", GIT_COMMITTER_EMAIL="probe@example.com")
    for name in ("alpha", "beta", "gamma"):
        (work / name / "fixtures").mkdir(parents=True)
        (work / name / "fixtures" / "replay-one.py").write_text(RUNNER.format(name=name, fail="fail") + ("# reads .github and every plugin\n" if name == "gamma" else ""))
        (work / name / "notes.txt").write_text("one\n")
    (work / "alpha" / "fixtures" / "replay-two.py").write_text(RUNNER.format(name="alpha", fail="fail-two").replace("'alpha\\n'", "'alpha-two\\n'"))
    (work / ".github").mkdir()
    (work / ".github" / "notes.txt").write_text("one\n")
    (work / ".github" / "fixtures").mkdir()
    (work / ".github" / "fixtures" / "replay-one.py").write_text(RUNNER.format(name="github", fail="fail"))
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=work, check=True)
    subprocess.run(["git", "add", "."], cwd=work, check=True)

    def call(*options):
        log.write_text("")
        done = subprocess.run([sys.executable, str(CHECK), *options, str(work)], capture_output=True, text=True)
        return done.stdout, sorted(log.read_text().split())

    call()
    out, ran = call()
    step("same-files-once", ran == [] and "5 replayed" in out, (ran, out))
    (work / "alpha" / "notes.txt").write_text("two\n")
    out, ran = call()
    step("one-plugin-runs", ran == ["alpha", "alpha-two", "gamma", "github"], (ran, out))
    (work / "notes.txt").write_text("one\n")
    subprocess.run(["git", "add", "."], cwd=work, check=True)
    out, ran = call()
    step("root-file-runs", ran == ["alpha", "alpha-two", "beta", "gamma", "github"], (ran, out))
    (work / ".github" / "notes.txt").write_text("two\n")
    out, ran = call()
    step("github-runs-all", ran == ["alpha", "alpha-two", "beta", "gamma", "github"], (ran, out))
    (work / "alpha" / "new.txt").write_text("one\n")
    out, ran = call()
    step("untracked-file-runs", ran == ["alpha", "alpha-two", "gamma", "github"], (ran, out))
    (work / ".claude-plugin").mkdir()
    (work / ".claude-plugin" / "notes.txt").write_text("one\n")
    subprocess.run(["git", "add", "."], cwd=work, check=True)
    out, ran = call()
    step("claude-plugin-file-runs", ran == ["alpha", "alpha-two", "beta", "gamma", "github"], (ran, out))
    (work / "alpha" / "fail-two").write_text("")
    subprocess.run(["git", "add", "."], cwd=work, check=True)
    call()
    out, ran = call()
    step("second-runner-runs", "fixture alpha/fixtures/replay-two.py: exit 1" in out and ran == ["alpha-two"], (ran, out))
    (work / "alpha" / "fail-two").unlink()
    out, ran = call("--fresh")
    step("fresh-runs", ran == ["alpha", "alpha-two", "beta", "gamma", "github"], (ran, out))
    (work / "beta" / "fail").write_text("")
    subprocess.run(["git", "add", "."], cwd=work, check=True)
    call()
    out, ran = call()
    step("failure-runs", ran == ["beta"] and "fixture beta/fixtures/replay-one.py: exit 1" in out, (ran, out))
    (work / "beta" / "fail").unlink()
    plain = work.parent / f"{work.name}-plain"
    shutil.copytree(work, plain, ignore=shutil.ignore_patterns(".git"))
    log.write_text("")
    done = [subprocess.run([sys.executable, str(CHECK), str(plain)], capture_output=True, text=True) for _ in range(2)]
    ran = sorted(log.read_text().split())
    step("no-git-runs", ran == sorted(["alpha", "alpha-two", "beta", "gamma", "github"] * 2) and not list(plain.rglob("check-repository-passes")), (ran, [d.stdout for d in done]))
    print("PASS" if all(results.values()) else "FAIL")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
