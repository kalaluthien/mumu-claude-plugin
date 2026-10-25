"""Put a reviewed book.html on a host and record what went there; publish-book.py is its command line.
"""
import argparse, datetime, hashlib, json, os, re, shutil, sys

from .const import PUBLISH_BOOK
TARGETS = ('file', 'static', 'claude-artifact')
ARTIFACT_MAX = 16 * 1024 * 1024  # the Artifact page limit
HEAD_TAGS = (r'<!doctype html>\s*', r'<html[^>]*>\s*', r'</html>\s*', r'<head>\s*', r'</head>\s*', r'<body[^>]*>\s*', r'</body>\s*', r'<meta charset="utf-8">\s*', r'<meta name="viewport"[^>]*>\s*')


class PublishError(Exception):
    pass


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:16]


def build_path(d):
    p = os.path.join(d, 'book.html')
    if not os.path.exists(p):
        raise PublishError('book.html not found; run `make-book.py build` and pass the review gate first')
    return p


def records(d):
    p = os.path.join(d, 'publish.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def record(d, target, url, digest=None, dry=False):
    r = dict(target=target, url=url, sha=digest or sha(build_path(d)), at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'))
    if dry:
        return f'would record {json.dumps(r)}'
    j = records(d)
    j[target] = r
    json.dump(j, open(os.path.join(d, 'publish.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return f'recorded {target} {url} sha {r["sha"]}'


def current(d):
    """Targets whose record matches the current build."""
    s = sha(build_path(d))
    return [k for k, r in records(d).items() if r.get('sha') == s]


def _copy(src, dst, dry):
    if dry:
        return f'would copy {src} -> {dst} (sha {sha(src)})'
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    shutil.copyfile(src, dst)
    if sha(dst) != sha(src):
        raise PublishError(f'{dst} differs from the build after copying')
    return f'copied to {dst}'


def host_warning(d):
    """A line when the book's scripts call a host capability (`.use("NAME")`): off the Artifact host these features have nothing to call and break."""
    caps = capabilities(d)
    if not caps:
        return ''
    return f'warning: book scripts call host capabilities ({", ".join(caps)}) via .use("..."); outside the Artifact host those features break (guard them or leave them out)'


def pub_file(d, to, dry):
    src = build_path(d)
    msg = _copy(src, to, dry)
    w = host_warning(d)
    return msg + '\n' + record(d, 'file', os.path.abspath(to), dry=dry) + ('\n' + w if w else '')


def pub_static(d, to, url, dry):
    src = build_path(d)
    msg = _copy(src, os.path.join(to, 'index.html'), dry)  # the build is self-contained: one file serves the whole book
    w = host_warning(d)
    return msg + '\n' + record(d, 'static', url or os.path.abspath(to), dry=dry) + ('\n' + w if w else '')


def capabilities(d):
    """Artifact runtime capabilities the book's scripts use: any receiver's .use("NAME") or .use('NAME') -> {NAME: {}}."""
    from .dom import read_js
    return {m[1]: {} for m in sorted(set(re.findall(r"""\.\s*use\(\s*(['"])(\w+)\1""", read_js(d))))}


def pub_artifact(d, dry):
    from .plan import Plan
    src = build_path(d)
    page = open(src, encoding='utf-8').read()
    for pat in HEAD_TAGS:  # the Artifact host wraps the page in its own document skeleton
        page = re.sub(pat, '', page, count=1, flags=re.IGNORECASE)
    if len(page.encode('utf-8')) > ARTIFACT_MAX:
        raise PublishError(f'page is {len(page.encode("utf-8")) >> 20} MB, over the 16 MB Artifact limit; move large figures out or split the book')
    plan = Plan(os.path.join(d, 'book.json'))
    slug = re.sub(r'[^\w-]+', '-', str(plan.book.get('doc_title') or plan.book.get('title') or 'book')).strip('-')[:40] or 'book'
    out = os.path.join(os.path.abspath(d), '.publish', 'claude-artifact', slug + '.html')
    if not dry:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, 'w', encoding='utf-8').write(page)
    last = records(d).get('claude-artifact', {}).get('url')
    call = {'action': 'publish', 'file_path': out}
    if last:
        call['url'] = last
    else:
        call['icon'] = 'book'
    caps = capabilities(d)
    if caps:
        call['capabilities'] = caps
    if plan.book.get('goal'):
        call['description'] = str(plan.book['goal'])[:200]
    lines = [('(dry run: the page file is not written) ' if dry else '') + 'Call the Artifact tool with:', json.dumps(call, ensure_ascii=False),
             f'then: {sys.executable} {PUBLISH_BOOK} record claude-artifact {os.path.abspath(d)} --url URL_FROM_THE_RESULT']
    return '\n'.join(lines)


def status(d):
    s = sha(build_path(d))
    rs = records(d)
    if not rs:
        return f'build {s}; no publish records'
    return '\n'.join([f'build {s}'] + [f'{k:16} {r.get("url")} sha {r.get("sha")} {r.get("at")} ' + ('current' if r.get('sha') == s else 'STALE') for k, r in rs.items()])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('file'); s.add_argument('dir', nargs='?', default='.'); s.add_argument('--to', required=True); s.add_argument('--dry-run', action='store_true')
    s = sub.add_parser('static'); s.add_argument('dir', nargs='?', default='.'); s.add_argument('--to', required=True); s.add_argument('--url'); s.add_argument('--dry-run', action='store_true')
    s = sub.add_parser('claude-artifact'); s.add_argument('dir', nargs='?', default='.'); s.add_argument('--dry-run', action='store_true')
    s = sub.add_parser('record'); s.add_argument('target', choices=TARGETS); s.add_argument('dir', nargs='?', default='.'); s.add_argument('--url', required=True); s.add_argument('--sha')
    s = sub.add_parser('status'); s.add_argument('dir', nargs='?', default='.')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'file':
            print(pub_file(a.dir, a.to, a.dry_run))
        elif a.cmd == 'static':
            print(pub_static(a.dir, a.to, a.url, a.dry_run))
        elif a.cmd == 'claude-artifact':
            print(pub_artifact(a.dir, a.dry_run))
        elif a.cmd == 'record':
            print(record(a.dir, a.target, a.url, a.sha))
        else:
            print(status(a.dir))
        return 0
    except PublishError as e:
        print(f'error: {e}', file=sys.stderr)
        return 2

