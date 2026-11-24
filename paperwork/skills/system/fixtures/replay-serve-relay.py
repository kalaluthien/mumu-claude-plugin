#!/usr/bin/env python3
"""Run the relay path on a scratch copy of a bare page: connect it, serve it, queue a comment, see it pending and acknowledge it.

usage: replay-serve-relay.py

It prints one line per step, then PASS or FAIL."""
import json
import pathlib
import queue
import subprocess
import sys
import tempfile
import threading
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
BARE = '<!doctype html><html><body><p data-id="idea">An idea</p></body></html>'


def call(url, body=None):
    request = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Origin": url.split("/", 3)[0] + "//" + url.split("/")[2], "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as reply:
        return json.loads(reply.read())


def lines(stream):
    """A function returning the stream's next line, or "" when none comes within 10 seconds, so a missing line fails a step."""
    waiting = queue.Queue()
    threading.Thread(target=lambda: [waiting.put(line) for line in stream], daemon=True).start()

    def next_line():
        try:
            return waiting.get(timeout=10).strip()
        except queue.Empty:
            return ""
    return next_line


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as scratch:
        page = pathlib.Path(scratch) / "page.html"
        page.write_text(BARE)
        steps = []
        connect = subprocess.run([sys.executable, str(SCRIPTS / "connect-page.py"), str(page)], capture_output=True, text=True)
        check = subprocess.run([sys.executable, str(SCRIPTS / "check-page.py"), str(page)], capture_output=True, text=True)
        steps.append(("connect-page writes the runtime and check-page prints follows",
                      connect.returncode == 0 and "<!-- relay runtime -->" in page.read_text() and check.stdout.strip() == "follows"))
        steps.append(("SKILL.md routes to the relay playbook", "(references/relay.md)" in (HERE.parent / "SKILL.md").read_text()
                      and (HERE.parent / "references" / "relay.md").is_file()))
        server = subprocess.Popen([sys.executable, str(SCRIPTS / "serve-relay.py"), str(page), "--port", "0", "--quiet", "1"],
                                  stdout=subprocess.PIPE, text=True)
        try:
            read = lines(server.stdout)
            first = read()
            url = first.removeprefix("relay url: ")
            steps.append(("serve-relay prints its url", first.startswith("relay url: ")))
            steps.append(("serve-relay prints the page's file url", read() == "relay page: " + page.resolve().as_uri()))
            if first.startswith("relay url: "):
                change = call(url + "api/changes", {"kind": "comment", "target": "idea", "payload": {"text": "Say more"}})
                steps.append(("a posted comment is queued", change.get("id") is not None))
                pending = read()
                steps.append(("a pending line follows", pending.startswith("relay pending 1")))
                queued = call(url + "api/changes")
                queued = queued.get("changes", queued) if isinstance(queued, dict) else queued
                ids = [each["id"] for each in queued]
                call(url + "api/changes/ack", {"ids": ids})
                left = call(url + "api/changes")
                left = left.get("changes", left) if isinstance(left, dict) else left
                steps.append(("an acknowledged comment leaves the queue", len(ids) == 1 and not left))
        finally:
            server.terminate()
            server.wait()
    for name, right in steps:
        print(f"{'PASS' if right else 'FAIL'} {name}")
    right = len(steps) == 7 and all(right for _, right in steps)
    print("PASS" if right else "FAIL")
    return 0 if right else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
