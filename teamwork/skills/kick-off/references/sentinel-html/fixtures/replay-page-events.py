#!/usr/bin/env python3
"""Replay the page server's events by HTTP on throwaway pages, from a copy of this playbook's folder with its page drawing folder deleted, and print one `PASS <case>` or `FAIL <case>: <why>` line per case, then PASS or FAIL.

usage: replay-page-events.py [<case>]
usage: replay-page-events.py --record

No session answers and no browser runs. The copy is the folder above this one, without the one folder `sentinel-html.md`
names as the page drawing, so every case shows the connection working alone. `--record` writes
`recorded-page-payloads.json` beside this script: the status and body the server gives each route in one fixed
exchange, times and versions made constant, which the page drawing is replayed against; the `recorded-payloads` case
fails when the server no longer gives them.

Cases: a `</body>` inside a page's script string, a thread block whose attributes come in another order, one id
counter for comments and errors, Undo stepping back through two content changes across a reply-only edit, a guest note
kept quiet, a typed comment answering an open ask, event lines that carry no comment text, reply times stamped by the server,
a proposal preview served without the live panel, no Undo of the block the server adds to a page that had none, a file
beside the page served and the server's records refused, a comment on an anchor named in Korean, a contract break in
the page file said once as an error, a changed contract said as an event, one error event for one version of the page
file however many tabs report it, a preview that loads the page's files, a proposal with no file said as a break, an
Accept of a proposal older than the page's last content change refused with its reason, the server reached on
127.0.0.1 alone, no route answered without the token, the contract check's own fixtures, the page served as written
with no drawing, each file named for what it is, and the drawing folder and the rest naming none of each other's files."""
import json
import pathlib
import queue
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
PLAYBOOK = ROOT.parent / (ROOT.name + ".md")
RECORDED = HERE / "recorded-page-payloads.json"
TIME = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d")
BLOCK = re.compile(r'(<script\b(?=[^>]*\bid=["\']page-threads["\'])[^>]*>)(.*?)(</script>)', re.S | re.I)


class Server:
    def __init__(self, folder, html, home):
        self.page = folder / "page.html"
        self.page.write_text(html)
        self.home = home
        self.process = subprocess.Popen([sys.executable, str(home / "scripts" / "serve-html-page.py"), str(self.page)], stdout=subprocess.PIPE, text=True)
        self.lines = queue.Queue()
        threading.Thread(target=lambda: [self.lines.put(line.rstrip("\n")) for line in self.process.stdout], daemon=True).start()
        self.url = self.lines.get(timeout=10).split("url: ")[1]
        time.sleep(0.6)

    def post(self, route, body):
        request = urllib.request.Request(self.url + route, json.dumps(body).encode(), {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, response.read().decode()
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode()

    def get(self, route=""):
        with urllib.request.urlopen(self.url + route, timeout=10) as response:
            return response.read().decode()

    def code(self, route):
        try:
            with urllib.request.urlopen(self.url + route, timeout=10) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code

    def events(self, wait=1.0):
        time.sleep(wait)
        found = []
        while not self.lines.empty():
            found.append(self.lines.get())
        return found

    def state(self):
        return json.loads(BLOCK.search(self.page.read_text()).group(2))

    def write(self, html):
        self.page.write_text(html)
        time.sleep(1.2)

    def stop(self):
        self.process.terminate()
        self.process.wait(timeout=10)


def page(body, block='{"threads": {}}', open_tag='<script type="application/json" id="page-threads">'):
    return f'<!doctype html><html><body>{body}\n{open_tag}{block}</script>\n</body></html>\n'


def body_in_script(server):
    original = server.page.read_text()
    served = server.get()
    at = original.rfind("</body>")
    if not (served.startswith(original[:at]) and served.endswith(original[at:])):
        return "the served page changed outside the script put before the last </body>"
    code, _ = server.post("comment", {"anchor": "intro", "text": "hello"})
    after = server.page.read_text()
    if code != 202 or 'var s = "</body>";' not in after or after.count('id="page-threads"') != 1:
        return f"after a comment ({code}) the page's own script or its one block was not intact"


def attribute_order(server):
    code, _ = server.post("comment", {"anchor": "intro", "text": "ordered"})
    blocks = BLOCK.findall(server.page.read_text())
    if code != 202 or len(blocks) != 1 or "ordered" not in blocks[0][1]:
        return f"a comment ({code}) left {len(blocks)} blocks"


def one_counter(server):
    _, comment = server.post("comment", {"anchor": "intro", "text": "first"})
    _, error = server.post("error", {"text": "drawn badly"})
    kinds = {path.stem: json.loads(path.read_text())["kind"] for path in (server.page.parent / "inbox").glob("*.json")}
    if comment != "2" or error != "3" or kinds != {"2": "comment", "3": "error"}:
        return f"comment id {comment}, error id {error}, inbox {kinds}"


def undo_steps(server):
    one = server.page.read_text()
    server.write(one.replace("<p>v1</p>", "<p>v2</p>"))
    two = server.page.read_text()
    server.write(two.replace("<p>v2</p>", "<p>v3</p>"))
    state = server.state()
    state["threads"]["intro"] = [{"id": 1, "by": "owner", "text": "hi", "replies_to": None}, {"id": "1.1", "by": "sentinel", "text": "hello", "replies_to": 1}]
    three = server.page.read_text()
    server.write(three.replace(BLOCK.search(three).group(2), json.dumps(state)))
    seen = []
    for _ in range(3):
        code, _ = server.post("undo", {})
        time.sleep(0.8)
        text = server.page.read_text()
        seen.append((code, re.search(r"<p>(v\d)</p>", text).group(1), len(server.state()["threads"].get("intro", []))))
    if seen != [(202, "v2", 2), (202, "v1", 2), (409, "v1", 2)]:
        return f"undo three times gave {seen}"


def quiet_guest(server):
    server.events(0)
    server.post("comment", {"anchor": "intro", "text": "guest note", "author": "guest"})
    quiet = server.events()
    server.post("comment", {"anchor": "intro", "text": "@sentinel guest ask", "author": "guest"})
    loud = server.events()
    entries = server.state()["threads"]["intro"]
    if quiet or len(loud) != 1 or not entries[0].get("quiet") or entries[1].get("quiet"):
        return f"quiet note gave {len(quiet)} events, the @sentinel one {len(loud)}; quiet marks {[e.get('quiet') for e in entries]}"


def typed_answer(server):
    server.events(0)
    server.post("comment", {"anchor": "intro", "text": "Ship it"})
    lines = server.events()
    ask = server.state()["threads"]["intro"][0]
    if ask.get("answered") != "Ship it" or len(lines) != 1 or not lines[0].startswith("page-threads answer "):
        return f"ask answered {ask.get('answered')!r}, events {lines}"


def no_text(server):
    server.events(0)
    server.post("comment", {"anchor": "intro", "text": "secret words here"})
    lines = server.events()
    if len(lines) != 1 or "secret words" in lines[0] or not re.fullmatch(r"page-threads comment \d+ on intro: read its text and context in \S+\.json \| page: \S+", lines[0]):
        return f"event lines {lines}"


def stamped(server):
    state = server.state()
    state["threads"]["intro"] = [{"id": 1, "by": "owner", "text": "hi", "replies_to": None},
                                 {"id": "1.1", "by": "sentinel", "text": "hello", "replies_to": 1, "at": "2001-01-01T00:00:00"}]
    html = server.page.read_text()
    before = time.time()
    server.write(html.replace(BLOCK.search(html).group(2), json.dumps(state)))
    stamps = json.loads((server.page.parent / "stamps.json").read_text()) if (server.page.parent / "stamps.json").is_file() else {}
    claimed = time.mktime(time.strptime(stamps.get("1.1", "2001-01-01T00:00:00"), "%Y-%m-%dT%H:%M:%S"))
    if abs(claimed - before) > 3 or '"1.1"' not in server.get().split("window.pageThreadsStamps = ")[-1][:200]:
        return f"stamps {stamps}, written at {time.strftime('%H:%M:%S', time.localtime(before))}"


def plain_preview(server):
    (server.page.parent / "proposals" / "1.1.html").write_text(server.page.read_text().replace("Intro", "Proposed"))
    shown = server.get("?proposal=1.1")
    if "pageThreads" in shown or "page-threads-panel" in shown or "Preview of proposal 1.1" not in shown or "Proposed" not in shown:
        return "the preview carries the live panel or lacks its banner"
    if "position:fixed" in shown or not re.search(r'<body><div id="page-threads-preview"', shown):
        return "the banner is not in the flow at the top of the body, so it covers the page's first lines"
    if server.code("?proposal=9.9") != 404 or server.code("?proposal=..%2Fpage") != 404:
        return "a proposal that does not exist is not refused"


def added_block(server):
    code, _ = server.post("comment", {"anchor": "intro", "text": "first"})
    time.sleep(0.8)
    undo, _ = server.post("undo", {})
    if code != 202 or undo != 409:
        return f"after the server added the block, undo answered {undo}, not 409"


def sibling_file(server):
    folder = server.page.parent
    (folder / "style.css").write_text("h1 { color: rgb(1, 2, 3); }")
    (folder / ".hidden").write_text("hidden")
    (folder / "sub").mkdir()
    server.post("comment", {"anchor": "intro", "text": "a record to keep in"})
    (folder.parent / (folder.name + "-outside.txt")).write_text("outside")
    try:
        shown = server.get("style.css")
        routes = ("url.txt", "stamps.json", "inbox/1.json", "history/", f"..%2F{folder.name}-outside.txt", "missing.css",
                  "Inbox/1.json", "INBOX/1.json", "URL.TXT", "sub/../Inbox/1.json", "sub%2F..%2Finbox%2F1.json", "x%00y", ".hidden")
        refused = {route: server.code(route) for route in routes}
    finally:
        (folder.parent / (folder.name + "-outside.txt")).unlink()
    if "rgb(1, 2, 3)" not in shown or set(refused.values()) != {404}:
        return f"style.css gave {shown[:40]!r}; the routes to refuse gave {refused}"


def korean_anchor(server):
    code, _ = server.post("comment", {"anchor": "h-설치-방법", "text": "hello"})
    bad, _ = server.post("comment", {"anchor": "h 설치", "text": "hello"})
    if code != 202 or bad != 400 or len(server.state()["threads"].get("h-설치-방법", [])) != 1:
        return f"a comment on a Korean anchor got {code}, one on an anchor with a space {bad}"


def contract_break(server):
    server.events(0)
    state = {"threads": {"intro": [{"id": 1, "by": "owner", "text": "hi", "replies_to": None}, {"id": "9.1", "by": "sentinel", "text": "accepted", "replies_to": 9}]}}
    html = server.page.read_text()
    broken = html.replace(BLOCK.search(html).group(2), json.dumps(state))
    server.write(broken)
    first = server.events()
    server.write(broken + "\n")
    again = server.events()
    records = [json.loads(path.read_text()) for path in (server.page.parent / "inbox").glob("*.json")]
    named = [record for record in records if record["kind"] == "error" and "break replies" in record["text"] and "9.1" in record["text"]]
    if len(first) != 1 or not first[0].startswith("page-threads error ") or again or len(named) != 1:
        return f"a reply to no comment gave events {first}, the same break again {again}, {len(named)} records naming it"


def contract_change(server):
    folder = server.page.parent
    home = folder / "code"
    shutil.copytree(server.home, home, ignore=shutil.ignore_patterns("fixtures", "__pycache__"))
    (folder / "second").mkdir()
    second = Server(folder / "second", server.page.read_text(), home)
    try:
        quiet = second.events()
        with (home / "interactive-html-contract.md").open("a") as contract:
            contract.write("\n")
        lines = second.events(1.5)
    finally:
        second.stop()
    if quiet or len(lines) != 1 or not re.fullmatch(r"page-threads contract \d+ on page: read its text and context in \S+\.json \| page: \S+", lines[0]):
        return f"events before the change {quiet}, after it {lines}"


def error_once(server):
    server.events(0)
    codes = [server.post("error", {"text": "the block does not parse"})[0] for _ in range(3)]
    lines = server.events()
    server.write(server.page.read_text() + "\n")
    later, _ = server.post("error", {"text": "the block does not parse"})
    if codes != [202, 202, 202] or len(lines) != 1 or len(server.events()) != 1:
        return f"three reports of one version got {codes} and {len(lines)} events, and the next version's report was {later}"


def preview_files(server):
    (server.page.parent / "proposals" / "1.1.html").write_text('<!doctype html><html><head><link rel="stylesheet" href="style.css"></head><body><h1>Proposed</h1><a href="#part">part</a></body></html>')
    shown = server.get("?proposal=1.1")
    if "<base" in shown or server.code("proposal/1.1") != 404:
        return "the preview is not at the page's own url, so a link to a part leaves it or style.css loads from another folder"


def decided_preview(server):
    proposal = server.page.parent / "proposals" / "1.1.html"
    proposal.write_text(server.page.read_text().replace("Intro", "Proposed"))
    server.write(server.page.read_text() + "\n")
    proposal.unlink()
    if server.code("?proposal=1.1") != 200 or "Proposed" not in server.get("?proposal=1.1"):
        return "the preview of a proposal whose file was removed after its decision is gone"


def proposal_file(server):
    server.events(0)
    state = {"threads": {"intro": [{"id": 1, "by": "owner", "text": "propose", "replies_to": None}, {"id": "1.1", "by": "sentinel", "text": "Proposal", "replies_to": 1, "proposal": True}]}}
    html = server.page.read_text()
    (server.page.parent / "proposals" / "1.html").write_text(html)
    server.write(html.replace(BLOCK.search(html).group(2), json.dumps(state)))
    lines = server.events()
    records = [json.loads(path.read_text()) for path in (server.page.parent / "inbox").glob("*.json")]
    named = [record for record in records if record["kind"] == "error" and "proposals/1.1.html" in record["text"]]
    if len(lines) != 1 or len(named) != 1:
        return f"a proposal whose file sits under another name gave events {lines} and {len(named)} records naming the file to write"
    (server.page.parent / "proposals" / "1.html").rename(server.page.parent / "proposals" / "1.1.html")
    server.write(server.page.read_text() + "\n")
    if server.events():
        return "a proposal with its file was still reported"


PROPOSED = '{"threads": {"intro": [{"id": 1, "by": "owner", "text": "propose a new intro", "replies_to": null, "at": "2026-01-01T00:00:00"}, {"id": "1.1", "by": "sentinel", "text": "A new intro", "replies_to": 1, "proposal": true}]}}'


def stale_accept(server):
    proposal = server.page.parent / "proposals" / "1.1.html"
    proposal.write_text(server.page.read_text().replace("Intro", "Proposed"))
    time.sleep(0.1)
    server.write(server.page.read_text().replace("<p>v1</p>", "<p>v2</p>"))
    code, why = server.post("decide", {"reply": "1.1", "verdict": "accept"})
    kept = "<p>v2</p>" in server.page.read_text() and "decided" not in json.dumps(server.state())
    if code != 409 or "changed after proposal 1.1" not in why or not kept:
        return f"an Accept of a proposal older than the page's last change got {code} {why!r}, the change kept: {kept}"
    proposal.write_text(server.page.read_text().replace("Intro", "Proposed"))
    code, _ = server.post("decide", {"reply": "1.1", "verdict": "accept"})
    text = server.page.read_text()
    if code != 202 or "Proposed" not in text or "<p>v2</p>" not in text:
        return f"an Accept of a proposal written after that change got {code}"


def local_only(server):
    if not server.url.startswith("http://127.0.0.1:"):
        return f"the url is {server.url.split('/')[2]}"
    port = int(server.url.split(":")[2].split("/")[0])
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))  # no packet is sent: this only asks which address the machine would use
        other = probe.getsockname()[0]
    except OSError:
        other = "127.0.0.1"
    finally:
        probe.close()
    if other.startswith("127."):
        return None
    try:
        socket.create_connection((other, port), timeout=2).close()
    except OSError:
        return None
    return f"the server answers on {other}, not on 127.0.0.1 alone"


def token_everywhere(server):
    host, token = server.url.split("/")[2], server.url.split("/")[3]
    codes = {}
    for route in ("", "version", "history", "wrong/", "wrong/version", f"{token[:-1]}/", f"x/{token}/"):
        try:
            with urllib.request.urlopen(f"http://{host}/{route}", timeout=10) as response:
                codes[route] = response.status
        except urllib.error.HTTPError as error:
            codes[route] = error.code
    request = urllib.request.Request(f"http://{host}/wrong/comment", b'{"anchor": "intro", "text": "x"}', {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            codes["post"] = response.status
    except urllib.error.HTTPError as error:
        codes["post"] = error.code
    server.post("comment", {"anchor": "intro", "text": "hello"})
    record = json.loads(next((server.page.parent / "inbox").glob("*.json")).read_text())
    saved = (server.page.parent / "url.txt").read_text().strip()
    if set(codes.values()) != {404} or len(token) < 16 or saved != server.url or record["url"] != server.url:
        return f"routes with no token or a wrong one gave {codes}; the token is {len(token)} letters; url.txt holds the url: {saved == server.url}"


def contract_fixtures(server):
    done = subprocess.run([sys.executable, str(server.home / "scripts" / "check-html-contract.py"), "fixtures"], capture_output=True, text=True)
    last = (done.stdout.strip().splitlines() or [""])[-1]
    if done.returncode or last != "PASS":
        return f"check-html-contract.py fixtures ended {done.returncode}: {last}"


def served_as_written(server):
    served = server.get()
    scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", served, re.S)
    added = [each for each in scripts if each not in server.page.read_text()]
    if len(added) != 1 or not added[0].startswith("window.pageThreadsStamps = "):
        return f"with no page drawing the served page gained {len(added)} scripts beside its reply times"


def exchange(server):
    """The status and body of each route in one fixed exchange, times and versions made constant."""
    proposal = server.page.parent / "proposals" / "1.1.html"
    proposal.write_text(server.page.read_text().replace("Intro", "Proposed"))
    time.sleep(0.1)
    server.write(server.page.read_text().replace("<p>v1</p>", "<p>v2</p>"))
    steps = [("GET", "", None), ("GET", "version", None), ("POST", "comment", {"anchor": "intro", "text": "hello"}),
             ("POST", "decide", {"reply": "1.1", "verdict": "accept"}), ("POST", "undo", {}), ("POST", "error", {"text": "drawn badly"}),
             ("POST", "comment", {"anchor": "in tro", "text": "hello"})]
    found = []
    for method, route, body in steps:
        status, text = (200, server.get(route)) if method == "GET" else server.post(route, body)
        text = "0" if route == "version" else TIME.sub("2026-01-01T00:00:00", text)
        found.append({"method": method, "route": route, "sent": body, "status": status, "body": text})
    return found


def recorded_payloads(server):
    found = exchange(server)
    if not RECORDED.is_file() or json.loads(RECORDED.read_text()) != found:
        return f"the server's answers differ from {RECORDED.name}; record them again with --record and replay the page drawing"


def file_names(server):
    """The names are read in the playbook's own folder, since the copy has lost the drawing folder."""
    drawing = ROOT / drawing_name()
    files = [path for path in ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    inside = [path for path in files if drawing in path.parents]
    outside = [path for path in files if drawing not in path.parents] + [PLAYBOOK]
    gaps = [f"{path.name} is one word" for path in files if len(re.findall(r"[a-z0-9]+", path.stem.lower())) < 2]
    gaps += [f"{path.name} of the drawing folder has sentinel in its name" for path in inside if "sentinel" in path.name.lower()]
    if not inside:
        gaps.append(f"{drawing.name}/ holds no file")
    for path in inside:
        text = path.read_text(errors="replace")
        gaps += [f"{path.name} names {other.name}" for other in outside if other.name in text]
        gaps += [f"{path.name} names {word}" for word in (ROOT.name, "../", "scripts/", "fixtures/") if word in text]
    for path in outside:
        text = path.read_text(errors="replace")
        gaps += [f"{path.name} names {other.name} of the drawing folder" for other in inside if other.name in text]
    if gaps:
        return "; ".join(sorted(set(gaps)))


def drawing_name():
    """The one folder the playbook names as the page drawing."""
    found = set(re.findall(r"\*\*Page drawing\*\*: \[" + re.escape(ROOT.name) + r"/([\w-]+)/\]", PLAYBOOK.read_text()))
    if len(found) != 1:
        raise ValueError(f"{PLAYBOOK.name} names {len(found)} folders as the page drawing")
    return found.pop()


ASK = '{"threads": {"intro": [{"id": "0.1", "by": "sentinel", "text": "Which?", "replies_to": null, "ask": {"options": ["Ship it", "Hold"]}}]}}'
CASES = [
    ("body-in-script", page('<h1 id="intro">Intro</h1><script>var s = "</body>";</script>'), body_in_script),
    ("attribute-order", page('<h1 id="intro">Intro</h1>', open_tag='<script id="page-threads" type="application/json">'), attribute_order),
    ("one-counter", page('<h1 id="intro">Intro</h1>', '{"threads": {"intro": [{"id": 1, "by": "owner", "text": "seed", "replies_to": null}]}}'), one_counter),
    ("undo-steps", page('<h1 id="intro">Intro</h1><p>v1</p>'), undo_steps),
    ("quiet-guest", page('<h1 id="intro">Intro</h1>'), quiet_guest),
    ("typed-answer", page('<h1 id="intro">Intro</h1>', ASK), typed_answer),
    ("no-text", page('<h1 id="intro">Intro</h1>'), no_text),
    ("stamped", page('<h1 id="intro">Intro</h1>'), stamped),
    ("plain-preview", page('<h1 id="intro">Intro</h1>'), plain_preview),
    ("added-block", '<!doctype html><html><body><h1 id="intro">Intro</h1>\n</body></html>\n', added_block),
    ("sibling-file", page('<h1 id="intro">Intro</h1>'), sibling_file),
    ("korean-anchor", page("<h1>설치 방법</h1>"), korean_anchor),
    ("contract-break", page('<h1 id="intro">Intro</h1>'), contract_break),
    ("contract-change", page('<h1 id="intro">Intro</h1>'), contract_change),
    ("error-once", page('<h1 id="intro">Intro</h1>'), error_once),
    ("preview-files", page('<h1 id="intro">Intro</h1>'), preview_files),
    ("decided-preview", page('<h1 id="intro">Intro</h1>'), decided_preview),
    ("proposal-file", page('<h1 id="intro">Intro</h1>'), proposal_file),
    ("stale-accept", page('<h1 id="intro">Intro</h1><p>v1</p>', PROPOSED), stale_accept),
    ("local-only", page('<h1 id="intro">Intro</h1>'), local_only),
    ("token-everywhere", page('<h1 id="intro">Intro</h1>'), token_everywhere),
    ("contract-fixtures", page('<h1 id="intro">Intro</h1>'), contract_fixtures),
    ("served-as-written", page('<h1 id="intro">Intro</h1>'), served_as_written),
    ("recorded-payloads", page('<h1 id="intro">Intro</h1><p>v1</p>', PROPOSED), recorded_payloads),
    ("file-names", page('<h1 id="intro">Intro</h1>'), file_names),
]


def main(args):
    record = args == ["--record"]
    if not record and (len(args) > 1 or args and args[0] not in [name for name, _, _ in CASES]):
        print(__doc__, file=sys.stderr)
        return 2
    chosen = [each for each in CASES if record and each[0] == "recorded-payloads" or not record and (not args or each[0] == args[0])]
    failed = 0
    with tempfile.TemporaryDirectory() as scratch:
        home = pathlib.Path(scratch) / ROOT.name
        shutil.copytree(ROOT, home, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.rmtree(home / drawing_name())
        for name, html, case in chosen:
            with tempfile.TemporaryDirectory() as folder:
                server = Server(pathlib.Path(folder), html, home)
                try:
                    if record:
                        RECORDED.write_text(json.dumps(exchange(server), ensure_ascii=False, indent=1) + "\n")
                        why = None
                    else:
                        why = case(server)
                except Exception as error:
                    why = f"{type(error).__name__}: {error}"
                finally:
                    server.stop()
            failed += bool(why)
            print(f"FAIL {name}: {why}" if why else f"PASS {name}")
    print(f"FAIL: {failed} of {len(chosen)} cases" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
