"""Language packs: lang/<code>.json, chosen by book.lang. A pack overlays lang/en.json key by key; strings merge, and scripts, stop and catch_all add to English (books mix scripts)."""
import functools, json, os, re

from .const import ASSETS

LANG_DIR = os.path.join(ASSETS, 'lang')
UNION = ('scripts', 'stop', 'catch_all')


def _load(code):
    p = os.path.join(LANG_DIR, f'{code}.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


@functools.lru_cache(None)
def pack(code='en'):
    """The merged pack for a book language; an unknown code gets English rules with code set."""
    code = str(code or 'en').split('-')[0].lower()
    en = _load('en')
    own = (_load(code) if code != 'en' else None) or {}
    out = dict(en, **own)
    out['strings'] = dict(en['strings'], **own.get('strings', {}))
    for k in UNION:
        out[k] = list(own.get(k, [])) + list(en.get(k, []))
    out['code'], out['has_pack'] = code, code == 'en' or bool(own)
    out['catch_all_re'] = re.compile(r'^\s*(' + '|'.join(out['catch_all']) + r')[.。]?\s*$', re.I)
    return out




def native(L):
    """The book script's letters when it is not English, else None."""
    return L['scripts'][0]['letters'] if L['code'] != 'en' else None


def words_of(t, L):
    """Content words: letter runs of each script's minimum length, and numbers; stop words dropped."""
    rx = '|'.join(f"[{s['letters']}]{{{s['min']},}}" for s in L['scripts']) + r'|\d+(?:\.\d+)?'
    stop = set(L['stop'])
    return {w for w in re.findall(rx, t) if w.lower() not in stop}


def stems_of(t, L):
    """Word stems for echo checks: the first `stem` letters of each word (0 = the whole word, case-folded)."""
    out = set()
    for s in L['scripts']:
        for w in re.findall(f"[{s['letters']}]{{{s['min']},}}", t):
            out.add(w[:s['stem']] if s['stem'] else w.lower())
    return out


def final_sound(t, L):
    """v (vowel), l (liquid) or c (other consonant) ending of how a text is read aloud, for packs whose particles depend on it; None if unknown."""
    pt = L.get('particles')
    if not pt:
        return None
    t = t.rstrip(' )]»"\'.,')
    if not t:
        return None
    ch = t[-1]
    if pt.get('syllables') == 'hangul' and '가' <= ch <= '힣':
        j = (ord(ch) - 0xAC00) % 28
        return 'v' if j == 0 else 'l' if j == 8 else 'c'
    if ch == '%':
        return pt.get('percent')
    return dict(zip('0123456789', pt.get('digit_final', ''))).get(ch)
