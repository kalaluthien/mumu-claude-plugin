"""The checks a contract's prose must pass, whatever the contract's shape: each reads texts and names by where they sit and returns
its breaks as (where, rule, message)."""
import re

from tex_mathml import SUBSET, formulas, mathml, unformulated

REFERENCE = re.compile(r"\{([a-z0-9-]+)\}")
STYLE = re.compile(r"#(?:[0-9a-fA-F]{6}|(?=[0-9a-fA-F]{0,2}[a-fA-F])[0-9a-fA-F]{3})\b|\b(?:rgba?|hsla?|oklch)\(|\b\d+(?:\.\d+)?px\b|\b[xy]\s*=\s*-?\d"
                   r"|\b(?:color|background|background-color|left|top|right|bottom|width|height|margin|padding|font-size|font-family|font-weight|border|opacity|z-index)\s*:\s*\S")
MARKUP = re.compile(r"<\s*[A-Za-z/!?][^<>]{0,30}>?")
PARTICLE = (r"(?:(?:이라는|이라고|으로서|으로써|에서는|에서도|에게서|으로는|으로도|이라면|입니다|이며|이고|이나|이란|이든|으로|에서|에게|에는|에도|까지|부터|처럼|보다|라는|라고|로서|로써|로는|로도"
            r"|은|는|이|가|을|를|의|에|와|과|도|만|로|며|고|나|란|든)(?![가-힣]))?")
KOREAN = re.compile(r"[ㄱ-ㆎ가-힣]")
PAIRED = re.compile(r"\}(은|는|이|가|을|를|과|와|으로|로)(?![가-힣(])")
ENDING = re.compile(r"([가-힣]+)\.(?=\s|$)")
APART = re.compile(r"(?:[}`]|[A-Za-z])\s+(?:은|는|가|을|를|의|에|와|과|도|로|으로|에서|에게)(?=[\s.,]|$)")


def shown(text, labels):
    """TEXT with each `{id}` replaced by the label LABELS holds for the record it names."""
    return REFERENCE.sub(lambda match: labels.get(match.group(1), match.group(0)), text)


def spelling(word):
    """A pattern for WORD as a text may say it: its parts whatever the space between them, a Korean word alone or with a particle after it,
    any other with a plural ending, and never inside a longer word."""
    return whole(word, PARTICLE if re.search(r"[가-힣]$", word) else r"(?:e?s)?")


def whole(words, ending="", prefix=""):
    """A pattern for WORDS after PREFIX, whatever the space between them, then ENDING, never inside a longer word."""
    return r"(?<![\w-])" + prefix + r"\s+".join(re.escape(word) for word in words.split()) + ending + r"(?![\w-])"


def text_breaks(texts, labels):
    """Breaks of `formula` and `text-plain` in TEXTS, each (where, text), an item quoted as code left out: a formula outside the drawn subset,
    an open backtick, a `{id}` that names none of LABELS, {id: label}, and a drawing value or markup outside backticks."""
    found = []
    for where, text in texts:
        for tex, display in formulas(text):
            try:
                mathml(tex, display)
            except ValueError as error:
                found.append((where, "formula", f"`{tex}` in `{text[:40]}`: {error}; write it with {SUBSET} only, or quote it between backticks"))
        text = unformulated(text)
        if re.sub(r"```", "", text).count("`") % 2 or text.count("```") % 2:
            found.append((where, "text-plain", f"`{text[:40]}` opens a backtick it never closes; close the quote, since the page shows an open one as a mark"))
        for name in REFERENCE.findall(text):
            if name not in labels:
                found.append((where, "text-plain", f"`{{{name}}}` in `{text[:40]}` names no node, edge or area, the records a text can show by a label; quote the subject's own braces or markup in an item of the code form"))
        markup = MARKUP.search(re.sub(r"`[^`]*`", "", text)) or MARKUP.search(re.sub(r"`[^`]*`", "", shown(text, labels)))
        style = STYLE.search(re.sub(r"`[^`]*`", "", text))
        if style:
            found.append((where, "text-plain", f"`{style.group(0)}` in `{text[:40]}` reads as a colour, a size or a position; the page's code decides how a thing is drawn, so say what it is, or quote the subject's own value between backticks or in an item of the code form"))
        if markup:
            found.append((where, "text-plain", f"`{markup.group(0)}` in `{text[:40]}` reads as markup; the page's code decides how a text is drawn, so write a placeholder or the subject's own markup between backticks or in an item of the code form"))
    return found


RUN = re.compile(r"[\w-]+")
FOLDING = re.compile("[" + "".join(map(chr, (0x130, 0x131, 0x17F))) + "]")


class Spellings:
    """The labels a text may spell, found by the runs of word characters they hold: a match of a label is bounded by no word character on
    either side, so each run of its words is a whole run of the text, and replacing a match by a space leaves no new run; a label beyond
    ASCII, or a text holding a letter whose case folds onto ASCII while its lower case does not, is a candidate for every text or label."""

    def __init__(self, labels):
        self.wild, self.by_run, self.runs = [], {}, []
        for at, label in enumerate(labels):
            runs = frozenset(RUN.findall(label.lower()))
            self.runs.append(runs)
            if not label.isascii() or not runs:
                self.wild.append(at)
            else:
                self.by_run.setdefault(min(runs), []).append(at)

    def candidates(self, text):
        """The places, in order, of the labels TEXT may spell."""
        if FOLDING.search(text):
            return range(len(self.runs))
        runs = set(RUN.findall(text.lower()))
        found = set(self.wild)
        for run in runs:
            found.update(at for at in self.by_run.get(run, ()) if self.runs[at] <= runs)
        return sorted(found)


def wording_breaks(said, names, named, terms):
    """Breaks of `text-plain`, `formula`, `name-english`, `korean-text` and `term-words` in the words a contract chose: SAID, each (where, text),
    the texts that say something of the subject, a title or label among them placed at a `/title` or `/label` end; NAMES, each (where, name), the
    names drawn as words, such as a title or a node's label; NAMED, each (id, label), the records whose label no other text spells; TERMS, the
    contract's terms, each (where, avoiding, entry): the place of its term, the place of the words it avoids, and the entry, a `term` with
    the words it `avoid`s."""
    found = []
    # a label is spelt after `the` in any case, or as written when it holds two words; one word as written opens many a sentence
    ordered = sorted(((re.compile(whole(label, prefix=r"the\s+"), re.IGNORECASE), re.compile(whole(label) if len(label.split()) > 1 else "(?!)"), name, label)
                      for name, label in named if label.split()), key=lambda pair: -len(pair[0].pattern))
    spelt = [entry[:3] for entry in ordered]
    spelt_labels = [entry[3] for entry in ordered]
    index = Spellings(spelt_labels)
    pairs = sorted((at, number) for number, (other, label) in enumerate(named) for at in index.candidates(label)
                   if other != spelt[at][2] and spelt[at][0].search(label))
    for at, number in pairs:
        other, name = named[number][0], spelt[at][2]
        found.append((other, "text-plain", f"the label of `{other}` spells the label of `{name}`, so a new name for `{name}` would leave it stale; give it words of its own"))
    for where, text in said:
        rest = re.sub(r"`[^`]*`|\{[a-z0-9-]+\}", "", text)
        for after_article, written, name in (spelt[at] for at in index.candidates(rest)):
            rest, count = after_article.subn(" ", rest)
            rest, more = written.subn(" ", rest)
            if count or more:
                found.append((where, "text-plain", f"`{text[:40]}` spells the label of `{name}`; name it as `{{{name}}}`, so a new name reaches this text"))
    kept = {entry["term"].casefold(): entry["term"] for _, _, entry in terms}
    termed = [(where, entry["term"]) for where, _, entry in terms]
    for where, name in names + termed:
        if formulas(name):
            found.append((where, "formula", f"`{name[:40]}` holds a formula; the title, an area's or a node's label and a term draw no formula, so write it in words"))
    for where, name in names + termed + [pair for pair in said if pair[0].endswith(("/title", "/label"))]:
        if KOREAN.search(name):
            found.append((where, "name-english", f"`{name[:40]}` holds Korean; a title, a label and a term stay English, and only a description may be Korean"))
    avoided = sorted(((word, entry["term"], avoiding) for _, avoiding, entry in terms for word in entry.get("avoid", [])), key=lambda pair: -len(pair[0]))
    for word, term, avoiding in avoided:
        if word.casefold() in kept:
            found.append((avoiding, "term-words", f"`{word}` is the term `{kept[word.casefold()]}` and a word to avoid for `{term}`; one word names one concept"))
    for where, text in said:
        if KOREAN.search(text) and not where.endswith(("/title", "/label")):
            bare = re.sub(r"`[^`]*`", "`", text)
            paired, apart = PAIRED.search(bare), APART.search(bare)
            if paired:
                found.append((where, "korean-text", f"`{text[:40]}` writes `{paired.group(1)}` after a name; a new label may end in another sound, so write both forms, such as `은(는)`, `을(를)` or `(으)로`, or a particle of one form"))
            if any(not ending.endswith("니다") for ending in ENDING.findall(bare)):
                found.append((where, "korean-text", f"`{text[:40]}` closes a sentence outside `니다`; a Korean description is in the formal polite form"))
            if apart:
                found.append((where, "korean-text", f"`{text[:40]}` puts a space before a particle in `{apart.group(0)}`; a particle joins the word before it"))
    for where, text in said + names:
        rest = re.sub(r"`[^`]*`|\{[a-z0-9-]+\}", " ", text)
        for word, term, _ in avoided:
            rest, count = re.subn(spelling(word), " ", rest, flags=re.IGNORECASE)
            if count and word.casefold() not in kept:
                found.append((where, "term-words", f"`{text[:40]}` says `{word}` for the term `{term}`; one concept keeps one word, so write `{term}`, or quote the subject's own word between backticks"))
    return found
