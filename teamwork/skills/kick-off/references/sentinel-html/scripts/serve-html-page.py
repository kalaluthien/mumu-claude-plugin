#!/usr/bin/env python3
"""Serve one HTML page on 127.0.0.1 behind a random token as interactive-html-contract.md says: keep its comment threads, versions and proposals, hand each page event to a session as one line, and let the page reload when its file changes.

usage: serve-html-page.py <page.html> [--port <n>] [--prompt <session>]

The first stdout line is `page-threads url: <url>`, also written to `url.txt` beside the page, whose port and token a
restart reuses. Each event (a comment, an answer, an accept or reject, an undo, a page error, a changed contract) is saved as
`inbox/<n>.json` beside the page and printed as one line, `page-threads <kind> <n> on <anchor>: read its text and context in <json> | page: <page>`,
so a session that runs this script as its `Monitor` receives it; `--prompt <session>` also types that line into the
herdr session. Each version of the page file, whoever wrote it, is kept in `history/`, and the time each sentinel entry
first appeared in `stamps.json`, which the served page carries instead of the time an entry claims. A file beside the page is
served under the same token, so the page's own stylesheet, script or image loads; the server's own records are not. Each
script of the `page-drawing/` folder beside this script's folder is put into the served page; with that folder gone
the page is served as written."""
import datetime
import hashlib
import http.server
import json
import mimetypes
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse

BLOCK = re.compile(r'(<script\b(?=[^>]*\bid=["\']page-threads["\'])[^>]*>)(.*?)(</script>)', re.S | re.I)
ANCHOR = re.compile(r"[\w.:-]{1,80}")
HANDLED = ("do_GET", "do_POST", "log_message")  # http.server calls these by name
RECORDS = ("inbox", "history", "proposals", "url.txt", "stamps.json")
HERE = pathlib.Path(__file__).resolve().parent


def main(args):
    if not args or args[0].startswith("-"):
        return usage()
    page = pathlib.Path(args[0]).resolve()
    port, session = 0, None
    rest = args[1:]
    while rest:
        flag = rest.pop(0)
        if flag == "--port" and rest and rest[0].isdigit():
            port = int(rest.pop(0))
        elif flag == "--prompt" and rest and not rest[0].startswith("-"):
            session = rest.pop(0)
        else:
            return usage()
    if not page.is_file():
        return usage()
    folder = page.parent
    inbox, history, proposals = folder / "inbox", folder / "history", folder / "proposals"
    decided = history / "proposals"
    for each in (inbox, history, proposals, decided):
        each.mkdir(exist_ok=True)
    saved = folder / "url.txt"
    token = secrets.token_urlsafe(16)
    if saved.is_file():  # a restart, as when its Monitor expires and is armed again, keeps the url the open page polls
        old = saved.read_text().strip().split("/")
        port, token = port or int(old[2].split(":")[1]), old[3]
    drawing = "".join(f"<script>{each.read_text()}</script>" for each in sorted((HERE.parent / "page-drawing").glob("*.js")))
    contract = HERE.parent / "interactive-html-contract.md"
    check = HERE / "check-html-contract.py"
    stamps, undone = folder / "stamps.json", history / "undo.json"
    lock = threading.Lock()
    reported = set()

    def read_state(html):
        match = BLOCK.search(html)
        if not match:
            return {"threads": {}}
        return json.loads(match.group(2))

    def write_page(html, state):
        body = "\n" + json.dumps(state, ensure_ascii=False, indent=1).replace("<", "\\u003c") + "\n"
        match = BLOCK.search(html)
        if match:
            html = html[:match.start(2)] + body + html[match.end(2):]
        else:
            block = f'<script type="application/json" id="page-threads">{body}</script>\n'
            html = before_body(html, block)
        temporary = page.with_name(page.name + ".tmp")
        temporary.write_text(html)
        os.replace(temporary, page)
        keep()

    def keep():
        """Copy the page into history/ when this version is not kept yet, stamp each sentinel entry seen for the first time, and return the versions, oldest first."""
        for each in proposals.glob("*.html"):  # a proposal's Preview link outlives the file the sentinel removes once it is decided
            if not (decided / each.name).is_file() or (decided / each.name).stat().st_mtime_ns < each.stat().st_mtime_ns:
                shutil.copyfile(each, decided / each.name)
        digest = hashlib.sha256(page.read_bytes()).hexdigest()[:12]
        versions = sorted(history.glob("*.html"))
        if not versions or not versions[-1].name.endswith(f"-{digest}.html"):
            now = datetime.datetime.now()
            shutil.copy2(page, history / f"{now.strftime('%Y%m%dT%H%M%S%f')}-{digest}.html")  # the version keeps the time the page was written, which decide() compares
            versions = sorted(history.glob("*.html"))
            try:
                threads = read_state(page.read_text()).get("threads", {})
            except ValueError:
                threads = {}
            known = json.loads(stamps.read_text()) if stamps.is_file() else {}
            fresh = {str(entry["id"]): now.isoformat(timespec="seconds") for thread in threads.values() if isinstance(thread, list)
                     for entry in thread if isinstance(entry, dict) and entry.get("by") == "sentinel" and str(entry.get("id")) not in known}
            if fresh:
                stamps.write_text(json.dumps({**known, **fresh}, indent=1))
        return versions

    def content(path):
        """The digest of a page version without its thread block and whitespace, so neither a reply nor the block the server adds is a change to undo."""
        return hashlib.sha256(re.sub(r"\s+", "", BLOCK.sub("", path.read_text())).encode()).hexdigest()

    def next_id(state):
        """One counter for every event and owner entry: above each inbox record and each integer id in the threads."""
        numbers = [entry["id"] for thread in state.get("threads", {}).values() if isinstance(thread, list)
                   for entry in thread if isinstance(entry, dict) and isinstance(entry.get("id"), int)]
        return max([0] + [int(each.stem) for each in inbox.glob("*.json") if each.stem.isdigit()] + numbers) + 1

    def record(n, fields):
        path = inbox / f"{n}.json"
        path.write_text(json.dumps({**fields, "page": str(page), "url": url, "contract": str(contract)}, ensure_ascii=False, indent=1))
        return path

    def announce(kind, n, anchor, path):
        line = f"page-threads {kind} {n} on {anchor}: read its text and context in {path} | page: {page}"
        print(line, flush=True)
        if session:
            subprocess.run(["herdr", "agent", "prompt", session, line], capture_output=True)

    def comment(message):
        anchor, text = str(message["anchor"]), str(message["text"]).strip()
        if not text or not ANCHOR.fullmatch(anchor):
            return 400, None
        html = page.read_text()
        state = read_state(html)
        n = next_id(state)
        author = str(message.get("author") or "owner")[:40]
        entry = {"id": n, "by": author, "text": text, "replies_to": message.get("replies_to"),
                 "at": datetime.datetime.now().isoformat(timespec="seconds")}
        thread = state.setdefault("threads", {}).setdefault(anchor, [])
        delivered = author == "owner" or bool(re.search(r"@sentinel\b", text))  # another person's comment reaches the session only when it names it
        if not delivered:
            entry["quiet"] = True
        open_asks = [each for each in thread if each.get("by") == "sentinel" and each.get("ask") and not each.get("answered")]
        asked = next((each for each in open_asks if each.get("id") == message.get("replies_to")), None)
        if not asked and author == "owner" and message.get("replies_to") is None and open_asks:
            asked = open_asks[-1]  # a typed comment while the sentinel asks answers that ask
            entry["replies_to"] = asked["id"]
        if asked:
            asked["answered"] = text
        thread.append(entry)
        write_page(html, state)
        kind = "answer" if asked else "comment"
        path = record(n, {"kind": kind, "comment": n, "anchor": anchor, "text": text, "author": author,
                          "replies_to": entry["replies_to"], "selection": message.get("selection"),
                          "element": str(message.get("element") or "")[:4000], "thread": thread})
        if delivered:
            announce(kind, n, anchor, path)
        return 202, n

    def decide(message):
        """Accept or reject the proposal a reply carries; an accept swaps the proposal in, keeping the current threads."""
        reply, verdict = str(message.get("reply")), message.get("verdict")
        if verdict not in ("accept", "reject"):
            return 400, None
        html = page.read_text()
        state = read_state(html)
        found = [(anchor, entry) for anchor, thread in state.get("threads", {}).items() for entry in thread
                 if str(entry.get("id")) == reply and entry.get("proposal")]
        proposal = proposals / f"{reply}.html"
        if not found or found[0][1].get("decided") or (verdict == "accept" and not proposal.is_file()):
            return 409, None
        if verdict == "accept":
            versions = keep()
            digests = [content(each) for each in versions]
            changed = next((versions[i] for i in range(len(versions) - 1, 0, -1) if digests[i] != digests[i - 1]), None)
            if changed and proposal.stat().st_mtime_ns < changed.stat().st_mtime_ns:  # the proposal was written from an older page, so applying it would drop that change
                return 409, f"the page changed after proposal {reply} was written; ask for a new one"
        anchor, entry = found[0]
        entry["decided"] = verdict
        write_page(proposal.read_text() if verdict == "accept" else html, state)
        n = next_id(state)
        path = record(n, {"kind": verdict, "reply": reply, "anchor": anchor, "text": f"the owner chose {verdict} for proposal {reply}"})
        announce(verdict, n, anchor, path)
        return 202, n

    def undo(message):
        """Put back the page's content as it was before its newest content change, keeping the current threads; undo
        again, with no content change between, steps further back, since a reply alone changes no content."""
        versions = keep()
        digests = [content(each) for each in versions]
        cursor = json.loads(undone.read_text()) if undone.is_file() else {}
        start = len(versions) - 1
        if cursor.get("content") == digests[-1] and cursor.get("version") in [each.name for each in versions]:
            start = [each.name for each in versions].index(cursor["version"])
        earlier = next((i for i in range(start - 1, -1, -1) if digests[i] != digests[start]), None)
        if earlier is None:
            return 409, None
        state = read_state(page.read_text())
        write_page(versions[earlier].read_text(), state)
        undone.write_text(json.dumps({"version": versions[earlier].name, "content": digests[earlier]}))
        n = next_id(state)
        path = record(n, {"kind": "undo", "restored": str(versions[earlier]), "text": f"the owner undid a change, restoring {versions[earlier].name}"})
        announce("undo", n, "page", path)
        return 202, n

    def error(message):
        """A page that cannot read its own thread block, or draws badly, says so, so the session can repair it; one
        version of the page file is said once, since each open tab and the server's own check report the same break."""
        version = page.stat().st_mtime_ns
        if version in reported:
            return 202, None
        reported.add(version)
        try:
            state = read_state(page.read_text())
        except ValueError:
            state = {}
        n = next_id(state)
        path = record(n, {"kind": "error", "text": str(message.get("text"))[:2000]})
        announce("error", n, "page", path)
        return 202, n

    def breaks():
        """The lines check-html-contract.py prints for each way the page file breaks the contract."""
        out = subprocess.run([sys.executable, str(check), str(page)], capture_output=True, text=True).stdout
        return [line for line in out.splitlines() if line.startswith("break ")] + waiting()

    def waiting():
        """A break line for each undecided proposal whose changed page is not in proposals/ under its entry's id,
        since Accept has nothing to apply until the file is there."""
        try:
            threads = read_state(page.read_text()).get("threads", {})
        except ValueError:
            return []
        return [f"break proposal: entry {entry['id']} has no proposals/{entry['id']}.html; write the changed page there"
                for thread in threads.values() if isinstance(thread, list) for entry in thread
                if isinstance(entry, dict) and entry.get("proposal") and not entry.get("decided") and not (proposals / f"{entry.get('id')}.html").is_file()]

    def watch():
        """Keep each version the sentinel writes as it lands, so history and stamps miss no edit; say once, as an
        error, each new set of contract breaks a version holds, and say when the contract itself changed, since a
        session that read it once goes on answering by the old text."""
        seen, told, read = None, [], contract.stat().st_mtime_ns
        while True:
            try:
                now = page.stat().st_mtime_ns
                if now != seen:
                    with lock:
                        keep()
                        found = breaks()
                        if found and found != told:
                            error({"text": "the page breaks the contract; repair each: " + "; ".join(found)})
                        told = found
                    seen = now
                changed = contract.stat().st_mtime_ns
                if changed != read:
                    read = changed
                    with lock:
                        n = next_id(read_state(page.read_text()))
                        path = record(n, {"kind": "contract", "text": f"the contract changed; read {contract} again and answer by it from now on"})
                        announce("contract", n, "page", path)
            except (OSError, ValueError):
                pass
            time.sleep(0.5)

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, code, body=b"", kind="text/plain"):
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def route(self):
            parts = self.path.split("?")[0].split("/")
            if len(parts) < 3 or not secrets.compare_digest(parts[1], token):
                return None
            return urllib.parse.unquote("/".join(parts[2:]))

        def asked(self, name):
            """The value of one query field of the url, or None."""
            return (urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get(name) or [None])[0]

        def serve(self, path):
            with lock:
                keep()
            known = stamps.read_text() if stamps.is_file() else "{}"
            script = f"<script>window.pageThreadsStamps = {known.replace('<', chr(92) + 'u003c')};</script>{drawing}"
            html = before_body(path.read_text(), script)
            self.reply(200, html.encode(), "text/html; charset=utf-8")

        def preview(self, path, name):
            """A proposal as it would look, under a banner and without the live panel, since comments and Undo belong to
            the live page; the banner sits in the flow above the page, so it covers none of it."""
            banner = ('<div id="page-threads-preview" style="position:sticky;top:0;z-index:2147483001;background:#fff3c4;'
                      f'padding:6px 12px;font:14px sans-serif;border-bottom:1px solid #bb9">Preview of proposal {name}: '
                      'Accept or Reject it in its thread on the live page.</div>')
            html = path.read_text()
            body = re.search(r"<body\b[^>]*>", html, re.I)
            html = html[:body.end()] + banner + html[body.end():] if body else banner + html
            self.reply(200, html.encode(), "text/html; charset=utf-8")

        def do_GET(self):
            route = self.route()
            if route == "" and self.asked("proposal") is not None:
                # at the page's own url, so a link to a part stays in the preview and a file beside the page loads
                name = self.asked("proposal")
                kept = next((each for each in (proposals / f"{name}.html", decided / f"{name}.html")
                             if re.fullmatch(r"[\w.-]+", name) and each.is_file()), None)
                return self.preview(kept, name) if kept else self.reply(404)
            if route == "":
                return self.serve(page)
            if route == "version":
                return self.reply(200, str(page.stat().st_mtime_ns).encode())
            if route == "history":
                return self.reply(200, json.dumps([each.name for each in keep()]).encode(), "application/json")
            try:
                beside = (folder / route).resolve() if route else folder
                inside = beside.relative_to(folder.resolve()).parts
                # the file system may match a name in another letter case, so compare the file reached, not its spelling
                if beside.is_file() and not any(part.startswith(".") for part in inside) and not any(
                        (folder / each).exists() and os.path.samefile(folder / each, folder / inside[0]) for each in RECORDS):
                    return self.reply(200, beside.read_bytes(), mimetypes.guess_type(beside.name)[0] or "application/octet-stream")
            except (ValueError, OSError):
                pass
            self.reply(404)

        def do_POST(self):
            route = self.route()
            actions = {"comment": comment, "decide": decide, "undo": undo, "error": error}
            if route not in actions or self.headers.get("Content-Type") != "application/json":
                return self.reply(404)
            origin = self.headers.get("Origin")
            if origin and origin != url.split("/", 3)[0] + "//" + url.split("/", 3)[2]:
                return self.reply(403)
            try:
                message = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                with lock:
                    code, n = actions[route](message)
            except (ValueError, KeyError, TypeError, AttributeError):
                return self.reply(400)
            self.reply(code, str(n or "").encode())

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/{token}/"
    saved.write_text(url + "\n")
    keep()
    threading.Thread(target=watch, daemon=True).start()
    print(f"page-threads url: {url}", flush=True)
    server.serve_forever()


def before_body(html, insert):
    """Put insert before the page's last </body>, since an earlier one can sit inside a script's string."""
    at = html.lower().rfind("</body>")
    return html[:at] + insert + html[at:] if at >= 0 else html + insert


def usage():
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
