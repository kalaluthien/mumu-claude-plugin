"""Find the formulas a contract's text holds and turn each, written in a small subset of TeX, into MathML a browser draws with no library.

A text holds an inline formula as `$...$` inside a sentence and a display formula as `$$...$$`, a centered block of its own; a quote in
backticks or a triple-backtick fence holds none. The page's code finds them by the same pattern, so the two must change together."""
import html
import re

CODE = re.compile(r"(```[\s\S]*?```|`[^`]+`)")
# a `$` opens an inline formula only before a character that is no space, and closes it only after one and before no digit,
# and `${NAME}` is a shell variable, so a price or a command line reads as text
FORMULA = re.compile(r"\$\$([^$`]+?)\$\$|\$(?!\{[A-Z_]+\})([^\s$`](?:[^$`]*?[^\s$`])?)\$(?!\d)")
GREEK = {name: chr(code) for name, code in [
    ("alpha", 0x3B1), ("beta", 0x3B2), ("gamma", 0x3B3), ("delta", 0x3B4), ("epsilon", 0x3B5), ("varepsilon", 0x3B5), ("zeta", 0x3B6),
    ("eta", 0x3B7), ("theta", 0x3B8), ("iota", 0x3B9), ("kappa", 0x3BA), ("lambda", 0x3BB), ("mu", 0x3BC), ("nu", 0x3BD), ("xi", 0x3BE),
    ("pi", 0x3C0), ("rho", 0x3C1), ("sigma", 0x3C3), ("tau", 0x3C4), ("upsilon", 0x3C5), ("phi", 0x3C6), ("varphi", 0x3C6), ("chi", 0x3C7),
    ("psi", 0x3C8), ("omega", 0x3C9), ("Gamma", 0x393), ("Delta", 0x394), ("Theta", 0x398), ("Lambda", 0x39B), ("Xi", 0x39E), ("Pi", 0x3A0),
    ("Sigma", 0x3A3), ("Upsilon", 0x3A5), ("Phi", 0x3A6), ("Psi", 0x3A8), ("Omega", 0x3A9)]}
RELATIONS = {"le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠", "approx": "≈", "equiv": "≡", "sim": "∼", "propto": "∝",
             "in": "∈", "notin": "∉", "subset": "⊂", "subseteq": "⊆", "supset": "⊃", "supseteq": "⊇", "to": "→", "rightarrow": "→",
             "leftarrow": "←", "Rightarrow": "⇒", "Leftarrow": "⇐", "Leftrightarrow": "⇔", "iff": "⇔", "mid": "∣", "ll": "≪", "gg": "≫"}
OPERATORS = {"cdot": "⋅", "times": "×", "pm": "±", "mp": "∓", "div": "÷", "cup": "∪", "cap": "∩", "land": "∧", "lor": "∨", "neg": "¬",
             "forall": "∀", "exists": "∃", "ldots": "…", "cdots": "⋯", "{": "{", "}": "}", "|": "‖"}
SYMBOLS = {"infty": "∞", "partial": "∂", "emptyset": "∅"}
LARGE = {"sum": "∑", "prod": "∏", "int": "∫", "lim": "lim"}
FUNCTIONS = ("log", "ln", "exp", "sin", "cos", "tan", "min", "max")
SPACES = {",": "0.17em", ";": "0.28em", " ": "0.25em", "quad": "1em"}
SIGNS = {"+": "+", "-": "−", "=": "=", "<": "&lt;", ">": "&gt;", "(": "(", ")": ")", "[": "[", "]": "]", ",": ",", ".": ".", "|": "|",
         "!": "!", "'": "′", "/": "/", ":": ":", ";": ";", "*": "∗"}
SUBSET = ("fractions, super- and subscripts, roots, Greek letters, relations, sums and the other large operators (`\\prod`, `\\int`, `\\lim`), "
          "the signs `\\cdot`, `\\times`, `\\pm`, set and logic operators and `\\infty`, functions such as `\\log`, `\\text{...}` and spaces")


def formulas(text):
    """Each formula TEXT holds outside its backtick quotes, as (tex, display), display True for a `$$...$$` one."""
    return [(match.group(1) or match.group(2), match.group(1) is not None)
            for part in CODE.split(text) if not CODE.fullmatch(part) for match in FORMULA.finditer(part)]


def unformulated(text):
    """TEXT with each formula outside its backtick quotes left out, so a rule about prose never reads TeX."""
    return "".join(part if CODE.fullmatch(part) else FORMULA.sub(" ", part) for part in CODE.split(text))


def key(tex, display):
    """The name the page looks a formula up by: its TeX with the marks around it."""
    return ("$$" if display else "$") + tex


def mathml(tex, display=False):
    """The MathML of one formula TEX; ValueError names the first part of it outside the subset."""
    reader = Reader(tex)
    inner = reader.row(None)
    return f'<math display="{"block" if display else "inline"}">{row_of(inner)}</math>'


def row_of(parts):
    return parts[0] if len(parts) == 1 else "<mrow>" + "".join(parts) + "</mrow>"


class Reader:
    def __init__(self, tex):
        self.tex, self.at = tex, 0

    def peek(self):
        while self.at < len(self.tex) and self.tex[self.at].isspace():
            self.at += 1
        return self.tex[self.at] if self.at < len(self.tex) else ""

    def row(self, closing):
        parts = []
        while True:
            char = self.peek()
            if not char:
                if closing:
                    raise ValueError(f"a `{'{' if closing == '}' else '['}` is never closed")
                return parts
            if char == closing:
                self.at += 1
                return parts
            if char == "}":
                raise ValueError("a `}` closes nothing")
            parts.append(self.scripted())

    def scripted(self):
        base, large = ("<mrow></mrow>", False) if self.peek() in ("^", "_") else self.atom()
        below = above = None
        while self.peek() in ("^", "_"):
            mark = self.tex[self.at]
            self.at += 1
            if (below if mark == "_" else above) is not None:
                raise ValueError(f"a second `{mark}` on one base")
            script = self.argument()
            below, above = (script, above) if mark == "_" else (below, script)
        if below is None and above is None:
            return base
        names = ("munder", "mover", "munderover") if large else ("msub", "msup", "msubsup")
        if above is None:
            return f"<{names[0]}>{base}{below}</{names[0]}>"
        if below is None:
            return f"<{names[1]}>{base}{above}</{names[1]}>"
        return f"<{names[2]}>{base}{below}{above}</{names[2]}>"

    def argument(self):
        if not self.peek():
            raise ValueError("a `^`, `_` or command lacks what it takes")
        return self.atom()[0]

    def atom(self):
        char = self.peek()
        if char == "{":
            self.at += 1
            return "<mrow>" + "".join(self.row("}")) + "</mrow>", False
        if char == "\\":
            return self.command()
        self.at += 1
        if char.isdigit() or char == "." and self.at < len(self.tex) and self.tex[self.at].isdigit():
            number = re.match(r"[0-9.]*", self.tex[self.at:]).group(0)
            self.at += len(number)
            return f"<mn>{char}{number}</mn>", False
        if char.isascii() and char.isalpha():
            return f"<mi>{char}</mi>", False
        if char in SIGNS:
            return f"<mo>{SIGNS[char]}</mo>", False
        raise ValueError(f"`{char}` is outside the subset")

    def command(self):
        self.at += 1
        name = re.match(r"[A-Za-z]+", self.tex[self.at:])
        name = name.group(0) if name else self.tex[self.at:self.at + 1]
        self.at += len(name)
        if name in GREEK:
            upright = ' mathvariant="normal"' if name[0].isupper() else ""
            return f"<mi{upright}>{GREEK[name]}</mi>", False
        if name in RELATIONS or name in OPERATORS:
            return f"<mo>{RELATIONS.get(name) or OPERATORS[name]}</mo>", False
        if name in SYMBOLS:
            return f"<mi>{SYMBOLS[name]}</mi>", False
        if name in LARGE:
            return (f"<mo>{LARGE[name]}</mo>" if name != "lim" else "<mi>lim</mi>"), name != "int"
        if name in FUNCTIONS:
            return f"<mi>{name}</mi>", False
        if name in SPACES:
            return f'<mspace width="{SPACES[name]}"></mspace>', False
        if name == "frac":
            top = self.argument()
            return f"<mfrac>{top}{self.argument()}</mfrac>", False
        if name == "sqrt":
            if self.peek() == "[":
                self.at += 1
                index = row_of(self.row("]"))
                return f"<mroot>{self.argument()}{index}</mroot>", False
            return f"<msqrt>{self.argument()}</msqrt>", False
        if name == "text":
            if self.peek() != "{" or "}" not in self.tex[self.at:]:
                raise ValueError("`\\text` takes its words in braces")
            end = self.tex.index("}", self.at)
            words, self.at = self.tex[self.at + 1:end], end + 1
            return f"<mtext>{html.escape(words)}</mtext>", False
        raise ValueError(f"`\\{name}` is outside the subset")
