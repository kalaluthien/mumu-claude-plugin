"""Run one external command and return its stdout, raising `RuntimeError` with its output when it fails."""
import subprocess


def run(*argv, cwd=None, stdin=None):
    """stdout of `argv`, raising with its stderr and stdout when it cannot start or exits non-zero."""
    try:
        done = subprocess.run(argv, cwd=cwd, input=stdin, capture_output=True, text=True)
    except OSError as e:
        raise RuntimeError(f"{argv[0]}: {e}") from e
    if done.returncode != 0:
        raise RuntimeError(f"{' '.join(argv)}: {' '.join(s.strip() for s in (done.stderr, done.stdout) if s.strip())}")
    return done.stdout
