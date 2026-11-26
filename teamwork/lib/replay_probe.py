"""The harness every fixture runner of teamwork stands on: `Cases`, its `ok`/`fail` lines and verdict; `scratch`, a folder that removes itself;
and `Sandbox`, a scratch git repository with an environment isolated from this machine, the herdr state the runner declares served by
`fake-herdr/herdr`, stand-ins first on `PATH`, a clock the runner sets, lib code evaluated inside it and the heartbeat monitor run for a number of polls.
A call the fake herdr refuses fails the verdict, naming the call."""
import contextlib
import json
import os
import pathlib
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid

PLUGIN = pathlib.Path(__file__).resolve().parents[1]
FAKE_HERDR = PLUGIN / "skills" / "kick-off" / "fixtures" / "fake-herdr"
ROUTER = PLUGIN / "hooks" / "route-event.py"
MONITOR = PLUGIN / "monitors" / "print-team-gaps.py"
IDENTITY = {"GIT_AUTHOR_NAME": "probe", "GIT_AUTHOR_EMAIL": "probe@example.com",
            "GIT_COMMITTER_NAME": "probe", "GIT_COMMITTER_EMAIL": "probe@example.com"}
CHECK = "1. [check] **The probe prints PASS when it runs**: `basename PASS` prints `PASS`; on base `FAIL`.\n"
BODY = f"A summary.\n\n## Goal\n\nDo it.\n\nPath: caller: the probe run; meets: the owner\n\n## Definition of done\n\n{CHECK}"
GIT_CONFIG = "[user]\n\tname = probe\n\temail = probe@example.com\n[init]\n\tdefaultBranch = main\n"
# a session's own variables, which would let a script under test reach the live herdr, the session's transcript or another repository
SESSION_PREFIXES = ("HERDR_", "CLAUDE", "TEAMWORK_", "GH_", "GIT_")
KEPT = ("GIT_ALLOW_PROTOCOL",)  # set by a caller that bars the network
DETAIL = 1500  # characters of a fail line's detail, its head and its tail kept
_refusal_logs, _refused = [], []


class Cases:
    """A runner's cases: `step` prints `ok <case>` or `fail <case>: <detail>`, `finish` the last line `PASS` or `FAIL`, followed by WORDS, and returns
    the exit code; ONLY, when given, names the cases `wanted` runs."""

    def __init__(self, words="", only=None):
        self.words, self.only, self.failed = words, only, []

    def wanted(self, name):
        return not self.only or name in self.only

    def step(self, name, ok, detail=""):
        said = " ".join(str(detail).split())
        said = said if len(said) <= DETAIL else f"{said[:DETAIL // 2]} ... {said[-DETAIL // 2:]}"
        print(f"ok {name}" if ok else f"fail {name}: {said}", flush=True)
        if not ok:
            self.failed.append(name)
        return ok

    def finish(self):
        collect_refusals()
        for call in dict.fromkeys(_refused):
            self.step("herdr-calls", False, f"{call}: the fake herdr refused this call, which the plugin must not make")
        _refused.clear()
        print(("FAIL" if self.failed else "PASS") + (f" {self.words}" if self.words else ""), flush=True)
        return 1 if self.failed else 0


def fail(why):
    """1 after the verdict line `FAIL: WHY` of a runner with one verdict."""
    print(f"FAIL: {why}")
    return 1


def collect_refusals():
    """Keep the calls each sandbox's fake herdr refused, read once, since a scratch folder may go before the verdict."""
    for path in _refusal_logs:
        if path.exists():
            _refused.extend(path.read_text().splitlines())
            path.unlink()


@contextlib.contextmanager
def scratch(prefix="replay-"):
    """A new folder under the temporary folder, removed with all it holds on leaving."""
    folder = pathlib.Path(tempfile.mkdtemp(prefix=prefix)).resolve()
    try:
        yield folder
    finally:
        collect_refusals()
        shutil.rmtree(folder, ignore_errors=True)


def write_text(folder, name, text):
    path = pathlib.Path(folder) / name
    path.write_text(text)
    return path


def isolated(work):
    """This process's environment without a session's variables, with HOME and the Claude config in WORK, the config outside HOME so a reader
    that skips CLAUDE_CONFIG_DIR finds nothing, no system or global git config but an identity and `main` as the default branch, and no bytecode written."""
    work = pathlib.Path(work)
    (work / "home").mkdir(parents=True, exist_ok=True)
    (work / "config").mkdir(exist_ok=True)
    write_text(work, "gitconfig", GIT_CONFIG)
    kept = {key: value for key, value in os.environ.items() if not key.startswith(SESSION_PREFIXES) or key in KEPT}
    return {**kept, **IDENTITY, "HOME": str(work / "home"), "CLAUDE_CONFIG_DIR": str(work / "config"), "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": str(work / "gitconfig"), "PYTHONDONTWRITEBYTECODE": "1"}


def sh(*argv, cwd, environment, check=True, timeout=120):
    """The finished command ARGV; a nonzero exit raises RuntimeError with its output unless CHECK is false."""
    done = subprocess.run([str(word) for word in argv], cwd=cwd, env=environment, capture_output=True, text=True, timeout=timeout)
    if check and done.returncode:
        raise RuntimeError(f"{' '.join(map(str, argv))}: {done.stdout}{done.stderr}")
    return done


def agent(name, pane, status="idle", workspace="w1", **more):
    """A herdr agent NAME in pane `<WORKSPACE>:p<PANE>` of its own tab, a Claude session unless its name ends in `codex`."""
    return {"name": name, "pane_id": f"{workspace}:p{pane}", "tab_id": f"{workspace}:t{pane}", "workspace_id": workspace,
            "agent": "codex" if name.endswith("codex") else "claude", "agent_status": status, "interactive_ready": True, **more}


def as_claude(argv, options, folder):
    """ARGV run under a stand-in `claude` in FOLDER whose command line holds OPTIONS, such as `--name t-worker` or `-p probe`, since a script takes its
    session's name from the nearest `claude` above it; the options sit in the shell's own line, which then runs ARGV."""
    stand_in = pathlib.Path(folder) / "claude"
    stand_in.parent.mkdir(parents=True, exist_ok=True)
    if not stand_in.exists():
        stand_in.symlink_to("/bin/sh")
    return [str(stand_in), "-c", f': {shlex.join(map(str, options))} ; "$@"', "claude", *map(str, argv)]


class Group(subprocess.Popen):
    """A process in a session of its own, whose `kill` ends all it started, since the stand-in `claude` that wraps a script would otherwise leave it running."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, start_new_session=True, **kwargs)

    def kill(self):
        try:
            os.killpg(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


class Sandbox:
    """A scratch git repository `repository` on `main`, with one empty commit, in the folder WORK, and the `environment` its scripts run in: `isolated`,
    with `fake-herdr/herdr` serving the AGENTS `herdr` sets, recording each `/rename` in the Claude config `config`, and a `gh` stand-in that `gh` sets first on PATH, and the commit time `clock` sets."""

    def __init__(self, work, agents=(), commit=True):
        self.work = pathlib.Path(work)
        self.bin, self.state, self.calls = self.work / "bin", self.work / "herdr.json", self.work / "herdr.log"
        self.refused = self.work / "herdr-refused.log"
        self.bin.mkdir(parents=True, exist_ok=True)
        _refusal_logs.append(self.refused)
        self.environment = {**isolated(self.work), "PATH": f"{self.bin}{os.pathsep}{FAKE_HERDR}{os.pathsep}{os.environ['PATH']}",
                            "TEAMWORK_FAKE_HERDR_STATE": str(self.state), "TEAMWORK_FAKE_HERDR_LOG": str(self.calls),
                            "TEAMWORK_FAKE_HERDR_REFUSED": str(self.refused)}
        self.home, self.config = pathlib.Path(self.environment["HOME"]), pathlib.Path(self.environment["CLAUDE_CONFIG_DIR"])
        self.environment["TEAMWORK_FAKE_HERDR_CONFIG"] = str(self.config)
        self.herdr(agents)
        self.gh()
        self.repository = self.init(self.work / "repo", commit)

    def init(self, folder, commit=True):
        """FOLDER made a git repository on `main`, with one empty commit when COMMIT."""
        pathlib.Path(folder).mkdir(parents=True, exist_ok=True)
        self.git("init", "-q", "-b", "main", cwd=folder)
        if commit:
            self.git("commit", "-q", "--allow-empty", "-m", "start", cwd=folder)
        return pathlib.Path(folder)

    def git(self, *argv, cwd=None):
        """What `git ARGV` printed in CWD, the repository by default; a failure raises RuntimeError."""
        return sh("git", *argv, cwd=cwd or self.repository, environment=self.environment).stdout

    def herdr(self, agents, n=20):
        """The fake herdr's state set to AGENTS, each with a tab labelled by its name; new panes are numbered after N."""
        agents = list(agents)
        tabs = [{"tab_id": listed["tab_id"], "workspace_id": listed["workspace_id"], "label": listed.get("name") or ""} for listed in agents]
        self.state.write_text(json.dumps({"n": n, "agents": agents, "tabs": tabs}))
        return agents

    def herdr_state(self):
        return json.loads(self.state.read_text())

    def herdr_calls(self):
        """Each call the fake herdr took, as its argv."""
        return [json.loads(line) for line in self.calls.read_text().splitlines()] if self.calls.exists() else []

    def gh(self, pulls=None):
        """A `gh` that appends each call to `gh.log` in the sandbox and answers `gh pr list` with the JSON PULLS when given, refusing every other call."""
        answer = f"if [ \"$1 $2\" = 'pr list' ]; then cat '{write_text(self.work, 'gh-pulls.json', json.dumps(pulls))}'; exit 0; fi\n" if pulls is not None else ""
        write_text(self.bin, "gh", f"#!/bin/sh\necho \"$@\" >> '{self.work / 'gh.log'}'\n{answer}exit 1\n").chmod(0o755)

    def gh_calls(self):
        log = self.work / "gh.log"
        return log.read_text().splitlines() if log.exists() else []

    def clock(self, when):
        """Commits stamped at WHEN, an ISO time such as `2026-01-05T09:00:00Z`, or at the real time again when WHEN is None."""
        for key in ("GIT_AUTHOR_DATE", "GIT_COMMITTER_DATE"):
            self.environment.pop(key, None) if when is None else self.environment.update({key: when})

    def name_of(self, pane):
        return next((listed.get("name") for listed in self.herdr_state()["agents"] if listed.get("pane_id") == pane), None)

    def command(self, argv, pane=None, claude=None):
        """ARGV as a session runs it: under a stand-in `claude` started with the options CLAUDE, else as the name the fake herdr lists for PANE,
        since a script takes its writer's name only from a session started as that name; ARGV alone when neither gives one."""
        options = claude if claude is not None else (["--name", self.name_of(pane)] if pane and self.name_of(pane) else None)
        return as_claude(argv, options, self.work / "stand-in") if options is not None else [str(word) for word in argv]

    def session(self, name, *typed):
        """The `run` options of a session a person types into, started as NAME, whose transcript holds each row of TYPED: a prompt the person typed,
        or a (kind, text) pair, a message of that `origin.kind`, such as `peer` for one another session sent; each call writes it anew."""
        session_id = str(uuid.uuid5(uuid.NAMESPACE_URL, name))
        transcript = self.config / "projects" / "sandbox" / f"{session_id}.jsonl"
        transcript.parent.mkdir(parents=True, exist_ok=True)
        rows = [row if isinstance(row, tuple) else ("human", row) for row in typed]
        transcript.write_text("".join(json.dumps({"type": "user", "origin": {"kind": kind}, "message": {"role": "user", "content": text}}, separators=(",", ":")) + "\n"
                                      for kind, text in rows))
        return {"claude": ["--name", name], "CLAUDE_CODE_SESSION_ID": session_id}

    def decider(self, by, said="", manager="probe-manager"):
        """(the `run` options, the `decide` arguments) of a decision by BY: a session started as BY, or for `owner` the session MANAGER,
        in which the owner typed SAID, which `--owner-said` quotes."""
        if by != "owner":
            return {"claude": ["--name", by]}, []
        return self.session(manager, said), ["--by", "owner", "--owner-said", write_text(self.work, "owner-said.txt", said + "\n")]

    def run(self, argv, pane=None, claude=None, cwd=None, input=None, timeout=120, **variables):
        """ARGV finished as `command` runs it, from CWD (the repository by default), in pane PANE with VARIABLES added to the environment; a run past
        TIMEOUT seconds is ended with all it started and has returncode None."""
        environment = {**self.environment, **({"HERDR_PANE_ID": pane} if pane else {}), **{key: str(value) for key, value in variables.items()}}
        argv = self.command(argv, pane, claude)
        process = Group(argv, cwd=cwd or self.repository, env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            out, err = process.communicate(input, timeout=timeout)
            return subprocess.CompletedProcess(argv, process.returncode, out, err)
        except subprocess.TimeoutExpired:
            process.kill()
            out, err = process.communicate()
            return subprocess.CompletedProcess(argv, None, out, err)

    def python(self, script, *argv, **options):
        """The plugin script SCRIPT run with ARGV as `run` runs it."""
        return self.run([sys.executable, script, *argv], **options)

    def evaluate(self, code, *argv, cwd=None):
        """The JSON value the last line of CODE prints, CODE run by `run` with the plugin's lib importable and ARGV as its arguments."""
        done = self.run([sys.executable, "-c", code, *argv], cwd=cwd, PYTHONPATH=PLUGIN / "lib")
        if done.returncode:
            raise RuntimeError(f"{code}: {done.stderr.strip()}")
        return json.loads(done.stdout.splitlines()[-1])

    def monitor(self, pane, polls, log, script=MONITOR, **variables):
        """print-team-gaps.py, or a copy of it at SCRIPT, started as PANE's for POLLS polls a tenth of a second apart, its output in the file LOG."""
        return Monitor(self, [sys.executable, script, "--polls", polls], pane, log, variables)

    def route(self, event, pane="w1:p1", claude=None, cwd=None, **variables):
        """route-event.py's decoded answer to the hook EVENT, from the session in PANE; {} when it printed nothing."""
        out = self.run([ROUTER], pane, claude, cwd=cwd or event.get("cwd"), input=json.dumps(event), timeout=60, **variables).stdout
        return json.loads(out) if out.strip() else {}

    def start(self, argv, log, pane=None, claude=None, cwd=None, **variables):
        """ARGV started as `command` runs it, a `Group` writing its output to the file LOG, for a script that runs until killed."""
        environment = {**self.environment, **({"HERDR_PANE_ID": pane} if pane else {}), **{key: str(value) for key, value in variables.items()}}
        return Group(self.command(argv, pane, claude), cwd=cwd or self.repository, env=environment, stdout=open(log, "w"), stderr=subprocess.STDOUT)


class Monitor:
    """A print-team-gaps.py run, counted by the `herdr agent list` calls of its own log, `calls`, since each poll opens with one."""

    def __init__(self, sandbox, argv, pane, log, variables):
        self.log, self.calls = log, log.with_name(log.name + ".herdr")
        self.process = sandbox.start(argv, log, pane=pane,
                                     **{"TEAMWORK_MONITOR_POLL": "0.1", **variables, "TEAMWORK_FAKE_HERDR_LOG": self.calls})

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.process.kill()
        self.process.wait()

    def text(self):
        return self.log.read_text()

    def lists(self):
        return self.calls.read_text().count('["agent", "list"]') if self.calls.exists() else 0

    def until(self, done):
        """Whether DONE came true before the monitor ended."""
        while not done() and self.process.poll() is None:
            time.sleep(0.05)
        return done()

    def polls(self, count):
        """Whether a manager's monitor went through COUNT whole polls after now; its poll lists the sessions once, and once more before a line."""
        began = self.lists()
        return self.until(lambda: self.lists() >= began + 2 * count + 2)

    def end(self, timeout=60):
        """The monitor's exit code once it ends, None when it runs past TIMEOUT seconds and is ended."""
        try:
            return self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return None


def run_every(script, flag, names):
    """Run SCRIPT once per name as `SCRIPT FLAG <name>`, one at a time, print each failing run's last lines and `FAIL <name>`, then `PASS` or
    `FAIL`; 0 when all pass, else 1."""
    failed = []
    for name in names:
        done = subprocess.run([sys.executable, str(script), flag, name], capture_output=True, text=True)
        if done.returncode:
            failed.append(name)
            print("\n".join((done.stdout + done.stderr).strip().splitlines()[-20:] + [f"FAIL {name}"]))
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0
