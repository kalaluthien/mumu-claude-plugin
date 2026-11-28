#!/usr/bin/env python3
"""Run teamwork in a repository that holds a `.teamwork/settings.json` which sets each key it once read, and print `ok <case>` or `fail <case>: <detail>` per case,
then `PASS` or `FAIL`, and exit 1 on any failure:
- `tools-off`: a manager started with `--allow Workflow` is accepted and runs with `Artifact` off, so the file's empty `manager` list changes nothing;
- `scope`: the scope label of a task that has an `area:` label and two `scope:` labels is the `scope:` one, so the file's `scope_prefix` changes nothing, the first of two `scope:` labels in sorted order.

usage: replay-no-settings.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
failed = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[:900]}", flush=True)
    if not ok:
        failed.append(name)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="no-settings-")).resolve()
    repository = work / "repository"
    (repository / ".teamwork").mkdir(parents=True)
    (repository / ".teamwork" / "settings.json").write_text(json.dumps({"scope_prefix": "area:", "tools_off": {"manager": []}}))
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    state, log = work / "state.json", work / "log"
    state.write_text(json.dumps({"n": 10, "tabs": [], "agents": []}))
    log.write_text("")
    environment = {**os.environ, "PATH": f"{HERE / 'fake-herdr'}:{os.environ['PATH']}", "TEAMWORK_FAKE_HERDR_STATE": str(state), "TEAMWORK_FAKE_HERDR_LOG": str(log)}
    done = subprocess.run([str(ROOT / "skills/kick-off/scripts/start-session.py"), "fresh-manager", str(repository), "fresh", "--model", "opus", "--effort", "low", "--allow", "Workflow"],
                          cwd=repository, env=environment, capture_output=True, text=True)
    words = " ".join(word for call in (json.loads(line) for line in log.read_text().splitlines()) if call[:2] == ["agent", "start"] for word in call)
    step("tools-off", done.returncode == 0 and "Artifact" in words, [done.returncode, done.stderr])
    done = subprocess.run([sys.executable, "-c", "import task_estimate; print(task_estimate.group_key(['area:x', 'scope:z', 'scope:y']))"], cwd=repository,
                          env={**os.environ, "PYTHONPATH": str(ROOT / "lib")}, capture_output=True, text=True)
    step("scope", done.stdout.strip() == "scope:y", [done.stdout, done.stderr])
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
