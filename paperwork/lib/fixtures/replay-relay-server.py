#!/usr/bin/env python3
"""Replay the relay server of `../relay_server.py` from a skill script of no skill, over HTTP as a page and a session would.

usage: replay-relay-server.py

In a scratch folder a page holding lib's runtime, a style file beside it and a stand-in skill script that serves the page through lib:
routes: the token url serves the page, the token without its slash serves nothing, a file beside the page is served with its own type;
ids: three posted changes get the ids 1, 2 and 3, and the open event stream hears of them;
pending: two comments and one data change print `relay pending 3: 2 comment, 1 data`;
refusals: an ack whose ids are no list, a post of a list and a post with no length each get 400;
history: the page written to a second version and back to the first keeps three copies, each read only;
writes: a page rewritten every 0.2 s keeps no copy of a version that never lasted a whole poll;
cut: a page cut off before the runtime's closing marker is kept once, and the whole page written back is the version already kept;
idle: with a stream open, the server spends under 0.3 s of processor time in 3 s;
keep-alive: a stream told nothing hears no keep-alive before 14 s and one by 17 s;
port: a stand-in started on a port already taken exits 1, saying it cannot listen.
It prints `PASS <step>` or `FAIL <step>: <reason>` per step, then PASS or FAIL."""
import http.client
import json
import pathlib
import queue
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

LIB = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIB))
from relay_page import connect  # noqa: E402

BARE = '<!doctype html><html><head><link rel="stylesheet" href="style.css"></head><body><p data-id="idea">An idea</p></body></html>\n'
STYLE = "p { color: teal; }\n"
STAND_IN = f'''import pathlib
import sys

sys.path.insert(0, {str(LIB)!r})
from relay_server import serve

sys.exit(serve(pathlib.Path(sys.argv[1]).resolve(), int(sys.argv[2]), float(sys.argv[3])))
'''


class Server:
    """A stand-in serving PAGE, its stdout lines on a queue."""

    def __init__(self, script, page, port=0, quiet=0.5):
        self.process = subprocess.Popen([sys.executable, str(script), str(page), str(port), str(quiet)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.lines = queue.Queue()
        threading.Thread(target=lambda: [self.lines.put(line.strip()) for line in self.process.stdout], daemon=True).start()
        first = self.line(10)
        self.url = first.removeprefix("relay url: ") if first.startswith("relay url: ") else ""
        self.origin = "/".join(self.url.split("/")[:3])
        self.line(10)

    def line(self, seconds):
        try:
            return self.lines.get(timeout=seconds)
        except queue.Empty:
            return ""

    def call(self, route, body=None, headers=None, raw=None):
        """(status, content type, body bytes) of a GET, or of a POST when BODY or RAW is given."""
        data = raw if raw is not None else None if body is None else json.dumps(body).encode()
        sent = {"Origin": self.origin, "Content-Type": "application/json", **(headers or {})}
        try:
            with urllib.request.urlopen(urllib.request.Request(self.url + route, data=data, headers=sent), timeout=5) as reply:
                return reply.status, reply.headers.get("Content-Type"), reply.read()
        except urllib.error.HTTPError as error:
            return error.code, error.headers.get("Content-Type"), error.read()

    def stream(self):
        """A queue of (seconds since opened, line) the event stream sends."""
        heard, host, port = queue.Queue(), *self.origin.removeprefix("http://").split(":")
        connection = http.client.HTTPConnection(host, int(port), timeout=30)
        connection.request("GET", "/" + self.url.split("/")[3] + "/api/events")
        reply, start = connection.getresponse(), time.monotonic()

        def listen():
            try:
                for line in reply:
                    heard.put((time.monotonic() - start, line.decode().strip()))
            except OSError:
                pass
        threading.Thread(target=listen, daemon=True).start()
        return heard

    def stop(self):
        self.process.terminate()
        self.process.wait()


def drain(heard, seconds, limit=10):
    """Every line HEARD holds once SECONDS have passed with no new one, or once LIMIT seconds have passed, so a stream that never goes quiet fails its step."""
    got, end = [], time.monotonic() + limit
    while time.monotonic() < end:
        try:
            got.append(heard.get(timeout=min(seconds, max(0, end - time.monotonic()))))
        except queue.Empty:
            return got
    return got


def history(folder):
    return sorted((folder / "history").glob("*.html"))


def until(probe, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if probe():
            return True
        time.sleep(0.1)
    return False


def cpu(pid):
    """The processor seconds PID has spent, as ps prints them."""
    minutes, seconds = subprocess.run(["ps", "-o", "time=", "-p", str(pid)], capture_output=True, text=True).stdout.strip().split(":")[-2:]
    return int(minutes) * 60 + float(seconds)


def routes(server, folder):
    status, kind, body = server.call("")
    found = [] if status == 200 and kind.startswith("text/html") and body == (folder / "page.html").read_bytes() else [f"the token url served {status} {kind}"]
    bare = urllib.request.Request(server.url.rstrip("/"))
    try:
        urllib.request.urlopen(bare, timeout=5)
        found.append("the token without its slash served the page")
    except urllib.error.HTTPError as error:
        found += [] if error.code == 404 else [f"the token without its slash got {error.code}"]
    status, kind, body = server.call("style.css")
    found += [] if (status, kind, body) == (200, "text/css", STYLE.encode()) else [f"the style beside the page came as {status} {kind}"]
    return found


def ids(server, heard):
    drain(heard, 0.6)
    first = json.loads(server.call("api/changes", {"kind": "comment", "target": "idea", "payload": {"text": "Say more"}})[2])
    second = json.loads(server.call("api/changes", {"kind": "data", "target": "idea", "payload": {"path": "idea", "value": 1}})[2])
    third = json.loads(server.call("api/changes", {"kind": "comment", "target": "idea", "payload": {"text": "And shorter"}})[2])
    given = [one.get("id") for one in (first, second, third)]
    found = [] if given == [1, 2, 3] else [f"three changes got the ids {given}"]
    told = [line for _, line in drain(heard, 1.5)]
    return found + ([] if "event: changes" in told else [f"the event stream heard {told} after a change"])


def pending(server, folder):
    said = server.line(5)
    want = f"relay pending 3: 2 comment, 1 data for {(folder / 'page.html').resolve()}"
    return [] if said.startswith(want + " | ") else [f"the pending line reads {said[:120]!r}"]


def refusals(server):
    found = []
    status = server.call("api/changes/ack", {"ids": "12"})[0]
    found += [] if status == 400 else [f"an ack whose ids are a text got {status}"]
    status = server.call("api/changes", raw=b"[]")[0]
    found += [] if status == 400 else [f"a post of a list got {status}"]
    host, port = server.origin.removeprefix("http://").split(":")
    with socket.create_connection((host, int(port)), timeout=5) as sent:
        sent.sendall(f"POST /{server.url.split('/')[3]}/api/changes HTTP/1.1\r\nHost: {host}\r\nOrigin: {server.origin}\r\nContent-Type: application/json\r\n\r\n".encode())
        try:
            reply = sent.recv(64).decode(errors="replace")
        except socket.timeout:
            reply = "no reply in 5 s"
    found += [] if reply.startswith("HTTP/1.0 400") else [f"a post with no length got {reply.splitlines()[0] if reply else 'nothing'}"]
    return found


def versions(folder):
    page = folder / "page.html"
    first = page.read_text()
    page.write_text(first.replace("An idea", "A second idea"))
    found = [] if until(lambda: len(history(folder)) == 2, 5) else [f"a second version left {len(history(folder))} copies"]
    page.write_text(first)
    found += [] if until(lambda: len(history(folder)) == 3, 5) else [f"the first version again left {len(history(folder))} copies, not 3"]
    found += [f"{copy.name} has the mode {copy.stat().st_mode & 0o777:o}" for copy in history(folder) if copy.stat().st_mode & 0o777 != 0o444]
    return found


def writes(folder):
    page, before = folder / "page.html", len(history(folder))
    first = page.read_text()
    for n in range(12):
        page.write_text(first.replace("An idea", "An idea" + "!" * (n + 1)))
        time.sleep(0.2)
    page.write_text(first.replace("An idea", "A last idea"))
    until(lambda: len(history(folder)) > before, 5)
    time.sleep(1.2)
    kept = [copy.read_text() for copy in history(folder)[before:]]
    return [] if len(kept) == 1 and "A last idea" in kept[0] else [f"a page rewritten every 0.2 s left {len(kept)} new copies, not the last alone"]


def cut(folder):
    page, before = folder / "page.html", len(history(folder))
    whole = page.read_text()
    page.write_text(whole.split("<!-- /relay runtime -->")[0])
    found = [] if until(lambda: len(history(folder)) == before + 1, 5) else [f"a cut-off page left {len(history(folder)) - before} new copies, not 1"]
    page.write_text(whole)
    time.sleep(1.6)
    return found + ([] if len(history(folder)) == before + 1 else [f"the whole page written back after a cut left {len(history(folder)) - before} new copies, not 1"])


def idle(server, heard):
    drain(heard, 0.6)
    start = cpu(server.process.pid)
    time.sleep(3)
    spent = cpu(server.process.pid) - start
    return [] if spent < 0.3 else [f"the idle server spent {spent:.2f} s of processor time in 3 s"]


def keep_alive(heard, opened):
    time.sleep(max(0, opened + 17.5 - time.monotonic()))
    told = [(at, line) for at, line in drain(heard, 0.1) if line == ": keep-alive"]
    return [] if told and all(at >= 14 for at, _ in told) and told[0][0] <= 17 else [f"a quiet stream heard keep-alives at {[round(at, 1) for at, _ in told]} s"]


def port(script, folder):
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        done = subprocess.run([sys.executable, str(script), str(folder / "page.html"), str(taken.getsockname()[1]), "1"], capture_output=True, text=True, timeout=20)
    return [] if done.returncode == 1 and "relay cannot listen" in done.stderr else [f"a taken port exited {done.returncode}: {done.stderr.strip()[:200]}"]


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    results = []
    with tempfile.TemporaryDirectory() as scratch:
        root = pathlib.Path(scratch)
        script = root / "serve-page.py"
        script.write_text(STAND_IN)
        folders = [root / "page", root / "quiet"]
        for folder in folders:
            folder.mkdir()
            (folder / "page.html").write_text(BARE)
            (folder / "style.css").write_text(STYLE)
            connect(folder / "page.html")
        folder = folders[0]
        quiet = Server(script, folders[1] / "page.html")
        opened, still = time.monotonic(), quiet.stream()
        server = Server(script, folder / "page.html")
        try:
            if not server.url:
                results.append(("routes", ["the stand-in printed no url"]))
            else:
                heard = server.stream()
                results += [("routes", routes(server, folder)), ("ids", ids(server, heard)), ("pending", pending(server, folder)),
                            ("refusals", refusals(server)), ("history", versions(folder)), ("writes", writes(folder)), ("cut", cut(folder)),
                            ("idle", idle(server, heard))]
            results.append(("keep-alive", keep_alive(still, opened)))
        finally:
            server.stop()
            quiet.stop()
        results.append(("port", port(script, folders[1])))
    for step, reasons in results:
        print(f"FAIL {step}: {'; '.join(reasons)}" if reasons else f"PASS {step}")
    failed = any(reasons for _, reasons in results)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
