#!/usr/bin/env python3
"""Run every teamwork fixture runner offline under an empty home, and on a copy of the plugin whose herdr caller makes a call the plugin never makes,
printing `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS fixture harness` or `FAIL fixture harness`, and exiting 1 on any failure.

usage: replay-fixture-harness.py [<root>]

ROOT is the repository whose teamwork runners run, this one by default. Cases:
- `every`: each runner of teamwork, as `.github/list-unreached.py` defines one, other than this one, runs from ROOT with HOME a new empty folder, no Claude
  config, proxies pointing at a closed local port, git taking only `file` urls and a `curl`, `wget`, `gh`, `claude` and `herdr` on PATH that refuse,
  and must exit 0 within RUNNER_SECONDS; a failure names the runner and its last line;
- `strict`: in a copy of ROOT's teamwork whose `session_herdr.sessions` lists agents by `herdr agent list --json`, a call the plugin never makes,
  the copy's replay-own-readers.py, which reads the sessions, runs offline as in `every` but from a scratch folder, and must exit non-zero with a `fail` line
  naming that call."""
import concurrent.futures
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

HERE = pathlib.Path(__file__).resolve()
RUNNER = re.compile(r"(?:^|/)fixtures/replay-[^/]+\.(?:py|ts)$")  # as `.github/list-unreached.py` defines a runner
FIXTURES_CALL = re.compile(r"^(?:usage:)? *\S+\.py fixtures\b", re.M)
RUNNER_SECONDS = 900
REFUSING = ("curl", "wget", "gh", "claude", "herdr")
SESSIONS_CALL = ('listed = remember(run("herdr", "agent", "list"))', 'listed = remember(run("herdr", "agent", "list", "--json"))')
STRICT_RUNNER = "skills/kick-off/fixtures/replay-own-readers.py"


def runners(plugin):
    """Each runner of PLUGIN as (its path from the plugin's folder, its argv), this one left out."""
    found = []
    for path in sorted(plugin.rglob("*")):
        relative = path.relative_to(plugin).as_posix()
        if path.name == HERE.name or "__pycache__" in path.parts or not path.is_file():
            continue
        if RUNNER.search(relative):
            found.append((relative, ["bun", str(path)] if path.suffix == ".ts" else [sys.executable, str(path)]))
        elif re.search(r"(?:^|/)scripts/[^/]+\.py$", relative) and FIXTURES_CALL.search(path.read_text(errors="replace")):
            found.append((relative, [sys.executable, str(path), "fixtures"]))
    return found


def closed_port():
    """A local port nothing listens on, so a proxied request fails at once."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def offline(work):
    """An environment with HOME a new empty folder under WORK, no Claude config, no route out and refusing stand-ins first on PATH."""
    refusing = work / "refusing"
    refusing.mkdir(parents=True, exist_ok=True)
    for name in REFUSING:
        replay_probe.write_text(refusing, name, f"#!/bin/sh\necho '{name}: a fixture runner may not reach the network or a live session' >&2\nexit 1\n").chmod(0o755)
    home = work / "home"
    home.mkdir()
    proxy = f"http://127.0.0.1:{closed_port()}"
    environment = {key: value for key, value in os.environ.items() if key not in ("CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME", "NO_PROXY", "no_proxy")}
    return {**environment, "HOME": str(home), "PATH": f"{refusing}{os.pathsep}{os.environ['PATH']}", "GIT_ALLOW_PROTOCOL": "file", "PYTHONDONTWRITEBYTECODE": "1",
            **{key: proxy for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")}}


def run_offline(argv, cwd, work):
    """(exit code, last line, output) of ARGV run offline from CWD; a run past RUNNER_SECONDS is ended and has exit code None."""
    process = replay_probe.Group(argv, cwd=cwd, env=offline(work), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    try:
        out = process.communicate(timeout=RUNNER_SECONDS)[0]
        code = process.returncode
    except subprocess.TimeoutExpired:
        process.kill()
        out, code = process.communicate()[0], None
    lines = out.strip().splitlines() or [""]
    return code, lines[-1][:300], out


def every(root, cases):
    with replay_probe.scratch("fixture-harness-") as work:
        calls = runners(root / "teamwork")

        def run(index_call):
            index, (path, argv) = index_call
            return path, run_offline(argv, root, work / str(index))

        with concurrent.futures.ThreadPoolExecutor(6) as pool:
            results = list(pool.map(run, enumerate(calls)))
    failed = [f"{path}: {'no end in ' + str(RUNNER_SECONDS) + ' s' if code is None else 'exit ' + str(code)}, {last}" for path, (code, last, _) in results if code != 0]
    cases.step("every", calls and not failed, "; ".join(failed) or "no runner found")


def strict(root, cases):
    with replay_probe.scratch("fixture-harness-strict-") as work:
        copy = work / "teamwork"
        shutil.copytree(root / "teamwork", copy, ignore=shutil.ignore_patterns("__pycache__"))
        module = copy / "lib" / "session_herdr.py"
        text = module.read_text()
        module.write_text(text.replace(*SESSIONS_CALL, 1))
        code, last, out = run_offline([sys.executable, str(copy / STRICT_RUNNER)], work, work / "run")
    call = SESSIONS_CALL[1].split("run(", 1)[1].split(")")[0].replace('"', "").replace(", ", " ")
    named = [line for line in out.splitlines() if line.startswith(("fail ", "FAIL")) and call in line]
    cases.step("strict", SESSIONS_CALL[0] in text and code not in (0, None) and named,
               f"the copy's {STRICT_RUNNER} gave exit {code}, {last}; no fail line names `{call}`" if SESSIONS_CALL[0] in text else f"session_herdr.py holds no `{SESSIONS_CALL[0]}`")


def main(args):
    if len(args) > 1 or args and (args[0].startswith("-") or not pathlib.Path(args[0], "teamwork").is_dir()):
        print(__doc__, file=sys.stderr)
        return 2
    root = pathlib.Path(args[0]).resolve() if args else HERE.parents[4]
    cases = replay_probe.Cases("fixture harness")
    every(root, cases)
    strict(root, cases)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
