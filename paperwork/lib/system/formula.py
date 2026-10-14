"""Formulas in Alloy 6 notation: tokens, a parser, the names a formula uses, and a readable layout.

The model writes rules (guards among them), pre and post conditions in Alloy itself, with English keywords
(not, and, or, implies, iff) and every logic Alloy 6 has: predicate, relational, integer and temporal.
The next state is written only with `after`; a primed name is refused.
"""
import re

KEYWORDS = {
    "abstract", "all", "and", "as", "assert", "but", "check", "disj", "else", "enum", "exactly", "expect",
    "extends", "fact", "for", "fun", "iden", "iff", "implies", "in", "Int", "int", "let", "lone", "module", "no",
    "none", "not", "one", "open", "or", "pred", "private", "run", "seq", "set", "sig", "some", "steps", "String",
    "sum", "this", "univ", "var", "always", "eventually", "after", "before", "historically", "once", "until",
    "releases", "since", "triggered",
}
# words the translation itself declares; a model may not use them as names
OWN = {"Now", "Call", "happens", "at", "self", "result", "stutter", "behaviour", "assumptions", "consistent"}
RESERVED = KEYWORDS | OWN

QUANT = {"all", "some", "no", "lone", "one", "sum"}
MULT = {"no", "some", "lone", "one", "set"}
UNARY_F = {"not", "always", "eventually", "after", "before", "historically", "once"}
BIN_T = {"until", "releases", "since", "triggered", ";"}
CMP = {"in", "=", "!=", "<", ">", "=<", ">="}
CONST = {"none", "univ", "iden", "Int"}
REFUSE = {"&&": "and", "||": "or", "=>": "implies", "<=>": "iff", "!": "not", "!in": "not in"}

TOK = re.compile(r"""
    (?P<ws>\s+) | (?P<num>\d+) | (?P<name>[A-Za-z][A-Za-z0-9_]*) |
    (?P<quote>"[^"]*"|'[^'\s]*') | (?P<prime>') |
    (?P<op><=>|=>|=<|>=|!=|!in|&&|\|\||->|<:|:>|\+\+|<<|>>>|>>|[-+&#.~^*;=<>!|,:\[\](){}@])
""", re.X)


class FormulaError(Exception):
    def __init__(self, msg, pos=None):
        super().__init__(msg)
        self.pos = pos


def tokens(text):
    out, i = [], 0
    while i < len(text):
        m = TOK.match(text, i)
        if not m:
            raise FormulaError(f"cannot read '{text[i]}'", i)
        kind = m.lastgroup
        val = m.group(kind)
        if kind == "prime":
            raise FormulaError("write the next state with after, not a prime", i)
        if kind == "quote":
            raise FormulaError(f"a value is a name, not a string: write {val.strip(chr(39) + chr(34)).replace(' ', '')}", i)
        if kind == "op" and val in REFUSE:
            raise FormulaError(f"write {REFUSE[val]}, not {val}", i)
        if kind != "ws":
            out.append((kind, val, i))
        i = m.end()
    out.append(("end", "", len(text)))
    return out


class Parser:
    """Pratt parser over Alloy 6 formulas and expressions. Nodes are tuples whose first item is the kind."""

    def __init__(self, text):
        self.t = tokens(text)
        self.i = 0

    def peek(self, k=0):
        return self.t[min(self.i + k, len(self.t) - 1)]

    def val(self, k=0):
        return self.peek(k)[1]

    def take(self, want=None):
        tok = self.t[self.i]
        if want is not None and tok[1] != want:
            raise FormulaError(f"expected {want}, found {tok[1] or 'the end'}", tok[2])
        self.i += 1
        return tok

    def parse(self):
        node = self.expr(0)
        if self.peek()[0] != "end":
            raise FormulaError(f"unexpected {self.val()}", self.peek()[2])
        return node

    # binding powers, lowest first; quantifiers and let take the rest of the formula
    BIN = [({"or"}, 10), ({"iff"}, 20), ({"implies"}, 30), ({"and"}, 40), (BIN_T, 50), (CMP | {"not"}, 70),
           ({"<<", ">>", ">>>"}, 85), ({"+", "-"}, 90), ({"++"}, 100), ({"&"}, 110), ({"->"}, 120), ({"<:", ":>"}, 130)]

    def bp(self):
        v, kind = self.val(), self.peek()[0]
        if kind not in ("op", "name"):
            return None
        if v == "not" and self.val(1) == "in":
            return 70
        if v == "not":
            return None
        for ops, p in self.BIN:
            if v in ops:
                return p
        return None

    def expr(self, min_bp, operand=False):
        left = self.prefix(operand)
        while True:
            v = self.val()
            if v == "[":
                left = self.box(left)
                continue
            if v == "." and min_bp <= 150:
                pos = self.take()[2]
                right = self.prefix(True, dot=True)
                left = ("join", left, right, pos)
                continue
            p = self.bp()
            if p is None or p < min_bp or (p == min_bp and v != "implies"):
                break
            if v == "not":
                self.take()
                self.take("in")
                op = "not in"
            else:
                op = self.take()[1]
            if op == "implies":
                right = self.expr(p, True)
                if self.val() == "else":
                    self.take()
                    other = self.expr(p, True)
                    left = ("ite", left, right, other)
                    continue
                left = ("bin", op, left, right)
                continue
            right = self.expr(p + 1, True)
            if op in CMP | {"not in"} and self.val() in CMP | {"not"} and self.bp() == 70:
                raise FormulaError("chain comparisons with and", self.peek()[2])
            left = ("bin", op, left, right)
        return left

    def box(self, target):
        self.take("[")
        args = [] if self.val() == "]" else [self.expr(0)]
        while self.val() == ",":
            self.take()
            args.append(self.expr(0))
        self.take("]")
        return ("box", target, args)

    def decls(self):
        out = []
        while True:
            disj = self.val() == "disj"
            if disj:
                self.take()
            names = [self.name()]
            while self.val() == ",":
                self.take()
                names.append(self.name())
            self.take(":")
            mult = self.take()[1] if self.val() in MULT else None
            out.append((names, disj, mult, self.expr(60, True)))
            if self.val() != ",":
                return out
            self.take()

    def name(self):
        tok = self.take()
        if tok[0] != "name" or tok[1] in KEYWORDS:
            raise FormulaError(f"expected a variable name, found {tok[1] or 'the end'}", tok[2])
        return tok[1]

    def is_decl(self):
        k = 0
        if self.val(k) == "disj":
            k += 1
        while self.peek(k)[0] == "name" and self.val(k) not in KEYWORDS:
            if self.val(k + 1) == ":":
                return True
            if self.val(k + 1) != ",":
                return False
            k += 2
        return False

    def prefix(self, operand=False, dot=False):
        kind, v, pos = self.peek()
        if dot:   # after a dot: a field, an operation, or a parenthesised expression
            if kind == "name" and v not in KEYWORDS - {"Int"}:
                self.take()
                return ("name", v, pos)
            if v == "(":
                return self.prefix()
            if v in {"~", "^", "*"}:
                self.take()
                return ("un", v, self.prefix(True, dot=True))
            raise FormulaError(f"expected a field or operation after the dot, found {v or 'the end'}", pos)
        if v in QUANT and self.val(1) != "[" and (self.is_decl_at(1)):
            self.take()
            ds = self.decls()
            self.take("|")
            return ("quant", v, ds, self.expr(0), pos)
        if v == "let":
            self.take()
            binds = []
            while True:
                n = self.name()
                self.take("=")
                binds.append((n, self.expr(60, True)))
                if self.val() != ",":
                    break
                self.take()
            self.take("|")
            return ("let", binds, self.expr(0), pos)
        if v in UNARY_F:
            self.take()
            if operand and self.val() in QUANT | {"let"} and self.is_decl_at(1) | (self.val() == "let"):
                raise FormulaError(f"put parentheses round the formula after {v}", pos)
            return ("un", v, self.expr(60, operand))
        if v in MULT and self.val(1) not in {"[", ".", ")", ",", "]", "|"}:
            self.take()
            return ("mult", v, self.expr(80, True))
        if v == "#":
            self.take()
            return ("un", "#", self.expr(100, True))
        if v in {"~", "^", "*"}:
            self.take()
            return ("un", v, self.expr(160, True))
        if v == "-" and self.peek(1)[0] == "num":
            self.take()
            return ("num", "-" + self.take()[1])
        if v == "(":
            self.take()
            inner = self.expr(0)
            self.take(")")
            return ("paren", inner)
        if v == "{":
            self.take()
            if self.is_decl():
                ds = self.decls()
                self.take("|")
                body = self.expr(0)
                self.take("}")
                return ("compr", ds, body, pos)
            items = []
            while self.val() != "}":
                items.append(self.expr(0))
            self.take("}")
            return ("block", items)
        if kind == "num":
            self.take()
            return ("num", v)
        if kind == "name":
            if v in CONST or v == "this":
                self.take()
                return ("const", v)
            if v in KEYWORDS:
                raise FormulaError(f"{v} cannot start an expression here", pos)
            self.take()
            return ("name", v, pos)
        raise FormulaError(f"unexpected {v or 'end of formula'}", pos)

    def is_decl_at(self, k):
        save = self.i
        self.i += k
        try:
            return self.is_decl()
        finally:
            self.i = save


def parse(text):
    return Parser(text).parse()


def walk(node, bound, use):
    """Call use(kind, name, pos, bound) for every name: 'free' (a bare name), 'member' (after a dot) or 'call'."""
    k = node[0]
    if k == "name":
        use("free", node[1], node[2], bound)
    elif k in ("num", "const"):
        return
    elif k == "paren":
        walk(node[1], bound, use)
    elif k == "block":
        for x in node[1]:
            walk(x, bound, use)
    elif k == "un" or k == "mult":
        walk(node[2], bound, use)
    elif k == "bin":
        walk(node[2], bound, use)
        walk(node[3], bound, use)
    elif k == "ite":
        for x in node[1:]:
            walk(x, bound, use)
    elif k == "join":
        walk(node[1], bound, use)
        r = node[2]
        while r[0] == "un" and r[1] in "~^*":
            r = r[2]
        if r[0] == "name":
            use("member", r[1], r[2], bound)
        else:
            walk(r, bound, use)
    elif k == "box":
        t = node[1]
        if t[0] == "name":
            use("call", t[1], t[2], bound)
        elif t[0] == "join" and t[2][0] == "name":
            walk(t[1], bound, use)
            use("member", t[2][1], t[2][2], bound)
        else:
            walk(t, bound, use)
        for a in node[2]:
            walk(a, bound, use)
    elif k in ("quant", "compr"):
        ds = node[2] if k == "quant" else node[1]
        inner = set(bound)
        for names, _, _, e in ds:
            walk(e, inner, use)
            inner |= set(names)
        walk(node[3] if k == "quant" else node[2], inner, use)
    elif k == "let":
        inner = set(bound)
        for n, e in node[1]:
            walk(e, inner, use)
            inner.add(n)
        walk(node[2], inner, use)


def uses(text):
    """[(kind, name, pos, bound)] for a formula, or raises FormulaError."""
    out = []
    walk(parse(text), set(), lambda *a: out.append(a))
    return out


def binders(text):
    """Every variable a formula binds with a quantifier, a comprehension or let."""
    out = []

    def grab(node):
        if not isinstance(node, tuple):
            return
        if node[0] in ("quant", "compr"):
            for names, *_ in (node[2] if node[0] == "quant" else node[1]):
                out.extend(names)
        if node[0] == "let":
            out.extend(n for n, _ in node[1])
        for x in node[1:]:
            if isinstance(x, tuple):
                grab(x)
            elif isinstance(x, list):
                for y in x:
                    if isinstance(y, tuple):
                        grab(y)
                        for z in y:
                            grab(z) if isinstance(z, tuple) else None

    grab(parse(text))
    return out


def free_spans(text, names):
    """Positions of bare, unbound occurrences of the given names, for renaming."""
    return [(pos, n) for kind, n, pos, bound in uses(text) if kind in ("free", "call") and n in names and n not in bound]


def rename(text, mapping):
    """Replace bare, unbound names (parameters, self, result) by expressions."""
    spans = sorted(free_spans(text, set(mapping)), reverse=True)
    for pos, n in spans:
        text = text[:pos] + mapping[n] + text[pos + len(n):]
    return text


def temporal(text):
    """Whether a formula speaks about time: a temporal operator, or one that only time gives meaning to."""
    return any(v in UNARY_F - {"not"} or v in BIN_T for _, v, _ in tokens(text))


WIDTH = 40   # a formula line holds about 40 mono characters


def show(node):
    k = node[0]
    if k in ("name",):
        return node[1]
    if k in ("num", "const"):
        return node[1]
    if k == "paren":
        return "(" + show(node[1]) + ")"
    if k == "block":
        return "{ " + " ".join(show(x) for x in node[1]) + " }"
    if k == "un":
        return node[1] + ("" if node[1] in "#~^*" else " ") + show(node[2])
    if k == "mult":
        return node[1] + " " + show(node[2])
    if k == "bin":
        sep = "" if node[1] in ("->",) else " "
        return show(node[2]) + sep + node[1] + sep + show(node[3])
    if k == "ite":
        return f"{show(node[1])} implies {show(node[2])} else {show(node[3])}"
    if k == "join":
        return show(node[1]) + "." + show(node[2])
    if k == "box":
        return show(node[1]) + "[" + ", ".join(show(a) for a in node[2]) + "]"
    if k in ("quant", "compr"):
        ds = node[2] if k == "quant" else node[1]
        d = ", ".join(("disj " if dj else "") + ", ".join(ns) + ": " + (m + " " if m else "") + show(e) for ns, dj, m, e in ds)
        body = node[3] if k == "quant" else node[2]
        return (f"{node[1]} {d} | {show(body)}" if k == "quant" else "{" + d + " | " + show(body) + "}")
    if k == "let":
        return "let " + ", ".join(f"{n} = {show(e)}" for n, e in node[1]) + " | " + show(node[2])
    raise ValueError(k)


def chain(node, op):
    if node[0] == "bin" and node[1] == op:
        return chain(node[2], op) + chain(node[3], op)
    return [node]


def lines(node, ind=0):
    """Lay a formula out over lines no wider than WIDTH: a quantifier's body goes below it, long chains break before and, or."""
    flat = show(node)
    pad = "  " * ind
    if len(flat) + len(pad) <= WIDTH:
        return [pad + flat]
    k = node[0]
    if k == "quant":
        ds = [("disj " if dj else "") + ", ".join(ns) + ": " + (mm + " " if mm else "") + show(e) for ns, dj, mm, e in node[2]]
        head, rows = pad + node[1] + " ", []
        for i, d in enumerate(ds):   # declarations wrap one per line when the header is too wide
            piece = d + ("," if i < len(ds) - 1 else " |")
            if rows and len(rows[-1]) + 1 + len(piece) > WIDTH:
                rows.append(pad + "    " + piece)
            else:
                rows = rows[:-1] + [(rows[-1] + " " if rows else head) + piece]
        return rows + lines(node[3], ind + 1)
    if k == "let":
        head = "let " + ", ".join(f"{n} = {show(e)}" for n, e in node[1]) + " |"
        return [pad + head] + lines(node[2], ind + 1)
    if k == "paren":
        inner = lines(node[1], ind + 1)
        return [pad + "(" + inner[0].lstrip()] + inner[1:-1] + [inner[-1] + ")"] if len(inner) > 1 else [pad + "(" + inner[0].lstrip() + ")"]
    if k == "un" and node[1] not in "#~^*":
        inner = lines(node[2], ind)
        return [pad + node[1] + " " + inner[0].lstrip()] + inner[1:]
    if k == "bin" and node[1] in ("and", "or"):
        parts = chain(node, node[1])
        out = lines(parts[0], ind)
        for p in parts[1:]:
            sub = lines(p, ind)
            out += [pad + node[1] + " " + sub[0].lstrip()] + sub[1:]
        return out
    if k in ("bin", "ite") and (k == "ite" or node[1] in ("implies", "iff")):
        a, b = (node[1], node[2]) if k == "ite" else (node[2], node[3])
        word = "implies" if k == "ite" else node[1]
        head = lines(a, ind)
        head[-1] += " " + word
        out = head + lines(b, ind + 1)
        if k == "ite":
            out += [pad + "else"] + lines(node[3], ind + 1)
        return out
    if k == "bin" and node[1] in CMP | {"not in"}:   # a long comparison: its right side goes below
        return lines(node[2], ind) + [pad + "  " + node[1] + " " + l.lstrip() for l in lines(node[3], ind + 1)[:1]] + lines(node[3], ind + 1)[1:]
    return [pad + flat]


def layout(text):
    """The formula over several lines, or the text unchanged when it does not parse."""
    try:
        return "\n".join(lines(parse(text)))
    except FormulaError:
        return text
