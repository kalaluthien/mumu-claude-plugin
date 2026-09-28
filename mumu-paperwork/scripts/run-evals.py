#!/usr/bin/env python3
"""Run the plugin's evals, then grade the page of each page case's run with check.py outside the eval sandbox.

usage: run-evals.py [claude plugin eval options, --json <path> included]
Headless Chrome cannot start inside the sandbox, which denies binding its profile's socket, so a page case, one whose
graders read an .html file, gets a `check.py` grader here: the run's directory is kept, check.py runs on the page the
run wrote, and the run passes only when check.py does. Each run's verdict is printed, the kept directories removed, and
the result, with these graders, written to the --json path when one is given.
Exit 0 every run passed, 1 a run failed or scored below the threshold, 2 the eval could not run.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK = ROOT / "skills" / "typesetting" / "scripts" / "check.py"


def pages(case):
    """The .html files a case's graders read."""
    return sorted({g["config"]["target"]["path"] for g in case["graders"]
                   if isinstance(g.get("config", {}).get("target"), dict) and g["config"]["target"].get("source") == "file"
                   and g["config"]["target"]["path"].endswith(".html")})


def kept(run):
    """The directory a run was kept in, or None: its trace sits in <dir>/out/."""
    return pathlib.Path(run["tracePath"]).parents[1] if run.get("tracePath") else None


def written(run, page):
    """Where the run wrote `page`: its cwd, sealed in the kept directory."""
    return kept(run) / "sealed" / "home" / "cwd" / page if kept(run) else None


def score(run):
    """(passed, score) of a run from its scored graders, each by its weight."""
    scored = [g for g in run["graders"] if g.get("scored", True)]
    total = sum(g.get("weight", 1) for g in scored)
    return all(g["passed"] for g in scored), (sum(g.get("weight", 1) for g in scored if g["passed"]) / total if total else 1)


def grade(result, check):
    """`result` with a check.py grader on each with-arm run of each page case, its run and case scores redone;
    check(path or None) gives (passed, explanation)."""
    for case in result["cases"]:
        runs = case["arms"].get("with", [])
        for page in pages(case):
            for run in runs:
                ok, why = check(written(run, page))
                run["graders"].append({"name": f"check.py {page}", "passed": ok, "weight": 1, "explanation": why,
                                       "withOnly": False, "scored": True})
                run["passed"], run["score"] = score(run)
        if pages(case) and runs:
            case["aggregates"]["score"] = sum(r["score"] for r in runs) / len(runs)
            case["aggregates"]["passRate"] = sum(r["passed"] for r in runs) / len(runs)
    return result


def check(page):
    """(passed, its FAIL lines or last line) of check.py on `page`, opening the sealed directory it sits in."""
    if page is None:
        return False, "no kept run directory"
    sealed = page.parents[2]
    for d in (sealed.parent, sealed):
        if d.exists():
            os.chmod(d, 0o700)
    if not page.is_file():
        return False, f"no {page.name}"
    r = subprocess.run([sys.executable, str(CHECK), str(page)], capture_output=True, text=True)
    lines = r.stdout.splitlines() + r.stderr.splitlines()
    fails = [line for line in lines if "FAIL" in line and line != "FAIL"]
    return r.returncode == 0, "; ".join(fails) or (lines[-1] if lines else f"exit {r.returncode}")


def remove(result):
    """Delete each run's kept directory, which the eval left read-only."""
    for case in result["cases"]:
        for runs in case["arms"].values():
            for run in runs:
                d = kept(run)
                if d and d.exists():
                    for p in [d, *d.rglob("*")]:
                        if p.is_dir() and not p.is_symlink():
                            os.chmod(p, 0o700)
                    shutil.rmtree(d, ignore_errors=True)


def main(args):
    out = None
    if "--json" in args:
        i = args.index("--json")
        out = args[i + 1] if i + 1 < len(args) and not args[i + 1].startswith("-") else "-"
        del args[i:i + (2 if out != "-" else 1)]
    with tempfile.TemporaryDirectory() as d:
        raw = pathlib.Path(d) / "result.json"
        code = subprocess.run(["claude", "plugin", "eval", str(ROOT), "--keep-temp", "--json", str(raw), *args]).returncode
        if not raw.is_file():
            print("run-evals.py: the eval wrote no result", file=sys.stderr)
            return 2
        result = grade(json.loads(raw.read_text()), check)
    remove(result)
    failed = False
    for case in result["cases"]:
        for page in pages(case):
            for i, run in enumerate(case["arms"].get("with", []), 1):
                g = next(g for g in run["graders"] if g["name"] == f"check.py {page}")
                failed |= not g["passed"]
                print(f"{case['name']} run {i} check.py {page} " + ("pass" if g["passed"] else f"FAIL: {g['explanation']}"))
    if out == "-":
        print(json.dumps(result, indent=2))
    elif out:
        pathlib.Path(out).write_text(json.dumps(result, indent=2))
    return 2 if code == 2 else 1 if code or failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
